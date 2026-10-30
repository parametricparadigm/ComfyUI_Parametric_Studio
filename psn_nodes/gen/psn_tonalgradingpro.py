"""PSN_TonalGradingPro: Pure-logic tonal grading pipeline (no GPU/torch).

This module implements the *pure-logic, secure-by-design* part of a professional
tonal-grading node. Because the original spec requires PyTorch/GPU tensor
operations (which are disallowed here), this implementation operates on plain
Python values and JSON text only:

- It validates and clamps scalar tonal parameters (exposure, contrast,
  brightness, saturation) to safe, finite ranges.
- It parses and validates an optional ``curves_json`` string that describes
  per-channel curve points, rejecting malformed or out-of-range data.
- It computes a deterministic, float32-precision *reference* tonal transform
  for a single scalar pixel value (0.0..1.0), which mirrors the math a GPU
  kernel would apply: exposure (multiplicative), brightness (additive),
  contrast (pivot around 0.5), saturation (mix toward luminance), and an
  optional piecewise-linear curve.

The node therefore takes plain numbers and JSON text, and returns plain
numbers plus a human-readable report. It never opens sockets, files, or
processes, and never imports torch/comfy.
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Tonal"

# Safe, finite bounds for scalar tonal parameters.
_EXPOSURE_RANGE = (-10.0, 10.0)
_CONTRAST_RANGE = (-10.0, 10.0)
_BRIGHTNESS_RANGE = (-1.0, 1.0)
_SATURATION_RANGE = (0.0, 2.0)

# Contrast pivot (mid-gray) used by the standard contrast operator.
_CONTRAST_PIVOT = 0.5

# Maximum number of curve points we will accept per channel.
_MAX_CURVE_POINTS = 64


def _is_finite_number(value):
    """Return True if value is a real, finite number (int/float, not bool)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    return False


