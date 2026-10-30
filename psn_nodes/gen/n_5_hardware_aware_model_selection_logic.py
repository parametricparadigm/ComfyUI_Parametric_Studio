"""
Hardware-Aware Model Selection Logic (pure-logic, secure-by-design).

This module implements the *decision* logic for hardware-aware model selection
without touching GPU, torch, ComfyUI internals, or any I/O.

- PSN_VRAM_Checker: takes a reported free-VRAM value (in MB) and a threshold,
  and returns whether the free VRAM meets the threshold. In a real ComfyUI
  environment the free VRAM would be obtained from torch.cuda.mem_get_info();
  here we accept it as a plain INT input so the node is testable and safe.
- PSN_Model_Selector: given a boolean flag and two model identifiers (strings
  standing in for MODEL objects), selects the appropriate model.

No torch, no network, no file access, no subprocess.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Hardware"

# ---------------------------------------------------------------------------
# PSN_VRAM_Checker
# ---------------------------------------------------------------------------

class PSN_VRAM_Checker:
    """
    Check whether reported free VRAM meets a threshold.

    Inputs:
        free_vram_mb (INT): Free VRAM in megabytes, as reported by the host
                            (e.g. from torch.cuda.mem_get_info()).
        threshold_mb (INT): Minimum free VRAM required to use the large model.

    Outputs:
        has_vram (BOOLEAN): True if free_vram_mb >= threshold_mb.
        free_vram_mb (INT): The free VRAM value passed through.
        reason (STRING): Human-readable explanation of the decision.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "free_vram_mb": ("INT", {"default": 0, "min": 0, "max": 10**9, "step": 1}),
                "threshold_mb": ("INT", {"default": 4096, "min": 0, "max": 10**9, "step": 1}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "INT", "STRING")
    RETURN_NAMES = ("has_vram", "free_vram_mb", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, free_vram_mb, threshold_mb):
        if not isinstance(free_vram_mb, int) or not isinstance(threshold_mb, int):
            raise ValueError("free_vram_mb and threshold_mb must be integers")
        if free_vram_mb < 0 or threshold_mb < 0:
            raise ValueError("VRAM values must be non-negative")
        has_vram = free_vram_mb >= threshold_mb
        if has_vram:
            reason = f"Free VRAM {free_vram_mb} MB meets threshold {threshold_mb} MB"
        else:
            reason = f"Free VRAM {free_vram_mb} MB below threshold {threshold_mb} MB"
        return (has_vram, free_vram_mb, reason)


# ---------------------------------------------------------------------------
# PSN_Model_Selector
# ---------------------------------------------------------------------------

class PSN_Model_Selector:
    """
    Select a model based on a boolean hardware flag.

    In a full ComfyUI setup the inputs would be MODEL objects; here we use
    STRING identifiers to keep the node pure-logic and testable.

    Inputs:
        has_vram (BOOLEAN): True if sufficient VRAM is available.
        model_small (STRING): Identifier/name of the small model variant.
        model_large (STRING): Identifier/name of the large model variant.

    Outputs:
        selected_model (STRING): The chosen model identifier.
        reason (STRING): Explanation of the selection.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "has_vram": ("BOOLEAN", {"default": False}),
                "model_small": ("STRING", {"default": "small_model", "multiline": False}),
                "model_large": ("STRING", {"default": "large_model", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("selected_model", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, has_vram, model_small, model_large):
        if not isinstance(has_vram, bool):
            raise ValueError("has_vram must be a boolean")
        if not isinstance(model_small, str) or not isinstance(model_large, str):
            raise ValueError("model_small and model_large must be strings")
        if has_vram:
            selected = model_large
            reason = "Sufficient VRAM: selected large model"
        else:
            selected = model_small
            reason = "Insufficient VRAM: selected small model"
        return (selected, reason)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_Checker": PSN_VRAM_Checker,
    "PSN_Model_Selector": PSN_Model_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_Checker": "PSN VRAM Checker",
    "PSN_Model_Selector": "PSN Model Selector",
}
