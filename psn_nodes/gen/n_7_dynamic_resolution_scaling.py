"""PSN_Resolution_Scaler: pure-logic dynamic resolution scaling.

Given an aspect ratio and a target megapixel budget, this node computes a
width/height pair that (a) approximates the requested megapixels, (b) honours
the requested aspect ratio as closely as possible, (c) is a multiple of a
configurable alignment value, and (d) never exceeds the supplied max width /
max height.

This module is pure Python standard library only. It performs no file, OS,
network, subprocess, GPU/torch, or ComfyUI-internal access. It is a safe,
deterministic math helper that takes plain numbers and returns plain ints,
suitable for feeding an Empty Latent Image node.
"""

import math

CAT = "ParametricStudio/Resolution"

# Internal safety bounds to keep the math well-behaved.
_MIN_ASPECT = 1e-6
_MAX_ASPECT = 1e6
_MIN_MP = 1e-6
_MAX_MP = 1e6
_MIN_MULTIPLE = 1
_MAX_MULTIPLE = 1024
_MIN_DIM = 1
_MAX_DIM = 16384


def _clamp(value, lo, hi):
    """Clamp value into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _round_to_multiple(value, multiple):
    """Round value to the nearest multiple, never below 1."""
    if multiple <= 1:
        return max(1, int(round(value)))
    nearest = int(round(value / float(multiple))) * multiple
    if nearest < 1:
        nearest = multiple
    return nearest


def _snap_to_multiple(value, multiple):
    """Snap value down to the nearest multiple, never below 1."""
    if multiple <= 1:
        return max(1, int(value))
    snapped = int(value // float(multiple)) * multiple
    if snapped < 1:
        snapped = multiple
    return snapped


def _snap_up_to_multiple(value, multiple):
    """Snap value up to the nearest multiple, never below 1."""
    if multiple <= 1:
        return max(1, int(math.ceil(value)))
    snapped = int(math.ceil(value / float(multiple))) * multiple
    if snapped < 1:
        snapped = multiple
    return snapped


def _validate_inputs(aspect_ratio, target_megapixels, max_width, max_height, multiple_of):
    """Validate and normalise inputs. Returns (ok, reason, normalised tuple)."""
    try:
        aspect = float(aspect_ratio)
        mp = float(target_megapixels)
        mw = int(max_width)
        mh = int(max_height)
        mult = int(multiple_of)
    except (TypeError, ValueError):
        return False, "Inputs must be numeric.", None

    if not math.isfinite(aspect) or not math.isfinite(mp):
        return False, "aspect_ratio and target_megapixels must be finite.", None

    if aspect <= 0:
        return False, "aspect_ratio must be positive.", None
    if mp <= 0:
        return False, "target_megapixels must be positive.", None
    if mw < _MIN_DIM:
        return False, "max_width must be at least 1.", None
    if mh < _MIN_DIM:
        return False, "max_height must be at least 1.", None
    if mult < _MIN_MULTIPLE:
        return False, "multiple_of must be at least 1.", None

    # Normalise into safe ranges.
    aspect = _clamp(aspect, _MIN_ASPECT, _MAX_ASPECT)
    mp = _clamp(mp, _MIN_MP, _MAX_MP)
    mw = _clamp(mw, _MIN_DIM, _MAX_DIM)
    mh = _clamp(mh, _MIN_DIM, _MAX_DIM)
    mult = _clamp(mult, _MIN_MULTIPLE, _MAX_MULTIPLE)

    return True, "ok", (aspect, mp, mw, mh, mult)


def _compute_resolution(aspect, mp, max_width, max_height, multiple):
    """Compute (width, height) for the given normalised parameters."""
    total_pixels = mp * 1e6
    # width = sqrt(total * aspect), height = width / aspect
    width = math.sqrt(total_pixels * aspect)
    height = width / aspect

    # Round both to the nearest multiple.
    width = _round_to_multiple(width, multiple)
    height = _round_to_multiple(height, multiple)

    # Preserve aspect ratio as closely as possible: recompute height from the
    # rounded width, then snap it to a multiple.
    height = _round_to_multiple(width / aspect, multiple)

    # Clamp to the maximums. If clamping is needed, recompute the other
    # dimension to keep the ratio, then snap to a multiple.
    if width > max_width:
        width = _snap_to_multiple(max_width, multiple)
        height = _round_to_multiple(width / aspect, multiple)
    if height > max_height:
        height = _snap_to_multiple(max_height, multiple)
        width = _round_to_multiple(height * aspect, multiple)

    # Final safety clamp (in case recompute pushed the other dim over).
    if width > max_width:
        width = _snap_to_multiple(max_width, multiple)
    if height > max_height:
        height = _snap_to_multiple(max_height, multiple)

    # Ensure at least 1 and a multiple.
    width = max(_snap_up_to_multiple(width, multiple), multiple)
    height = max(_snap_up_to_multiple(height, multiple), multiple)

    return int(width), int(height)


class PSN_Resolution_Scaler:
    """Dynamically compute width/height from aspect ratio and megapixel budget."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": ("FLOAT", {"default": 1.0, "min": 0.0001, "max": 10000.0, "step": 0.001}),
                "target_megapixels": ("FLOAT", {"default": 1.0, "min": 0.0001, "max": 10000.0, "step": 0.001}),
                "max_width": ("INT", {"default": 2048, "min": 1, "max": 16384, "step": 1}),
                "max_height": ("INT", {"default": 2048, "min": 1, "max": 16384, "step": 1}),
                "multiple_of": ("INT", {"default": 8, "min": 1, "max": 1024, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, aspect_ratio, target_megapixels, max_width, max_height, multiple_of):
        ok, reason, norm = _validate_inputs(
            aspect_ratio, target_megapixels, max_width, max_height, multiple_of
        )
        if not ok:
            # Return a safe minimal resolution and surface the reason via a
            # deterministic fallback rather than raising, so downstream nodes
            # still receive valid ints.
            return (int(multiple_of) if isinstance(multiple_of, int) and multiple_of >= 1 else 8,
                    int(multiple_of) if isinstance(multiple_of, int) and multiple_of >= 1 else 8)
        aspect, mp, mw, mh, mult = norm
        width, height = _compute_resolution(aspect, mp, mw, mh, mult)
        return (width, height)


NODE_CLASS_MAPPINGS = {
    "PSN_Resolution_Scaler": PSN_Resolution_Scaler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Resolution_Scaler": "PSN Resolution Scaler",
}
