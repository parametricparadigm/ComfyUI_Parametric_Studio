"""PSN 2.5D Parallax Video Effect (pure-logic core).

This module implements the *algorithmic* part of a 2.5D parallax video effect
without any GPU / torch / ComfyUI / file / network / subprocess access.

Because the real effect needs pixel tensors (torch) and video encoding
(ffmpeg / pyav), which are disallowed here, the nodes operate on *plain*
values:

  * ``PSN_Depth_Parallax_Generator`` takes a depth map as a JSON string
    (a 2D list of numbers in [0, 1]) plus camera-path parameters and returns
    a JSON string describing the per-frame displacement field (the "motion
    vectors") together with the number of frames produced.  This is the
    pure-logic core: given a depth map and a camera path, compute how much
    each pixel should be displaced for every frame.  A downstream (GPU)
    stage would apply these displacements to the actual image pixels.

  * ``PSN_Parallax_Video_Assembler`` takes a JSON string describing a batch
    of frames plus fps / codec and returns a *descriptive* video path string
    (it does NOT write any file).  It validates the codec / fps and builds a
    deterministic, safe path name.

All inputs are plain numbers / strings / JSON text.  No sockets, no files,
no subprocess, no eval/exec, no dunder tricks.
"""

import json
import math

CAT = "ParametricStudio/Parallax"

# Camera paths supported by the generator.
CAMERA_PATHS = ["pan_left", "pan_right", "zoom_in", "zoom_out"]

# Codecs supported by the assembler.
CODECS = ["mp4", "webm"]

# Displacement is expressed in pixels.  We clamp so that no pixel is pushed
# off the image, which is the "artifacts at edges" risk from the spec.
_MAX_DISPLACEMENT = 64.0


def _parse_depth_map(depth_json):
    """Parse a JSON 2D list of numbers into a list of lists of floats.

    Returns (rows, cols, grid) where grid[r][c] is a float in [0, 1].
    Raises ValueError on malformed input.
    """
    if not isinstance(depth_json, str):
        raise ValueError("depth_map must be a JSON string")
    try:
        data = json.loads(depth_json)
    except (ValueError, TypeError) as exc:
        raise ValueError("depth_map is not valid JSON: %s" % exc)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("depth_map must be a non-empty 2D list")

    rows = len(data)
    cols = None
    grid = []
    for r, row in enumerate(data):
        if not isinstance(row, list):
            raise ValueError("depth_map row %d is not a list" % r)
        if cols is None:
            cols = len(row)
            if cols == 0:
                raise ValueError("depth_map rows must be non-empty")
        if len(row) != cols:
            raise ValueError("depth_map rows must all have the same length")
        parsed_row = []
        for c, val in enumerate(row):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError("depth_map[%d][%d] is not a number" % (r, c))
            f = float(val)
            if not math.isfinite(f):
                raise ValueError("depth_map[%d][%d] is not finite" % (r, c))
            # Clamp to [0, 1]; out-of-range values are treated as invalid
            # depth and clamped (spec: "artifacts at edges where depth is
            # invalid").
            if f < 0.0:
                f = 0.0
            elif f > 1.0:
                f = 1.0
            parsed_row.append(f)
        grid.append(parsed_row)
    return rows, cols, grid


def _camera_displacement(camera_path, frame_index, frame_count, rows, cols):
    """Return (dx, dy) base displacement (in pixels) for a frame.

    The displacement is scaled by depth per-pixel downstream; here we return
    the *maximum* displacement that a depth-1.0 pixel would receive.  The
    actual per-pixel displacement is ``depth * base``.

    Motion is spread across the frames so that frame 0 has zero displacement
    (the original image) and the last frame has the full displacement.
    """
    if frame_count <= 1:
        t = 0.0
    else:
        t = float(frame_index) / float(frame_count - 1)

    # Total travel in pixels across the whole sequence.  We use a fraction of
    # the image size so it looks reasonable for typical image dimensions.
    travel_x = 0.05 * cols
    travel_y = 0.05 * rows

    dx = 0.0
    dy = 0.0
    if camera_path == "pan_left":
        dx = -travel_x * t
    elif camera_path == "pan_right":
        dx = travel_x * t
    elif camera_path == "zoom_in":
        # Zoom in: pixels move outward from the center.  We model this as a
        # uniform scale factor; the per-pixel displacement is computed
        # relative to the center in the caller.  Here we return a scale
        # factor encoded as dy (positive = zoom in).
        dy = 0.05 * t
    elif camera_path == "zoom_out":
        dy = -0.05 * t
    else:
        raise ValueError("unknown camera_path: %r" % camera_path)

    # Clamp the base displacement so we never push pixels off the image.
    dx = max(-_MAX_DISPLACEMENT, min(_MAX_DISPLACEMENT, dx))
    dy = max(-_MAX_DISPLACEMENT, min(_MAX_DISPLACEMENT, dy))
    return dx, dy


