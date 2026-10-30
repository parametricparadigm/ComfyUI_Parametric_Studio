"""
PSN_FreeU_Patch: Pure-logic configuration and validation for FreeU (Free U-Net) patching.

This module implements the secure, pure-Python logic portion of a FreeU patching node.
Since actual model patching requires torch and ComfyUI internals (which are prohibited
by the constraints), this node:
  1. Validates the four FreeU scale parameters (b1, b2, s1, s2) against safe ranges.
  2. Produces a deterministic, JSON-serializable patch descriptor that a downstream
     torch-based executor could consume to apply the actual weight scaling.
  3. Reports whether the configuration is valid and why, so users can catch
     over-sharpening or artifact-inducing settings before they reach the model.

The node does NOT open sockets, access files, use eval/exec, or import torch/comfy.
It takes plain numbers and returns plain values (booleans, strings, JSON text).
"""

import json
import math

# Safe ranges for FreeU scale parameters.
# Values outside these ranges are likely to cause over-sharpening or artifacts.
_B1_MIN, _B1_MAX = 0.5, 2.0
_B2_MIN, _B2_MAX = 0.5, 2.0
_S1_MIN, _S1_MAX = 0.1, 1.5
_S2_MIN, _S2_MAX = 0.0, 1.0

# Default values as specified
_B1_DEFAULT = 1.1
_B2_DEFAULT = 1.2
_S1_DEFAULT = 0.9
_S2_DEFAULT = 0.2

# Maximum absolute value to guard against absurd inputs
_MAX_ABS = 1e6


def _validate_scale(name, value, lo, hi):
    """Validate a single scale parameter. Returns (ok, reason)."""
    if not isinstance(value, (int, float)):
        return False, f"{name} must be a number, got {type(value).__name__}"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return False, f"{name} must be finite, got {value}"
    if abs(value) > _MAX_ABS:
        return False, f"{name} is too large in magnitude: {value}"
    if value < lo:
        return False, f"{name}={value} is below minimum {lo}"
    if value > hi:
        return False, f"{name}={value} is above maximum {hi}"
    return True, f"{name}={value} is within safe range [{lo}, {hi}]"


def build_freeu_descriptor(b1, b2, s1, s2):
    """
    Build a JSON-serializable descriptor for the FreeU patch.
    Returns (ok, descriptor_dict, reason_string).
    """
    checks = [
        _validate_scale("b1", b1, _B1_MIN, _B1_MAX),
        _validate_scale("b2", b2, _B2_MIN, _B2_MAX),
        _validate_scale("s1", s1, _S1_MIN, _S1_MAX),
        _validate_scale("s2", s2, _S2_MIN, _S2_MAX),
    ]
    reasons = []
    all_ok = True
    for ok, why in checks:
        if not ok:
            all_ok = False
            reasons.append(why)
        else:
            reasons.append(why)

    if not all_ok:
        return False, None, "; ".join(reasons)

    descriptor = {
        "patch_type": "freeu",
        "b1": float(b1),
        "b2": float(b2),
        "s1": float(s1),
        "s2": float(s2),
        "target_architecture": "unet",
        "note": "Apply b1/b2 to early attention blocks, s1/s2 to skip connections.",
    }
    return True, descriptor, "; ".join(reasons)


class PSN_FreeU_Patch:
    """
    Validates FreeU scale parameters and produces a patch descriptor.

    Inputs:
        b1 (FLOAT): Block 1 scale (default 1.1)
        b2 (FLOAT): Block 2 scale (default 1.2)
        s1 (FLOAT): Skip 1 scale (default 0.9)
        s2 (FLOAT): Skip 2 scale (default 0.2)

    Outputs:
        valid (BOOLEAN): Whether the configuration is within safe ranges.
        descriptor (STRING): JSON text describing the FreeU patch to apply.
        reason (STRING): Human-readable explanation of validation result.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "b1": ("FLOAT", {"default": _B1_DEFAULT, "min": 0.0, "max": 5.0, "step": 0.01}),
                "b2": ("FLOAT", {"default": _B2_DEFAULT, "min": 0.0, "max": 5.0, "step": 0.01}),
                "s1": ("FLOAT", {"default": _S1_DEFAULT, "min": 0.0, "max": 3.0, "step": 0.01}),
                "s2": ("FLOAT", {"default": _S2_DEFAULT, "min": 0.0, "max": 2.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("valid", "descriptor", "reason")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/FreeU"

    def run(self, b1, b2, s1, s2):
        ok, descriptor, reason = build_freeu_descriptor(b1, b2, s1, s2)
        if ok:
            descriptor_json = json.dumps(descriptor, sort_keys=True)
        else:
            descriptor_json = json.dumps({"error": reason}, sort_keys=True)
        return (ok, descriptor_json, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_FreeU_Patch": PSN_FreeU_Patch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FreeU_Patch": "FreeU Patch (Config)",
}
