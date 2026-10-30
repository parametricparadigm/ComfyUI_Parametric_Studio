"""PSN_VRAM_Guard: pure-logic VRAM threshold guard.

This module implements a secure, dependency-free guard that compares a
reported VRAM usage value against a configured threshold. It does NOT
touch the GPU, read system memory, open sockets, or perform any I/O.
It is intended to be wired into a ComfyUI workflow where an upstream
node supplies `current_usage` (in GB) and this node decides whether
generation should proceed.

Inputs (plain values):
    threshold (float, GB)   - maximum allowed VRAM usage.
    current_usage (float, GB) - reported current VRAM usage.

Outputs:
    is_safe (bool)   - True when current_usage <= threshold.
    warning (str)    - human-readable warning when unsafe, else "".
"""

import math

CAT = "ParametricStudio/Guard"


def _validate_finite_number(value, name):
    """Return (ok, reason, coerced_value).

    Accepts int/float (not bool), rejects NaN/Inf, and coerces to float.
    """
    if isinstance(value, bool):
        return False, f"{name} must be a number, got bool", None
    if isinstance(value, (int, float)):
        num = float(value)
        if math.isnan(num) or math.isinf(num):
            return False, f"{name} must be finite, got {value!r}", None
        return True, "", num
    if isinstance(value, str):
        try:
            num = float(value.strip())
        except (ValueError, AttributeError):
            return False, f"{name} could not be parsed as a number: {value!r}", None
        if math.isnan(num) or math.isinf(num):
            return False, f"{name} must be finite, got {value!r}", None
        return True, "", num
    return False, f"{name} must be a number, got {type(value).__name__}", None


class PSN_VRAM_Guard:
    """Monitor VRAM usage and flag generation as unsafe when over threshold."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "threshold": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 1e9, "step": 0.1}),
                "current_usage": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_safe", "warning")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, threshold, current_usage):
        ok_t, why_t, thr = _validate_finite_number(threshold, "threshold")
        if not ok_t:
            return (False, f"Invalid input: {why_t}")

        ok_u, why_u, usage = _validate_finite_number(current_usage, "current_usage")
        if not ok_u:
            return (False, f"Invalid input: {why_u}")

        if thr < 0.0:
            return (False, f"Invalid input: threshold must be >= 0, got {thr}")
        if usage < 0.0:
            return (False, f"Invalid input: current_usage must be >= 0, got {usage}")

        if usage > thr:
            headroom = thr - usage
            warning = (
                f"VRAM guard: usage {usage:.3f} GB exceeds threshold {thr:.3f} GB "
                f"(over by {usage - thr:.3f} GB). Pause generation."
            )
            return (False, warning)

        return (True, "")


NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_Guard": PSN_VRAM_Guard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_Guard": "VRAM Guard",
}
