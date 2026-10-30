"""PSN_Uncond_Zero_Patch: A pure-logic configuration and validation node for the 'Uncond Zero' patch.

This module implements the secure, pure-Python logic required to configure and validate
the 'Uncond Zero' patch for ComfyUI. It does NOT modify the model or sampling loop directly
(as that requires torch/GPU access). Instead, it:
1. Validates the configuration (enable flag, safety checks).
2. Generates a structured patch descriptor (JSON-serializable) that a downstream
   torch-based node or ComfyUI hook would consume to actually skip the unconditional
   forward pass.
3. Provides a 'dry-run' simulation that reports what would be skipped.

The actual model patching (modifying the sampling loop to skip uncond forward pass)
is left to a separate torch-dependent node. This node ensures the configuration is
safe and well-formed before any GPU operation is attempted.

Inputs:
    - enable (BOOLEAN): Whether to enable the uncond-zero patch.
    - min_steps (INT): Minimum number of sampling steps before the patch is considered safe.
    - max_quality_drop (FLOAT): Maximum acceptable quality drop (0.0 to 1.0) before warning.

Outputs:
    - patch_config (STRING): JSON string describing the patch configuration.
    - enabled (BOOLEAN): Whether the patch is enabled and safe to apply.
    - warning (STRING): Any warning about potential quality drop or misconfiguration.
"""

import json
import re

CAT = "ParametricStudio/Patching"

# Allow-list of valid modes for the patch behavior
_VALID_MODES = ("skip_uncond", "zero_uncond", "disabled")

# Minimum steps before the patch is considered safe (heuristic)
_MIN_SAFE_STEPS = 10

# Maximum quality drop threshold before issuing a warning
_MAX_QUALITY_DROP_WARN = 0.15


def _validate_enable(enable):
    """Validate the enable flag. Returns (is_valid, error_message)."""
    if not isinstance(enable, bool):
        return False, "enable must be a boolean"
    return True, ""


def _validate_min_steps(min_steps):
    """Validate min_steps. Returns (is_valid, error_message)."""
    if not isinstance(min_steps, int) or isinstance(min_steps, bool):
        return False, "min_steps must be an integer"
    if min_steps < 0:
        return False, "min_steps must be non-negative"
    if min_steps > 10000:
        return False, "min_steps must be <= 10000"
    return True, ""


def _validate_max_quality_drop(max_quality_drop):
    """Validate max_quality_drop. Returns (is_valid, error_message)."""
    if not isinstance(max_quality_drop, (int, float)) or isinstance(max_quality_drop, bool):
        return False, "max_quality_drop must be a number"
    if max_quality_drop < 0.0 or max_quality_drop > 1.0:
        return False, "max_quality_drop must be between 0.0 and 1.0"
    return True, ""


def _build_patch_config(enable, min_steps, max_quality_drop):
    """Build the patch configuration dictionary.

    Returns a dict with keys:
        - enabled: bool
        - mode: str
        - min_steps: int
        - max_quality_drop: float
        - safe: bool (whether the config is considered safe)
        - warning: str
    """
    mode = "skip_uncond" if enable else "disabled"
    safe = enable and min_steps >= _MIN_SAFE_STEPS
    warning = ""
    if enable and min_steps < _MIN_SAFE_STEPS:
        warning = (
            f"min_steps ({min_steps}) is below the recommended threshold "
            f"({_MIN_SAFE_STEPS}). The uncond-zero patch may cause quality degradation "
            f"in early sampling steps."
        )
    elif enable and max_quality_drop > _MAX_QUALITY_DROP_WARN:
        warning = (
            f"max_quality_drop ({max_quality_drop}) exceeds the recommended threshold "
            f"({_MAX_QUALITY_DROP_WARN}). Significant quality drop may occur."
        )

    return {
        "enabled": enable,
        "mode": mode,
        "min_steps": min_steps,
        "max_quality_drop": float(max_quality_drop),
        "safe": safe,
        "warning": warning,
    }


def _simulate_skip(enable, total_steps, min_steps):
    """Simulate which steps would skip the unconditional forward pass.

    Returns a dict with:
        - total_steps: int
        - skipped_steps: list of step indices (0-based) where uncond is skipped
        - skipped_count: int
        - skipped_ratio: float
    """
    if not enable:
        return {
            "total_steps": total_steps,
            "skipped_steps": [],
            "skipped_count": 0,
            "skipped_ratio": 0.0,
        }

    skipped = []
    for step in range(total_steps):
        # Skip uncond forward pass for steps >= min_steps
        if step >= min_steps:
            skipped.append(step)

    ratio = len(skipped) / total_steps if total_steps > 0 else 0.0
    return {
        "total_steps": total_steps,
        "skipped_steps": skipped,
        "skipped_count": len(skipped),
        "skipped_ratio": ratio,
    }


class PSN_Uncond_Zero_Patch:
    """Configures and validates the Uncond Zero patch for skipping unconditional forward passes.

    This node does NOT modify the model. It produces a JSON patch descriptor and
    a safety assessment that a downstream torch-based node can use to actually
    patch the sampling loop.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enable": ("BOOLEAN", {"default": True}),
                "min_steps": ("INT", {"default": 10, "min": 0, "max": 10000, "step": 1}),
                "max_quality_drop": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "total_steps": ("INT", {"default": 20, "min": 1, "max": 10000, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("patch_config", "enabled", "warning", "simulation")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, enable, min_steps, max_quality_drop, total_steps=20):
        # Validate inputs
        ok, err = _validate_enable(enable)
        if not ok:
            return (json.dumps({"error": err}), False, err, "")

        ok, err = _validate_min_steps(min_steps)
        if not ok:
            return (json.dumps({"error": err}), False, err, "")

        ok, err = _validate_max_quality_drop(max_quality_drop)
        if not ok:
            return (json.dumps({"error": err}), False, err, "")

        if not isinstance(total_steps, int) or isinstance(total_steps, bool):
            return (json.dumps({"error": "total_steps must be an integer"}), False, "total_steps must be an integer", "")
        if total_steps < 1 or total_steps > 10000:
            return (json.dumps({"error": "total_steps must be between 1 and 10000"}), False, "total_steps must be between 1 and 10000", "")

        # Build config
        config = _build_patch_config(enable, min_steps, max_quality_drop)
        patch_config_json = json.dumps(config, indent=2)

        # Simulate
        sim = _simulate_skip(enable, total_steps, min_steps)
        sim_json = json.dumps(sim, indent=2)

        enabled = config["enabled"] and config["safe"]
        warning = config["warning"]

        return (patch_config_json, enabled, warning, sim_json)


NODE_CLASS_MAPPINGS = {
    "PSN_Uncond_Zero_Patch": PSN_Uncond_Zero_Patch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Uncond_Zero_Patch": "PSN Uncond Zero Patch",
}
