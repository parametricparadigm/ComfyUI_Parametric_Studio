"""PSN_ColorSpaceGuard: pure-logic color-space validation and conversion planning.

This module implements the secure, pure-Python control plane for a color-space
guard. It does NOT touch GPU tensors, torch, or ComfyUI internals. Instead it
operates on plain numeric summaries (min/max/mean) and metadata strings, and
returns a validated plan (status, conversion ops, warnings) that a downstream
GPU/torch node can execute.

Inputs are plain values: numbers, strings, JSON text. No sockets, no file I/O,
no subprocess, no eval/exec.
"""

import json
import math

CAT = "ParametricStudio/Color"

_SPACES = ["sRGB", "Linear_sRGB", "ACEScg", "P3_D65", "Custom"]
_BIT_DEPTHS = [8, 10, 16, 32]

# Approximate gamma / linearization constants
_GAMMA_SRGB = 2.2
_GAMMA_ACES = 2.4


def _srgb_to_linear(v):
    """Convert a scalar sRGB value [0,1] to linear."""
    if v <= 0.04045:
        return v / 12.92
    return ((v + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(v):
    """Convert a scalar linear value to sRGB [0,1]."""
    if v <= 0.0031308:
        return 12.92 * v
    return 1.055 * (v ** (1.0 / 2.4)) - 0.055


def _aces_to_linear(v):
    """Approximate ACEScg to linear (simplified power curve)."""
    return v ** _GAMMA_ACES


def _linear_to_aces(v):
    """Approximate linear to ACEScg."""
    return v ** (1.0 / _GAMMA_ACES)


def _infer_space_from_range(vmin, vmax, metadata=None):
    """Infer likely color space from value range and optional metadata.

    Returns (inferred_space, confidence, reason).
    """
    if metadata:
        meta = metadata.strip().lower()
        for sp in _SPACES:
            if sp.lower() in meta:
                return sp, "high", "metadata match: %s" % sp
    if vmax > 1.0:
        return "Linear_sRGB", "medium", "values exceed 1.0, likely linear/HDR"
    if vmin < 0.0:
        return "Linear_sRGB", "low", "negative values suggest linear"
    if vmax <= 1.0 and vmin >= 0.0:
        return "sRGB", "low", "values in [0,1], likely sRGB"
    return "Custom", "low", "unrecognized range"


def _conversion_ops(from_space, to_space):
    """Return a list of conversion operation names needed."""
    ops = []
    if from_space == to_space:
        return ops
    # Normalize: convert from -> linear -> to
    if from_space != "Linear_sRGB":
        ops.append("linearize_%s" % from_space.lower())
    if to_space != "Linear_sRGB":
        ops.append("encode_%s" % to_space.lower())
    return ops


def _validate_bit_depth(bit_depth):
    """Validate bit depth is in the allowed set."""
    if bit_depth not in _BIT_DEPTHS:
        raise ValueError("bit_depth must be one of %s, got %r" % (_BIT_DEPTHS, bit_depth))


def _validate_space(space):
    """Validate color space is in the allowed set."""
    if space not in _SPACES:
        raise ValueError("expected_space must be one of %s, got %r" % (_SPACES, space))


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class PSN_ColorSpaceGuard:
    """Validates and plans color-space conversion for incoming image data.

    Pure-logic node: takes numeric summaries (min, max, mean) and metadata
    instead of actual tensors. Returns a conversion plan and status string.
    A downstream GPU node would execute the actual tensor conversion.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vmin": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "vmax": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "vmean": ("FLOAT", {"default": 0.5, "min": -1e9, "max": 1e9, "step": 0.001}),
                "expected_space": (_SPACES,),
                "bit_depth": (_BIT_DEPTHS,),
                "auto_fix": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "metadata": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("status", "inferred_space", "conversion_plan", "needs_conversion")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, vmin, vmax, vmean, expected_space, bit_depth, auto_fix, metadata=""):
        # Validate inputs
        _validate_space(expected_space)
        _validate_bit_depth(bit_depth)

        if not (vmin <= vmean <= vmax):
            raise ValueError("vmin (%.4f) must be <= vmean (%.4f) <= vmax (%.4f)" % (vmin, vmean, vmax))

        # Infer space from range and metadata
        inferred, confidence, reason = _infer_space_from_range(vmin, vmax, metadata)

        # Determine if conversion is needed
        needs_conversion = (inferred != expected_space)

        if not needs_conversion:
            status = "OK"
            plan = "no-op"
        elif auto_fix:
            ops = _conversion_ops(inferred, expected_space)
            status = "Converted from %s to %s" % (inferred, expected_space)
            plan = " -> ".join(ops) if ops else "direct"
        else:
            status = "MISMATCH: expected %s, inferred %s (confidence: %s)" % (expected_space, inferred, confidence)
            plan = "skipped (auto_fix=False)"

        return (status, inferred, plan, needs_conversion)


NODE_CLASS_MAPPINGS = {"PSN_ColorSpaceGuard": PSN_ColorSpaceGuard}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_ColorSpaceGuard": "Color Space Guard"}
