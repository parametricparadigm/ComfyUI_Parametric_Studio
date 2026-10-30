"""ParametricStudio – Error Handling & Retry Logic nodes.

Provides PSN_Error_Catcher and PSN_Retry_Switch for catching generation
failures and automatically retrying with adjusted parameters.
"""

import torch

CAT = "ParametricStudio/ErrorHandling"


def _clamp_int(v, lo, hi):
    """Clamp an integer into [lo, hi]."""
    try:
        v = int(v)
    except (TypeError, ValueError):
        v = lo
    return max(lo, min(hi, v))


class PSN_Error_Catcher:
    """Checks for errors in the output; if error, captures message."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output": ("*",),
                "error_flag": ("BOOLEAN", {"default": False}),
                "error_message": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("*", "STRING")
    RETURN_NAMES = ("success", "error_message")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, output, error_flag, error_message=""):
        if error_flag:
            msg = error_message if error_message else "Unknown error"
            # Return None as the output to signal failure
            return (None, msg)
        else:
            return (output, "")


class PSN_Retry_Switch:
    """If retry_count < max_retries, adjusts parameters and signals retry."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "error_message": ("STRING", {"default": ""}),
                "retry_count": ("INT", {"default": 0, "min": 0, "max": 100}),
                "max_retries": ("INT", {"default": 3, "min": 0, "max": 100}),
                "base_steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "base_cfg": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "PSN_BUNDLE")
    RETURN_NAMES = ("should_retry", "adjusted_params")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, error_message, retry_count, max_retries, base_steps=20, base_cfg=7.0):
        retry_count = _clamp_int(retry_count, 0, 100)
        max_retries = _clamp_int(max_retries, 0, 100)
        base_steps = _clamp_int(base_steps, 1, 150)
        base_cfg = max(1.0, min(30.0, float(base_cfg)))

        should_retry = retry_count < max_retries

        if should_retry:
            # Adjust parameters: reduce steps by 10% per retry, reduce cfg slightly
            factor = 1.0 - 0.1 * retry_count
            adjusted_steps = max(1, int(base_steps * factor))
            adjusted_cfg = max(1.0, base_cfg - 0.5 * retry_count)
            adjusted_params = {
                "steps": adjusted_steps,
                "cfg": adjusted_cfg,
                "retry_count": retry_count + 1,
                "error_message": error_message,
            }
        else:
            adjusted_params = {
                "steps": base_steps,
                "cfg": base_cfg,
                "retry_count": retry_count,
                "error_message": error_message,
            }

        return (should_retry, adjusted_params)


NODE_CLASS_MAPPINGS = {
    "PSN_Error_Catcher": PSN_Error_Catcher,
    "PSN_Retry_Switch": PSN_Retry_Switch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Error_Catcher": "PSN Error Catcher",
    "PSN_Retry_Switch": "PSN Retry Switch",
}
