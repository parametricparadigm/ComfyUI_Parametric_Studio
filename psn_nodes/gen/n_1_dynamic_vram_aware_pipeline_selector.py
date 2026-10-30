"""Dynamic VRAM-Aware Pipeline Selector (pure-logic, secure-by-design).

This module implements the *decision* logic for choosing between a lightweight
and a heavy pipeline based on available VRAM.  It does NOT touch the GPU,
torch, psutil, or any network/file/OS resource.  Instead it exposes:

  * PSN_VRAM_Query        -- a pure function that takes a *pre-supplied*
                             (free_gb, total_gb) pair and computes utilization.
                             In a real ComfyUI build the caller would feed the
                             numbers obtained from torch.cuda / psutil; here
                             the numbers are plain floats passed in as inputs.
  * PSN_Pipeline_Selector -- compares free_vram_gb against two thresholds and
                             returns the selected pipeline id plus a human-
                             readable reason.

All inputs are plain Python values (int, float, str, bool).  No sockets, no
subprocess, no file I/O, no eval/exec.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/VRAM"

# Sentinel pipeline id used when free VRAM is below the light threshold.
_FALLBACK_PIPELINE_ID = "low-res"

# Minimum sensible VRAM values (GB) to avoid degenerate inputs.
_MIN_VRAM_GB = 0.0
_MAX_VRAM_GB = 1e6  # 1 PB – far beyond any real GPU


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_vram(value: Any, name: str) -> float:
    """Validate that *value* is a finite, non-negative float representing GB."""
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    v = float(value)
    if math.isnan(v) or math.isinf(v):
        raise ValueError(f"{name} must be a finite number, got {v!r}")
    if v < _MIN_VRAM_GB:
        raise ValueError(f"{name} must be >= {_MIN_VRAM_GB}, got {v}")
    if v > _MAX_VRAM_GB:
        raise ValueError(f"{name} must be <= {_MAX_VRAM_GB}, got {v}")
    return v


def _validate_threshold(value: Any, name: str) -> float:
    """Validate a threshold value (non-negative finite float)."""
    return _validate_vram(value, name)


def _validate_pipeline_id(value: Any, name: str) -> str:
    """Validate that a pipeline id is a non-empty string."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string, got {type(value).__name__}")
    s = value.strip()
    if not s:
        raise ValueError(f"{name} must be a non-empty string")
    return s


def _validate_device_index(value: Any) -> int:
    """Validate device index is a non-negative integer."""
    if isinstance(value, bool):  # bool is subclass of int – reject explicitly
        raise ValueError("device_index must be an integer, not a bool")
    if not isinstance(value, int):
        raise ValueError(f"device_index must be an integer, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"device_index must be >= 0, got {value}")
    return value


# ---------------------------------------------------------------------------
# Node 1: PSN_VRAM_Query
# ---------------------------------------------------------------------------

class PSN_VRAM_Query:
    """Query (or use cached) VRAM status and compute utilization.

    In a full ComfyUI build the caller would obtain *free_gb* and *total_gb*
    from torch.cuda.mem_get_info() or psutil.  This node accepts those numbers
    as plain float inputs so the logic is testable without a GPU.

    *refresh* is accepted for API compatibility; in this pure-logic build it
    has no side-effect (there is no cache to invalidate).
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "free_vram_gb": ("FLOAT", {"default": 0.0, "min": _MIN_VRAM_GB, "max": _MAX_VRAM_GB, "step": 0.1}),
                "total_vram_gb": ("FLOAT", {"default": 96.0, "min": _MIN_VRAM_GB, "max": _MAX_VRAM_GB, "step": 0.1}),
                "device_index": ("INT", {"default": 0, "min": 0, "max": 64}),
                "refresh": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("free_vram_gb", "total_vram_gb", "utilization_pct")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        free_vram_gb: float,
        total_vram_gb: float,
        device_index: int,
        refresh: bool,
    ) -> Tuple[float, float, float]:
        free = _validate_vram(free_vram_gb, "free_vram_gb")
        total = _validate_vram(total_vram_gb, "total_vram_gb")
        _validate_device_index(device_index)

        if total == 0.0:
            raise ValueError("total_vram_gb must be > 0 to compute utilization")
        if free > total:
            raise ValueError(
                f"free_vram_gb ({free}) cannot exceed total_vram_gb ({total})"
            )

        utilization_pct = ((total - free) / total) * 100.0
        return (free, total, utilization_pct)


# ---------------------------------------------------------------------------
# Node 2: PSN_Pipeline_Selector
# ---------------------------------------------------------------------------

class PSN_Pipeline_Selector:
    """Select a pipeline id based on free VRAM vs. two thresholds.

    Decision logic:
      * free_vram_gb > threshold_heavy  -> heavy pipeline
      * free_vram_gb > threshold_light  -> light pipeline
      * otherwise                       -> fallback "low-res" pipeline

    Returns (selected_pipeline_id, reason).
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "free_vram_gb": ("FLOAT", {"default": 0.0, "min": _MIN_VRAM_GB, "max": _MAX_VRAM_GB, "step": 0.1}),
                "threshold_light": ("FLOAT", {"default": 10.0, "min": _MIN_VRAM_GB, "max": _MAX_VRAM_GB, "step": 0.1}),
                "threshold_heavy": ("FLOAT", {"default": 50.0, "min": _MIN_VRAM_GB, "max": _MAX_VRAM_GB, "step": 0.1}),
                "pipeline_light_id": ("STRING", {"default": "sdxl"}),
                "pipeline_heavy_id": ("STRING", {"default": "video"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("selected_pipeline_id", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        free_vram_gb: float,
        threshold_light: float,
        threshold_heavy: float,
        pipeline_light_id: str,
        pipeline_heavy_id: str,
    ) -> Tuple[str, str]:
        free = _validate_vram(free_vram_gb, "free_vram_gb")
        t_light = _validate_threshold(threshold_light, "threshold_light")
        t_heavy = _validate_threshold(threshold_heavy, "threshold_heavy")
        light_id = _validate_pipeline_id(pipeline_light_id, "pipeline_light_id")
        heavy_id = _validate_pipeline_id(pipeline_heavy_id, "pipeline_heavy_id")

        if t_light >= t_heavy:
            raise ValueError(
                f"threshold_light ({t_light}) must be < threshold_heavy ({t_heavy})"
            )

        if free > t_heavy:
            return (
                heavy_id,
                f"free {free:.2f} GB > heavy threshold {t_heavy:.2f} GB -> heavy pipeline",
            )
        if free > t_light:
            return (
                light_id,
                f"free {free:.2f} GB > light threshold {t_light:.2f} GB -> light pipeline",
            )
        return (
            _FALLBACK_PIPELINE_ID,
            f"free {free:.2f} GB <= light threshold {t_light:.2f} GB -> fallback low-res pipeline",
        )


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS: Dict[str, type] = {
    "PSN_VRAM_Query": PSN_VRAM_Query,
    "PSN_Pipeline_Selector": PSN_Pipeline_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS: Dict[str, str] = {
    "PSN_VRAM_Query": "PSN VRAM Query",
    "PSN_Pipeline_Selector": "PSN Pipeline Selector",
}