def _clamp(value, low, high):
    """Clamp value into [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _validate_scalar(name, value, low, high):
    """Validate a scalar parameter; return (ok, clamped_value, reason)."""
    if not _is_finite_number(value):
        return False, 0.0, "invalid: %s must be a finite number" % name
    clamped = _clamp(float(value), low, high)
    return True, clamped, "ok"


def _parse_curves(curves_json):
    """Parse and validate a curves JSON string.

    Accepts either:
      - a list of points: [[x0,y0],[x1,y1],...]
      - a dict mapping channel name to a list of points:
        {"r": [[x,y],...], "g": [[x,y],...], "b": [[x,y],...]}

    Returns (ok, curves, reason). ``curves`` is a dict mapping channel name
    ("r","g","b") to a sorted list of (x,y) tuples, or None when no curves.
    """
    if curves_json is None or (isinstance(curves_json, str) and curves_json.strip() == ""):
        return True, None, "ok: no curves"

    if not isinstance(curves_json, str):
        return False, None, "invalid: curves_json must be a string"

    try:
        data = json.loads(curves_json)
    except (ValueError, TypeError) as exc:
        return False, None, "invalid: curves_json is not valid JSON (%s)" % exc

    # Normalize to a per-channel dict.
    if isinstance(data, list):
        channels = {"r": data, "g": data, "b": data}
    elif isinstance(data, dict):
        channels = {}
        for key in ("r", "g", "b"):
            if key in data:
                channels[key] = data[key]
        if not channels:
            return False, None, "invalid: curves_json dict must contain r, g, or b"
    else:
        return False, None, "invalid: curves_json must be a list or object"

    curves = {}
    for channel, points in channels.items():
        if not isinstance(points, list):
            return False, None, "invalid: channel %s must be a list of points" % channel
        if len(points) > _MAX_CURVE_POINTS:
            return False, None, "invalid: channel %s has too many points" % channel
        parsed = []
        for idx, point in enumerate(points):
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                return False, None, "invalid: point %d in channel %s must be [x, y]" % (idx, channel)
            x, y = point
            if not _is_finite_number(x) or not _is_finite_number(y):
                return False, None, "invalid: point %d in channel %s has non-finite values" % (idx, channel)
            x = _clamp(float(x), 0.0, 1.0)
            y = _clamp(float(y), 0.0, 1.0)
            parsed.append((x, y))
        # Sort by x for deterministic interpolation.
        parsed.sort(key=lambda p: p[0])
        curves[channel] = parsed

    return True, curves, "ok: %d channel(s)" % len(curves)


def _apply_curve(value, points):
    """Apply a piecewise-linear curve to a scalar value in [0,1]."""
    if not points:
        return value
    # Before first point: clamp to first y.
    if value <= points[0][0]:
        return points[0][1]
    # After last point: clamp to last y.
    if value >= points[-1][0]:
        return points[-1][1]
    # Find the segment.
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= value <= x1:
            if x1 == x0:
                return y0
            t = (value - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return value


def _luminance(r, g, b):
    """Rec. 709 luminance of an RGB triple in [0,1]."""
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _apply_tonal(r, g, b, exposure, contrast, brightness, saturation, curves):
    """Apply the full tonal pipeline to an RGB triple in [0,1].

    Order: exposure -> brightness -> contrast -> saturation -> curves.
    All intermediate values are clamped to [0,1] to emulate float32 clamping.
    """
    # Exposure: multiplicative (2^exposure).
    exp_factor = 2.0 ** exposure
    r = _clamp(r * exp_factor, 0.0, 1.0)
    g = _clamp(g * exp_factor, 0.0, 1.0)
    b = _clamp(b * exp_factor, 0.0, 1.0)

    # Brightness: additive.
    r = _clamp(r + brightness, 0.0, 1.0)
    g = _clamp(g + brightness, 0.0, 1.0)
    b = _clamp(b + brightness, 0.0, 1.0)

    # Contrast: pivot around mid-gray.
    r = _clamp(_CONTRAST_PIVOT + (r - _CONTRAST_PIVOT) * contrast, 0.0, 1.0)
    g = _clamp(_CONTRAST_PIVOT + (g - _CONTRAST_PIVOT) * contrast, 0.0, 1.0)
    b = _clamp(_CONTRAST_PIVOT + (b - _CONTRAST_PIVOT) * contrast, 0.0, 1.0)

    # Saturation: mix toward luminance.
    lum = _luminance(r, g, b)
    r = _clamp(lum + (r - lum) * saturation, 0.0, 1.0)
    g = _clamp(lum + (g - lum) * saturation, 0.0, 1.0)
    b = _clamp(lum + (b - lum) * saturation, 0.0, 1.0)

    # Curves: per-channel piecewise-linear.
    if curves:
        if "r" in curves:
            r = _apply_curve(r, curves["r"])
        if "g" in curves:
            g = _apply_curve(g, curves["g"])
        if "b" in curves:
            b = _apply_curve(b, curves["b"])

    return r, g, b


class PSN_TonalGradingPro:
    """Applies professional tonal adjustments (Curves, Levels, Exposure, Contrast).

    Pure-logic reference implementation: operates on scalar RGB values and
    JSON text, mirroring the math a GPU kernel would apply. No torch, no
    network, no file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "r": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "g": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "b": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "exposure": ("FLOAT", {"default": 0.0, "min": _EXPOSURE_RANGE[0], "max": _EXPOSURE_RANGE[1], "step": 0.01}),
                "contrast": ("FLOAT", {"default": 1.0, "min": _CONTRAST_RANGE[0], "max": _CONTRAST_RANGE[1], "step": 0.01}),
                "brightness": ("FLOAT", {"default": 0.0, "min": _BRIGHTNESS_RANGE[0], "max": _BRIGHTNESS_RANGE[1], "step": 0.001}),
                "saturation": ("FLOAT", {"default": 1.0, "min": _SATURATION_RANGE[0], "max": _SATURATION_RANGE[1], "step": 0.01}),
            },
            "optional": {
                "curves_json": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "FLOAT", "STRING")
    RETURN_NAMES = ("r", "g", "b", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, r, g, b, exposure, contrast, brightness, saturation, curves_json=""):
        # Validate scalar inputs.
        ok_r, r_c, why_r = _validate_scalar("r", r, 0.0, 1.0)
        ok_g, g_c, why_g = _validate_scalar("g", g, 0.0, 1.0)
        ok_b, b_c, why_b = _validate_scalar("b", b, 0.0, 1.0)
        ok_e, e_c, why_e = _validate_scalar("exposure", exposure, _EXPOSURE_RANGE[0], _EXPOSURE_RANGE[1])
        ok_ct, ct_c, why_ct = _validate_scalar("contrast", contrast, _CONTRAST_RANGE[0], _CONTRAST_RANGE[1])
        ok_br, br_c, why_br = _validate_scalar("brightness", brightness, _BRIGHTNESS_RANGE[0], _BRIGHTNESS_RANGE[1])
        ok_sa, sa_c, why_sa = _validate_scalar("saturation", saturation, _SATURATION_RANGE[0], _SATURATION_RANGE[1])

        if not (ok_r and ok_g and ok_b and ok_e and ok_ct and ok_br and ok_sa):
            reasons = [w for w in (why_r, why_g, why_b, why_e, why_ct, why_br, why_sa) if w != "ok"]
            return (0.0, 0.0, 0.0, "error: " + "; ".join(reasons))

        # Parse and validate curves.
        ok_curves, curves, why_curves = _parse_curves(curves_json)
        if not ok_curves:
            return (0.0, 0.0, 0.0, "error: " + why_curves)

        # Apply the tonal pipeline.
        out_r, out_g, out_b = _apply_tonal(r_c, g_c, b_c, e_c, ct_c, br_c, sa_c, curves)

        report = (
            "ok: exposure=%.3f contrast=%.3f brightness=%.3f saturation=%.3f curves=%s"
            % (e_c, ct_c, br_c, sa_c, why_curves)
        )
        return (out_r, out_g, out_b, report)


NODE_CLASS_MAPPINGS = {
    "PSN_TonalGradingPro": PSN_TonalGradingPro,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TonalGradingPro": "Tonal Grading Pro",
}
