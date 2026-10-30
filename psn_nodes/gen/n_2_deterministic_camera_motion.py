"""
PSN Deterministic Camera Motion (pure-logic, secure-by-design).

This module implements the *pure-logic* parts of the "Deterministic Camera Motion"
spec. It does NOT touch torch, torchvision, numpy, yaml, or any GPU/CUDA kernels,
and it performs no file, network, or OS access.

What it does (pure Python standard library only):
  * PSN_Camera_Path_Definer: parses a JSON keyframe string, validates it, and
    builds a deterministic, multi-dimensional (x, y, z, rot) keyframed curve
    with linear / cubic (Catmull-Rom) / step interpolation. It also emits a
    small ASCII "preview" plot of the path (a stand-in for the IMAGE debug plot).
  * PSN_Camera_Apply: evaluates the curve at a frame index and computes the
    affine transform parameters (pan x/y, zoom, rotation) that a downstream
    image renderer would apply. It returns the numeric transform, not pixels.

The "KEYFRAMED_CURVE" output is a plain dict (JSON-serializable) so it can be
passed between nodes without any external dependency.
"""

import json
import math

CAT = "ParametricStudio/Camera"

_INTERP_MODES = ["linear", "cubic", "step"]
_DIMS = ["x", "y", "z", "rot"]


def _clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _parse_keyframes(text):
    """Parse a JSON keyframe string into a validated, sorted list of dicts.

    Each keyframe must be a mapping with integer 'frame' and numeric
    x, y, z, rot. Returns (keyframes, error).
    """
    if not isinstance(text, str):
        return None, "keyframes must be a JSON string"
    try:
        data = json.loads(text)
    except Exception as exc:
        return None, "invalid JSON: %s" % exc

    if not isinstance(data, list):
        return None, "keyframes must be a JSON array of objects"
    if len(data) == 0:
        return None, "keyframes must contain at least one entry"

    parsed = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            return None, "keyframe %d must be an object" % i
        if "frame" not in item:
            return None, "keyframe %d missing 'frame'" % i
        frame = item["frame"]
        if isinstance(frame, bool) or not isinstance(frame, int):
            return None, "keyframe %d 'frame' must be an integer" % i
        if frame < 0:
            return None, "keyframe %d 'frame' must be >= 0" % i
        entry = {"frame": frame}
        for dim in _DIMS:
            val = item.get(dim, 0)
            if not _is_number(val):
                return None, "keyframe %d '%s' must be a number" % (i, dim)
            if math.isnan(val) or math.isinf(val):
                return None, "keyframe %d '%s' must be finite" % (i, dim)
            entry[dim] = float(val)
        parsed.append(entry)

    # Sort by frame; reject duplicate frames.
    parsed.sort(key=lambda e: e["frame"])
    for i in range(1, len(parsed)):
        if parsed[i]["frame"] == parsed[i - 1]["frame"]:
            return None, "duplicate frame %d" % parsed[i]["frame"]
    return parsed, None


