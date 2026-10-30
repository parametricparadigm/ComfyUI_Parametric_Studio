"""PSN_Aspect_Ratio_Enforcer: pure-logic aspect-ratio planning for image/latent tensors.

This module implements ONLY the secure, pure-logic part of the spec: it computes the
target output dimensions and the crop/pad/resize plan (offsets, sizes, padding amounts)
for a given input shape and target aspect ratio. It does NOT touch GPU/torch/ComfyUI
internals, does no file/network I/O, and operates on plain values (integers, floats,
strings, JSON text). The actual tensor manipulation (cropping/padding/resizing) is left
to the host runtime; this node emits a deterministic, validated plan plus the resulting
width/height so downstream nodes can apply it.

Inputs are plain numbers/strings; outputs are plain numbers/strings.
"""

import json

CAT = "ParametricStudio/Geometry"

_MODES = ("crop", "pad", "resize")


def _psn_validate_positive_int(value, name):
    """Validate that value is a positive integer (or integer-valued number)."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer, got bool")
    if isinstance(value, int):
        if value <= 0:
            raise ValueError(f"{name} must be > 0, got {value}")
        return value
    if isinstance(value, float):
        if value != int(value) or value <= 0:
            raise ValueError(f"{name} must be a positive integer, got {value}")
        return int(value)
    raise ValueError(f"{name} must be a positive integer, got {type(value).__name__}")


def _psn_validate_ratio(ratio):
    """Validate target aspect ratio is a finite positive number."""
    if isinstance(ratio, bool):
        raise ValueError("target_ratio must be a positive number, got bool")
    if not isinstance(ratio, (int, float)):
        raise ValueError(f"target_ratio must be a number, got {type(ratio).__name__}")
    if ratio != ratio or ratio in (float("inf"), float("-inf")):
        raise ValueError("target_ratio must be finite")
    if ratio <= 0:
        raise ValueError(f"target_ratio must be > 0, got {ratio}")
    return float(ratio)


def _psn_compute_plan(width, height, target_ratio, mode):
    """Compute the aspect-ratio adjustment plan.

    Returns a dict with:
      - out_width, out_height: resulting dimensions
      - crop_x, crop_y, crop_w, crop_h: crop window (for crop mode; identity for others)
      - pad_left, pad_right, pad_top, pad_bottom: padding amounts (for pad mode; 0 for others)
      - resize_from_w, resize_from_h: source dims to resize from (for resize mode)
      - mode: the mode used
    """
    width = _psn_validate_positive_int(width, "width")
    height = _psn_validate_positive_int(height, "height")
    target_ratio = _psn_validate_ratio(target_ratio)
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")

    current_ratio = width / height

    if mode == "resize":
        # Distort: keep input dims, just declare a resize from input to input (no-op shape-wise)
        # but we still report the target dims equal to input (distortion is applied by host).
        out_width, out_height = width, height
        return {
            "out_width": out_width,
            "out_height": out_height,
            "crop_x": 0,
            "crop_y": 0,
            "crop_w": width,
            "crop_h": height,
            "pad_left": 0,
            "pad_right": 0,
            "pad_top": 0,
            "pad_bottom": 0,
            "resize_from_w": width,
            "resize_from_h": height,
            "mode": mode,
        }

    if mode == "crop":
        # Remove edges to match target ratio.
        if current_ratio > target_ratio:
            # Too wide: crop width
            new_width = int(round(height * target_ratio))
            new_width = max(1, min(new_width, width))
            crop_w = new_width
            crop_h = height
            crop_x = (width - crop_w) // 2
            crop_y = 0
        else:
            # Too tall: crop height
            new_height = int(round(width / target_ratio))
            new_height = max(1, min(new_height, height))
            crop_w = width
            crop_h = new_height
            crop_x = 0
            crop_y = (height - crop_h) // 2
        return {
            "out_width": crop_w,
            "out_height": crop_h,
            "crop_x": crop_x,
            "crop_y": crop_y,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "pad_left": 0,
            "pad_right": 0,
            "pad_top": 0,
            "pad_bottom": 0,
            "resize_from_w": 0,
            "resize_from_h": 0,
            "mode": mode,
        }

    # mode == "pad"
    # Add black borders to match target ratio.
    pad_left = 0
    pad_right = 0
    pad_top = 0
    pad_bottom = 0
    if current_ratio > target_ratio:
        # Too wide: pad height
        new_height = int(round(width / target_ratio))
        new_height = max(height, new_height)
        pad_total = new_height - height
        pad_top = pad_total // 2
        pad_bottom = pad_total - pad_top
        out_width, out_height = width, new_height
    else:
        # Too tall: pad width
        new_width = int(round(height * target_ratio))
        new_width = max(width, new_width)
        pad_total = new_width - width
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left
        out_width, out_height = new_width, height
    return {
        "out_width": out_width,
        "out_height": out_height,
        "crop_x": 0,
        "crop_y": 0,
        "crop_w": width,
        "crop_h": height,
        "pad_left": pad_left,
        "pad_right": pad_right,
        "pad_top": pad_top,
        "pad_bottom": pad_bottom,
        "resize_from_w": 0,
        "resize_from_h": 0,
        "mode": mode,
    }


class PSN_AspectRatioEnforcer:
    """Plan aspect-ratio adjustment (crop/pad/resize) for an image/latent tensor.

    Pure-logic node: takes input width/height (as plain ints) plus target ratio and mode,
    and emits the resulting dimensions and a JSON plan describing crop/pad/resize offsets.
    No tensor, file, network, or GPU access.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 512, "min": 1, "max": 16384, "step": 1}),
                "height": ("INT", {"default": 512, "min": 1, "max": 16384, "step": 1}),
                "target_ratio": ("FLOAT", {"default": 1.0, "min": 0.001, "max": 1000.0, "step": 0.001}),
                "mode": (list(_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("out_width", "out_height", "plan_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, width, height, target_ratio, mode):
        plan = _psn_compute_plan(width, height, target_ratio, mode)
        plan_json = json.dumps(plan, sort_keys=True)
        return (plan["out_width"], plan["out_height"], plan_json)


NODE_CLASS_MAPPINGS = {"PSN_AspectRatioEnforcer": PSN_AspectRatioEnforcer}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_AspectRatioEnforcer": "PSN Aspect Ratio Enforcer"}
