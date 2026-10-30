"""
PSN_SmartModelLoader: Unified Model Loader for PS Backend (Pure Logic).

This module implements the decision logic for selecting model loading strategies
based on file extension and available VRAM. It does NOT load actual models,
access the file system, or use torch/GPU. Instead, it validates inputs,
determines the appropriate backend and quantization strategy, and returns
a structured plan (as a dict) that a real ComfyUI node would use to perform
the actual loading.

The node class PSN_SmartModelLoader follows ComfyUI conventions but returns
a STRING (JSON plan) instead of actual MODEL/CLIP/VAE objects, since this
is a pure-logic implementation.
"""

import json
import re

# Allowed quantization types
_QUANT_TYPES = ["auto", "q8_0", "q4_0", "fp8"]

# File extensions we recognize
_SAFETENSORS_EXT = ".safetensors"
_GGUF_EXT = ".gguf"

# Minimum VRAM (in MB) below which we consider VRAM "low"
# This is a default; the user can override via min_vram_mb input
_DEFAULT_MIN_VRAM_MB = 4096


def _validate_model_path(model_path):
    """
    Validate the model path string.
    Returns (is_valid, error_message).
    """
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if not model_path.strip():
        return False, "model_path must not be empty"
    # Basic sanity: must contain a dot for extension
    if "." not in model_path:
        return False, "model_path must have a file extension"
    return True, ""


def _get_extension(model_path):
    """Extract lowercase file extension from path."""
    idx = model_path.rfind(".")
    if idx == -1:
        return ""
    return model_path[idx:].lower()


def _determine_backend(model_path):
    """
    Determine the backend based on file extension.
    Returns (backend, error_message).
    backend is one of: "safetensors", "gguf", "unknown"
    """
    ext = _get_extension(model_path)
    if ext == _SAFETENSORS_EXT:
        return "safetensors", ""
    elif ext == _GGUF_EXT:
        return "gguf", ""
    else:
        return "unknown", f"Unsupported file extension: '{ext}'. Expected '.safetensors' or '.gguf'."


def _select_quantization(backend, quantization_type, vram_mb, min_vram_mb):
    """
    Select the quantization strategy.
    
    Args:
        backend: "safetensors" or "gguf"
        quantization_type: user-specified quantization ("auto", "q8_0", "q4_0", "fp8")
        vram_mb: current available VRAM in MB
        min_vram_mb: minimum VRAM threshold for full precision
    
    Returns:
        (quantization, reason) tuple
    """
    if quantization_type != "auto":
        # User forced a specific quantization
        if quantization_type not in _QUANT_TYPES:
            return "error", f"Invalid quantization_type: '{quantization_type}'"
        return quantization_type, f"User-forced quantization: {quantization_type}"

    # Auto mode: decide based on VRAM and backend
    if backend == "gguf":
        # GGUF files are already quantized; we just note the backend
        return "gguf_native", "GGUF backend uses native quantization"

    # Safetensors: check VRAM
    if vram_mb < min_vram_mb:
        # Low VRAM: prefer fp8 if available, else q8_0
        return "fp8", f"VRAM {vram_mb}MB < threshold {min_vram_mb}MB, using FP8"
    else:
        # High VRAM: use fp16 (standard)
        return "fp16", f"VRAM {vram_mb}MB >= threshold {min_vram_mb}MB, using FP16"


def _build_plan(model_path, backend, quantization, vram_mb, min_vram_mb, quantization_type):
    """
    Build the loading plan as a dictionary.
    """
    plan = {
        "model_path": model_path,
        "backend": backend,
        "quantization": quantization,
        "vram_mb": vram_mb,
        "min_vram_mb": min_vram_mb,
        "requested_quantization": quantization_type,
        "outputs": {
            "MODEL": {"type": "MODEL", "dtype": _dtype_for_quant(quantization)},
            "CLIP": {"type": "CLIP", "dtype": _dtype_for_quant(quantization)},
            "VAE": {"type": "VAE", "dtype": _dtype_for_quant(quantization)},
        },
    }
    return plan


def _dtype_for_quant(quantization):
    """Map quantization to a dtype string."""
    mapping = {
        "fp16": "float16",
        "fp8": "float8",
        "q8_0": "q8_0",
        "q4_0": "q4_0",
        "gguf_native": "gguf",
    }
    return mapping.get(quantization, "unknown")


class PSN_SmartModelLoader:
    """
    Unified Model Loader for PS Backend.
    
    Selects between .safetensors and .gguf checkpoints based on available VRAM
    to simplify backend graph generation and optimize memory usage.
    
    This is a pure-logic implementation: it validates inputs and produces a
    loading plan (JSON string) rather than actually loading models.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {"default": "model.safetensors"}),
                "min_vram_mb": ("INT", {"default": 4096, "min": 0, "max": 1000000, "step": 1}),
                "quantization_type": (_QUANT_TYPES,),
            },
            "optional": {
                "vram_mb": ("INT", {"default": 8192, "min": 0, "max": 1000000, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("loading_plan",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/ModelLoading"

    def run(self, model_path, min_vram_mb, quantization_type, vram_mb=None):
        """
        Execute the smart model loading decision logic.
        
        Args:
            model_path: Path to the model file
            min_vram_mb: Minimum VRAM threshold for full precision
            quantization_type: Forced quantization or "auto"
            vram_mb: Current available VRAM in MB (optional, defaults to 8192)
        
        Returns:
            Tuple with a single STRING element containing the JSON loading plan.
        """
        # Validate model_path
        valid, err = _validate_model_path(model_path)
        if not valid:
            plan = {"error": err, "status": "failed"}
            return (json.dumps(plan),)

        # Validate min_vram_mb
        if not isinstance(min_vram_mb, int) or min_vram_mb < 0:
            plan = {"error": "min_vram_mb must be a non-negative integer", "status": "failed"}
            return (json.dumps(plan),)

        # Validate quantization_type
        if quantization_type not in _QUANT_TYPES:
            plan = {"error": f"Invalid quantization_type: '{quantization_type}'", "status": "failed"}
            return (json.dumps(plan),)

        # Validate vram_mb
        if vram_mb is None:
            vram_mb = 8192
        if not isinstance(vram_mb, int) or vram_mb < 0:
            plan = {"error": "vram_mb must be a non-negative integer", "status": "failed"}
            return (json.dumps(plan),)

        # Determine backend
        backend, err = _determine_backend(model_path)
        if backend == "unknown":
            plan = {"error": err, "status": "failed"}
            return (json.dumps(plan),)

        # Select quantization
        quantization, reason = _select_quantization(backend, quantization_type, vram_mb, min_vram_mb)
        if quantization == "error":
            plan = {"error": reason, "status": "failed"}
            return (json.dumps(plan),)

        # Build plan
        plan = _build_plan(model_path, backend, quantization, vram_mb, min_vram_mb, quantization_type)
        plan["status"] = "ok"
        plan["reason"] = reason

        return (json.dumps(plan),)


NODE_CLASS_MAPPINGS = {
    "PSN_SmartModelLoader": PSN_SmartModelLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SmartModelLoader": "PSN Smart Model Loader",
}
