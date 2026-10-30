"""VRAM-Aware Model Selector for ComfyUI (ParametricStudio).

Filters a list of candidate models to return only those that fit within a
VRAM budget, prioritizing smaller or quantized models when necessary.

The node is intentionally dependency-light: it uses only the Python standard
library and (optionally) torch for a real VRAM query.  File size is used as
a proxy for VRAM usage, which is a known simplification (activations and
runtime overhead are not accounted for).
"""

import math

try:
    import torch
except Exception:  # pragma: no cover - torch should be present in ComfyUI
    torch = None

CAT = "ParametricStudio/Models"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GB = 1024.0 ** 3

# Quantization level -> bytes per parameter (approximate).
# fp32 = 4, fp16/bf16 = 2, int8 = 1, int4 = 0.5, int2 = 0.25
_DTYPE_BYTES = {
    "fp32": 4.0,
    "fp16": 2.0,
    "bf16": 2.0,
    "int8": 1.0,
    "int4": 0.5,
    "int2": 0.25,
}

# Lower is "more quantized" (better for low-VRAM scenarios).
_QUANT_RANK = {
    "int2": 0,
    "int4": 1,
    "int8": 2,
    "bf16": 3,
    "fp16": 3,
    "fp32": 4,
}


def _normalize_dtype(raw):
    """Map a raw dtype string to a canonical key in _DTYPE_BYTES."""
    if raw is None:
        return "fp16"
    key = str(raw).strip().lower()
    # Common aliases
    aliases = {
        "float32": "fp32",
        "float16": "fp16",
        "half": "fp16",
        "bfloat16": "bf16",
        "int8": "int8",
        "int4": "int4",
        "int2": "int2",
        "q8": "int8",
        "q4": "int4",
        "q2": "int2",
    }
    key = aliases.get(key, key)
    if key in _DTYPE_BYTES:
        return key
    # Fallback: try to parse a number of bytes
    try:
        b = float(key)
        if b <= 0:
            return "fp16"
        # Pick the closest known dtype
        best = min(_DTYPE_BYTES, key=lambda k: abs(_DTYPE_BYTES[k] - b))
        return best
    except (ValueError, TypeError):
        return "fp16"


def _estimate_vram_gb(entry):
    """Estimate VRAM (in GB) for a single model entry.

    An entry is a dict with at least:
        - "name" (str)
        - "path" (str)
        - "file_size_bytes" (int/float)  OR  "file_size_gb" (float)
        - "dtype" (str, optional, default "fp16")

    If file_size_bytes is present we use it directly (it already reflects the
    on-disk size, which is a good proxy for VRAM).  Otherwise we fall back to
    a param-count based estimate if "param_count" is given.
    """
    if not isinstance(entry, dict):
        raise TypeError("model entry must be a dict")

    dtype = _normalize_dtype(entry.get("dtype"))

    # Prefer explicit file size in bytes
    size_bytes = entry.get("file_size_bytes")
    if size_bytes is not None:
        try:
            size_bytes = float(size_bytes)
        except (ValueError, TypeError):
            size_bytes = None
    if size_bytes is not None and size_bytes > 0:
        return max(0.0, size_bytes / _GB)

    size_gb = entry.get("file_size_gb")
    if size_gb is not None:
        try:
            size_gb = float(size_gb)
        except (ValueError, TypeError):
            size_gb = None
    if size_gb is not None and size_gb > 0:
        return max(0.0, size_gb)

    # Fallback: param_count * bytes_per_param
    param_count = entry.get("param_count")
    if param_count is not None:
        try:
            param_count = float(param_count)
        except (ValueError, TypeError):
            param_count = None
    if param_count is not None and param_count > 0:
        return max(0.0, param_count * _DTYPE_BYTES[dtype] / _GB)

    raise ValueError(
        "model entry must provide file_size_bytes, file_size_gb, or param_count"
    )


def _quant_rank(entry):
    """Return a sort key for quantization preference (lower = more quantized)."""
    dtype = _normalize_dtype(entry.get("dtype"))
    return _QUANT_RANK.get(dtype, 4)


def _query_vram_gb():
    """Return total GPU VRAM in GB, or None if unavailable."""
    if torch is None:
        return None
    try:
        if not torch.cuda.is_available():
            return None
        props = torch.cuda.get_device_properties(0)
        return props.total_memory / _GB
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_VRAMModelSelector:
    """Select the best-fitting model from a list given a VRAM budget.

    Inputs:
        model_list: list of dicts, each with name/path/file_size_bytes (or
            file_size_gb or param_count) and optional dtype.
        max_vram_gb: maximum VRAM (GB) the selected model may use.
        prefer_quantized: if True, prefer more-quantized models when several
            fit the budget.

    Outputs:
        SELECTED_MODEL_PATH: str path of the chosen model ("" if none fit).
        SELECTED_MODEL_NAME: str name of the chosen model ("" if none fit).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_list": ("MODEL_LIST",),
                "max_vram_gb": ("FLOAT", {"default": 8.0, "min": 0.1, "max": 512.0, "step": 0.1}),
                "prefer_quantized": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("SELECTED_MODEL_PATH", "SELECTED_MODEL_NAME")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_list, max_vram_gb, prefer_quantized):
        # --- validate inputs ------------------------------------------------
        if model_list is None:
            model_list = []
        if not isinstance(model_list, (list, tuple)):
            raise TypeError("model_list must be a list of model entries")

        try:
            budget = float(max_vram_gb)
        except (ValueError, TypeError):
            raise ValueError("max_vram_gb must be a positive number")
        if budget <= 0:
            raise ValueError("max_vram_gb must be positive")

        # --- estimate + filter ---------------------------------------------
        candidates = []
        for i, entry in enumerate(model_list):
            if not isinstance(entry, dict):
                raise TypeError(f"model_list[{i}] must be a dict")
            vram = _estimate_vram_gb(entry)
            if vram <= budget:
                candidates.append((vram, _quant_rank(entry), entry))

        if not candidates:
            return ("", "")

        # --- sort -----------------------------------------------------------
        if prefer_quantized:
            # Primary: more quantized first; secondary: larger first (best quality).
            candidates.sort(key=lambda t: (t[1], -t[0]))
        else:
            # Largest first (best quality that still fits the budget).
            candidates.sort(key=lambda t: -t[0])

        best = candidates[0][2]
        path = str(best.get("path", ""))
        name = str(best.get("name", ""))
        return (path, name)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_VRAMModelSelector": PSN_VRAMModelSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAMModelSelector": "VRAM-Aware Model Selector",
}