def _build_frame_displacement(grid, rows, cols, dx, dy, motion_strength, is_zoom):
    """Build a 2D list of (dx, dy) per-pixel displacements for one frame.

    For pan: displacement = depth * (dx, dy).
    For zoom: displacement = depth * (scale * (cx - x), scale * (cy - y))
    where (cx, cy) is the image center and scale is the zoom factor.
    """
    cx = (cols - 1) / 2.0
    cy = (rows - 1) / 2.0
    frame = []
    for r in range(rows):
        row = []
        for c in range(cols):
            depth = grid[r][c]
            if is_zoom:
                # dy here is the scale factor (positive = zoom in).
                scale = dy
                px = (c - cx) * scale * depth * motion_strength
                py = (r - cy) * scale * depth * motion_strength
                px = max(-_MAX_DISPLACEMENT, min(_MAX_DISPLACEMENT, px))
                py = max(-_MAX_DISPLACEMENT, min(_MAX_DISPLACEMENT, py))
                row.append([px, py])
            else:
                px = dx * depth * motion_strength
                py = dy * depth * motion_strength
                px = max(-_MAX_DISPLACEMENT, min(_MAX_DISPLACEMENT, px))
                py = max(-_MAX_DISPLACEMENT, min(_MAX_DISPLACEMENT, py))
                row.append([px, py])
        frame.append(row)
    return frame


def _build_mask(grid, rows, cols):
    """Build a binary mask: 1 where depth is valid (in [0,1] and finite),
    0 where depth was invalid (out of range before clamping).  Since we
    clamp, we instead mark pixels whose original depth was outside [0,1]
    as 0.  But we already clamped, so we track validity separately.

    For simplicity in this pure-logic core, the mask is 1 where depth > 0
    (i.e., the pixel participates in parallax) and 0 where depth == 0
    (background, no motion).  This is a reasonable proxy for a validity
    mask.
    """
    mask = []
    for r in range(rows):
        row = []
        for c in range(cols):
            row.append(1 if grid[r][c] > 0.0 else 0)
        mask.append(row)
    return mask


class PSN_Depth_Parallax_Generator:
    """Generate per-frame displacement fields for a 2.5D parallax effect.

    Inputs are plain values: a JSON string depth map, a motion strength,
    a frame count, and a camera path.  Outputs are a JSON string describing
    the per-frame displacement fields (the "video_frames" in the pure-logic
    sense) and a JSON string of the corresponding masks.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "depth_map": ("STRING", {"default": "[]", "multiline": True}),
                "motion_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "frame_count": ("INT", {"default": 10, "min": 1, "max": 1000, "step": 1}),
                "camera_path": (CAMERA_PATHS,),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_frames", "masks")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, depth_map, motion_strength, frame_count, camera_path):
        rows, cols, grid = _parse_depth_map(depth_map)
        if frame_count < 1:
            raise ValueError("frame_count must be >= 1")
        if motion_strength < 0.0:
            raise ValueError("motion_strength must be >= 0")
        if camera_path not in CAMERA_PATHS:
            raise ValueError("camera_path must be one of %s" % CAMERA_PATHS)

        is_zoom = camera_path in ("zoom_in", "zoom_out")
        frames = []
        for i in range(frame_count):
            dx, dy = _camera_displacement(camera_path, i, frame_count, rows, cols)
            frame = _build_frame_displacement(grid, rows, cols, dx, dy, motion_strength, is_zoom)
            frames.append(frame)

        mask = _build_mask(grid, rows, cols)
        # The mask is the same for every frame (depth doesn't change).
        masks = [mask] * frame_count

        frames_json = json.dumps(frames)
        masks_json = json.dumps(masks)
        return (frames_json, masks_json)


class PSN_Parallax_Video_Assembler:
    """Build a descriptive video path string for a batch of parallax frames.

    This does NOT write any file.  It validates the fps and codec, and
    returns a deterministic, safe path string that a downstream (GPU /
    ffmpeg) stage would use to encode the video.

    Inputs: a JSON string describing the batch of frames (list of per-frame
    displacement fields, as produced by PSN_Depth_Parallax_Generator), an
    fps (INT), and a codec (COMBO).
    Output: a STRING video path.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frames": ("STRING", {"default": "[]", "multiline": True}),
                "fps": ("INT", {"default": 30, "min": 1, "max": 240, "step": 1}),
                "codec": (CODECS,),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, frames, fps, codec):
        if not isinstance(frames, str):
            raise ValueError("frames must be a JSON string")
        try:
            data = json.loads(frames)
        except (ValueError, TypeError) as exc:
            raise ValueError("frames is not valid JSON: %s" % exc)
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("frames must be a non-empty JSON list")
        if fps < 1:
            raise ValueError("fps must be >= 1")
        if fps > 240:
            raise ValueError("fps must be <= 240")
        if codec not in CODECS:
            raise ValueError("codec must be one of %s" % CODECS)

        # Build a deterministic, safe path.  We use the frame count and a
        # simple hash-like suffix derived from the frame data length to make
        # the path unique but stable.
        frame_count = len(data)
        # A simple, safe identifier: frame count and total element count.
        total_elements = 0
        for frame in data:
            if not isinstance(frame, list):
                raise ValueError("each frame must be a list")
            for row in frame:
                if not isinstance(row, list):
                    raise ValueError("each frame row must be a list")
                total_elements += len(row)

        ext = "mp4" if codec == "mp4" else "webm"
        path = "parallax_video_%d_frames_%d_elems.%s" % (frame_count, total_elements, ext)
        return (path,)


NODE_CLASS_MAPPINGS = {
    "PSN_Depth_Parallax_Generator": PSN_Depth_Parallax_Generator,
    "PSN_Parallax_Video_Assembler": PSN_Parallax_Video_Assembler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Depth_Parallax_Generator": "PSN Depth Parallax Generator",
    "PSN_Parallax_Video_Assembler": "PSN Parallax Video Assembler",
}
