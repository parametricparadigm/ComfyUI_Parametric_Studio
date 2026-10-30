"""PSN_CV_VRAMGuard: pure-logic VRAM guard for heavy CV operations.

This module implements the decision logic for choosing a compute device
(cuda vs cpu) based on a reported VRAM usage value, without importing
torch or touching the GPU. The caller (a wrapper node or script) is
responsible for measuring actual memory (e.g. via torch.cuda.memory_allocated)
and passing the value in megabytes as a plain number.

Inputs are plain values (numbers, strings); no file, network, subprocess,
eval/exec, or dunder tricks are used.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/CV"

_DEVICES = ("auto", "cuda", "cpu")


class PSN_CV_VRAMGuard:
    """Decide whether a heavy CV op should run on cuda or cpu based on VRAM usage."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vram_used_mb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 1.0}),
                "threshold_mb": ("INT", {"default": 500, "min": 0, "max": 1000000, "step": 1}),
                "device": (_DEVICES,),
            },
            "optional": {
                "vram_total_mb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 1.0}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("device_str", "warning")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, vram_used_mb, threshold_mb, device, vram_total_mb=0.0):
        """Return (device_str, warning).

        Logic:
        - If device is "cpu", always return "cpu" with no warning.
        - If device is "cuda", always return "cuda" with no warning.
        - If device is "auto":
            - If vram_used_mb >= threshold_mb, return "cpu" with a warning.
            - Otherwise return "cuda" with empty warning.
        """
        if not isinstance(vram_used_mb, (int, float)):
            raise TypeError("vram_used_mb must be a number")
        if not isinstance(threshold_mb, (int, float)):
            raise TypeError("threshold_mb must be a number")
        if vram_used_mb < 0:
            raise ValueError("vram_used_mb must be non-negative")
        if threshold_mb < 0:
            raise ValueError("threshold_mb must be non-negative")
        if device not in _DEVICES:
            raise ValueError("device must be one of: auto, cuda, cpu")

        if device == "cpu":
            return ("cpu", "")
        if device == "cuda":
            return ("cuda", "")

        # device == "auto"
        if vram_used_mb >= threshold_mb:
            warning = (
                f"VRAM usage {vram_used_mb:.1f} MB meets or exceeds threshold "
                f"{threshold_mb:.1f} MB; falling back to CPU."
            )
            return ("cpu", warning)
        return ("cuda", "")


NODE_CLASS_MAPPINGS = {
    "PSN_CV_VRAMGuard": PSN_CV_VRAMGuard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CV_VRAMGuard": "CV VRAM Guard",
}