def _catmull_rom(p0, p1, p2, p3, t):
    """Catmull-Rom interpolation between p1 and p2 given neighbours p0, p3."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def _interp_dim(values, frames, frame, mode):
    """Interpolate a single dimension at an absolute frame index."""
    n = len(frames)
    if frame <= frames[0]:
        return values[0]
    if frame >= frames[-1]:
        return values[-1]

    # Find the segment [i, i+1] such that frames[i] <= frame < frames[i+1].
    i = 0
    for idx in range(n - 1):
        if frames[idx] <= frame < frames[idx + 1]:
            i = idx
            break

    f0 = frames[i]
    f1 = frames[i + 1]
    span = f1 - f0
    if span == 0:
        return values[i]
    t = (frame - f0) / span

    if mode == "step":
        return values[i]
    if mode == "linear":
        return values[i] + (values[i + 1] - values[i]) * t
    # cubic (Catmull-Rom)
    p0 = values[i - 1] if i - 1 >= 0 else values[i]
    p1 = values[i]
    p2 = values[i + 1]
    p3 = values[i + 2] if i + 2 < n else values[i + 1]
    return _catmull_rom(p0, p1, p2, p3, t)


def _build_curve(keyframes, interpolation, duration_frames):
    """Build the KEYFRAMED_CURVE dict (JSON-serializable)."""
    frames = [kf["frame"] for kf in keyframes]
    dims = {d: [kf[d] for kf in keyframes] for d in _DIMS}
    return {
        "type": "KEYFRAMED_CURVE",
        "interpolation": interpolation,
        "duration_frames": int(duration_frames),
        "frames": frames,
        "dims": dims,
    }


def _evaluate_curve(curve, frame_index):
    """Evaluate the curve at a frame index -> dict of x, y, z, rot."""
    frames = curve["frames"]
    dims = curve["dims"]
    mode = curve["interpolation"]
    out = {}
    for d in _DIMS:
        out[d] = _interp_dim(dims[d], frames, frame_index, mode)
    return out


def _ascii_preview(curve, width=40, height=12):
    """Render a small ASCII plot of the x/y path over the duration."""
    duration = max(1, int(curve["duration_frames"]))
    frames = curve["frames"]
    dims = curve["dims"]
    xs = [_interp_dim(dims["x"], frames, f, curve["interpolation"]) for f in range(duration)]
    ys = [_interp_dim(dims["y"], frames, f, curve["interpolation"]) for f in range(duration)]
    if not xs:
        return "(empty)"
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xr = (xmax - xmin) or 1.0
    yr = (ymax - ymin) or 1.0
    grid = [[" "] * width for _ in range(height)]
    for f, (x, y) in enumerate(zip(xs, ys)):
        col = int(round((x - xmin) / xr * (width - 1)))
        row = int(round((1.0 - (y - ymin) / yr) * (height - 1)))
        row = _clamp(row, 0, height - 1)
        col = _clamp(col, 0, width - 1)
        grid[row][col] = "*"
    return "\n".join("".join(r) for r in grid)


class PSN_Camera_Path_Definer:
    """Parse keyframed camera data and build a deterministic KEYFRAMED_CURVE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "keyframes": ("STRING", {"default": "[{\"frame\":0,\"x\":0,\"y\":0,\"z\":0,\"rot\":0}]"}),
                "interpolation": (_INTERP_MODES,),
                "duration_frames": ("INT", {"default": 100, "min": 1, "max": 100000, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("KEYFRAMED_CURVE", "STRING")
    RETURN_NAMES = ("camera_curve", "preview_image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, keyframes, interpolation, duration_frames):
        parsed, err = _parse_keyframes(keyframes)
        if err is not None:
            # Return an empty/invalid curve plus the error as the preview text.
            empty = {
                "type": "KEYFRAMED_CURVE",
                "interpolation": interpolation,
                "duration_frames": int(duration_frames),
                "frames": [],
                "dims": {d: [] for d in _DIMS},
                "error": err,
            }
            return (empty, "ERROR: " + err)
        curve = _build_curve(parsed, interpolation, duration_frames)
        preview = _ascii_preview(curve)
        return (curve, preview)


class PSN_Camera_Apply:
    """Evaluate a KEYFRAMED_CURVE at a frame and compute the affine transform."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "camera_curve": ("KEYFRAMED_CURVE",),
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
            },
            "optional": {
                "base_image": (None,),  # placeholder; pixel work is out of scope here
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("transformed_image", "pan_x", "pan_y", "zoom", "rotation_deg")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, camera_curve, frame_index, base_image=None):
        if not isinstance(camera_curve, dict) or camera_curve.get("type") != "KEYFRAMED_CURVE":
            return ("ERROR: invalid camera_curve", 0.0, 0.0, 1.0, 0.0)
        if not camera_curve.get("frames"):
            return ("ERROR: empty camera_curve", 0.0, 0.0, 1.0, 0.0)
        state = _evaluate_curve(camera_curve, int(frame_index))
        # z is treated as a zoom factor (1.0 == no zoom).
        zoom = state["z"] if state["z"] != 0.0 else 1.0
        # The "transformed_image" output is a JSON description of the affine
        # transform (pure-logic stand-in for the rendered pixels).
        transform = {
            "type": "AFFINE_TRANSFORM",
            "frame_index": int(frame_index),
            "pan_x": state["x"],
            "pan_y": state["y"],
            "zoom": zoom,
            "rotation_deg": state["rot"],
        }
        return (json.dumps(transform), state["x"], state["y"], zoom, state["rot"])


NODE_CLASS_MAPPINGS = {
    "PSN_Camera_Path_Definer": PSN_Camera_Path_Definer,
    "PSN_Camera_Apply": PSN_Camera_Apply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Camera_Path_Definer": "PSN Camera Path Definer",
    "PSN_Camera_Apply": "PSN Camera Apply",
}
