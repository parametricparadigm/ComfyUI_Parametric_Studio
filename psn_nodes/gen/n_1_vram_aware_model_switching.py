"""VRAM-Aware Model Switching for ComfyUI (ParametricStudio).

Provides a lightweight node that selects between a high-resolution and a
low-resolution model based on a boolean VRAM check signal.  The idea is to
prevent OOM on large GPUs by routing to the smaller model when the VRAM
check reports insufficient headroom.

Nodes:
    PSN_VRAM_Check          - reports whether enough VRAM is available
    PSN_VRAM_Model_Switch   - picks high_res_model or low_res_model
"""

import torch

CAT = "ParametricStudio/Model"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vram_available_gb() -> float:
    """Return the amount of free VRAM in GB, or 0.0 when no CUDA device.

    Uses torch.cuda.mem_get_info when available; falls back to 0.0 so the
    node degrades gracefully on CPU-only machines.
    """
    try:
        if torch.cuda.is_available():
            free, _total = torch.cuda.mem_get_info()
            return free / (1024 ** 3)
    except Exception:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# Node 1: VRAM Check
# ---------------------------------------------------------------------------

class PSN_VRAM_Check:
    """Check whether at least *threshold_gb* of VRAM is free.

    Outputs a BOOLEAN that can drive PSN_VRAM_Model_Switch.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "threshold_gb": (
                    "FLOAT",
                    {"default": 8.0, "min": 0.0, "max": 512.0, "step": 0.5},
                ),
            },
            "optional": {
                "force_result": (
                    "BOOLEAN",
                    {"default": False},
                ),
            },
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("vram_ok",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, threshold_gb: float, force_result: bool = False) -> tuple:
        if force_result:
            return (True,)
        if not force_result and threshold_gb < 0:
            raise ValueError("threshold_gb must be >= 0")
        free_gb = _vram_available_gb()
        return (free_gb >= threshold_gb,)


# ---------------------------------------------------------------------------
# Node 2: VRAM Model Switch
# ---------------------------------------------------------------------------

class PSN_VRAM_Model_Switch:
    """Select high_res_model when *vram_check* is True, else low_res_model.

    Both model inputs are passed through unchanged (no in-place mutation).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "high_res_model": ("MODEL",),
                "low_res_model": ("MODEL",),
                "vram_check": ("BOOLEAN",),
            },
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("selected_model",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, high_res_model, low_res_model, vram_check: bool) -> tuple:
        if not isinstance(vram_check, bool):
            raise TypeError("vram_check must be a boolean")
        if high_res_model is None:
            raise ValueError("high_res_model must not be None")
        if low_res_model is None:
            raise ValueError("low_res_model must not be None")
        selected = high_res_model if vram_check else low_res_model
        return (selected,)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_Check": PSN_VRAM_Check,
    "PSN_VRAM_Model_Switch": PSN_VRAM_Model_Switch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_Check": "VRAM Check",
    "PSN_VRAM_Model_Switch": "VRAM Model Switch",
}
