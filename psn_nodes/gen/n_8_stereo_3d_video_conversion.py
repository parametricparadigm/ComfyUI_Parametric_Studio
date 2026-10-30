"""PSN_Stereo_Converter -- pure-logic planning/validation for 2D->3D stereo conversion.

This module implements ONLY the secure, CPU-safe portion of the "Stereo 3D Video
Conversion" spec. The actual per-pixel parallax warping needs torch/numpy and a GPU,
which are intentionally NOT used here. Instead this node:

  * validates the incoming VIDEO / DEPTH_MAPS tensor descriptors (JSON text),
  * enforces the FORMAT allow-list (side_by_side | top_bottom | anaglyph),
  * checks that depth maps are in [0, 1] and share the video's T/H/W,
  * computes the exact output tensor shape a downstream GPU kernel would produce,
  * reports a human-readable reason for any rejection.

Inputs are plain values (strings / numbers / JSON text). No sockets, no files,
no network, no subprocess, no torch, no ComfyUI imports.
"""

import json

CAT = "ParametricStudio/Stereo"

_FORMATS = ("side_by_side", "top_bottom", "anaglyph")
_MIN_T = 1
_MAX_T = 100000
_MIN_DIM = 1
_MAX_DIM = 100000
_MIN_PARALLAX = -1e9
_MAX_PARALLAX = 1e9


def _parse_tensor_desc(text, name):
    """Parse a JSON tensor descriptor into (T, H, W, C) ints.

    Accepts either a list [T, H, W, C] or an object
    {"T":..,"H":..,"W":..,"C":..}. Returns (None, reason) on any problem.
    """
    if not isinstance(text, str):
        return None, "%s must be JSON text" % name
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None, "%s is not valid JSON" % name

    if isinstance(data, (list, tuple)):
        if len(data) != 4:
            return None, "%s must have exactly 4 dims [T,H,W,C]" % name
        vals = list(data)
    elif isinstance(data, dict):
        vals = [data.get("T"), data.get("H"), data.get("W"), data.get("C")]
    else:
        return None, "%s must be a list or object" % name

    dims = []
    for i, v in enumerate(vals):
        if isinstance(v, bool) or not isinstance(v, int):
            return None, "%s dim %d must be an integer" % (name, i)
        dims.append(v)

    t, h, w, c = dims
    if t < _MIN_T or t > _MAX_T:
        return None, "%s T out of range" % name
    if h < _MIN_DIM or h > _MAX_DIM:
        return None, "%s H out of range" % name
    if w < _MIN_DIM or w > _MAX_DIM:
        return None, "%s W out of range" % name
    if c < 1 or c > 4:
        return None, "%s must have C in [1,4] (RGB or RGBA)" % name
    return (t, h, w, c), None


def _validate_depth_range(depth_min, depth_max):
    """Depth maps must be normalised to [0, 1]."""
    if depth_min < 0.0 or depth_max > 1.0:
        return False, "depth maps must be in [0,1]"
    if depth_min > depth_max:
        return False, "depth min exceeds max"
    return True, "ok"


def compute_output_shape(t, h, w, fmt):
    """Return (T, H_out, W_out, C) for the given stereo format."""
    if fmt == "side_by_side":
        return (t, h, w * 2, 3)
    if fmt == "top_bottom":
        return (t, h * 2, w, 3)
    if fmt == "anaglyph":
        return (t, h, w, 3)
    raise ValueError("unknown format: %r" % (fmt,))


class PSN_Stereo_Converter:
    """Validate a 2D video + depth-map pair and plan its stereo 3D conversion."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_desc": ("STRING", {"default": "[1, 2, 2, 3]", "multiline": False}),
                "depth_desc": ("STRING", {"default": "[1, 2, 2, 1]", "multiline": False}),
                "parallax": ("FLOAT", {"default": 0.0, "min": _MIN_PARALLAX, "max": _MAX_PARALLAX, "step": 0.001}),
                "format": (list(_FORMATS),),
                "depth_min": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "depth_max": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("valid", "output_shape", "reason", "plan_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video_desc, depth_desc, parallax, format, depth_min, depth_max):
        # 1) format allow-list
        if format not in _FORMATS:
            return (False, "", "format not in allow-list", "")

        # 2) parse video
        video, why = _parse_tensor_desc(video_desc, "VIDEO")
        if video is None:
            return (False, "", why, "")

        # 3) parse depth
        depth, why = _parse_tensor_desc(depth_desc, "DEPTH_MAPS")
        if depth is None:
            return (False, "", why, "")

        # 4) depth maps must share T/H/W with the video
        vt, vh, vw, _ = video
        dt, dh, dw, _ = depth
        if (vt, vh, vw) != (dt, dh, dw):
            return (False, "", "DEPTH_MAPS T/H/W must match VIDEO", "")

        # 5) depth range
        ok, why = _validate_depth_range(depth_min, depth_max)
        if not ok:
            return (False, "", why, "")

        # 6) parallax sanity (finite)
        if parallax != parallax or parallax in (float("inf"), float("-inf")):
            return (False, "", "parallax must be finite", "")

        # 7) compute output shape
        out_shape = compute_output_shape(vt, vh, vw, format)

        plan = {
            "format": format,
            "parallax": parallax,
            "input_video": list(video),
            "input_depth": list(depth),
            "output_shape": list(out_shape),
            "depth_range": [depth_min, depth_max],
        }
        return (True, str(out_shape), "ok", json.dumps(plan))


NODE_CLASS_MAPPINGS = {
    "PSN_Stereo_Converter": PSN_Stereo_Converter,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Stereo_Converter": "Stereo 3D Video Converter (Plan)",
}
