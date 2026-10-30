"""
PSN_Unified_Model_VAE_Loader: Pure-logic validation and payload formatting for a unified model/VAE loader.

This node does NOT load models or access the filesystem. Instead, it validates
model_path, vae_path, and dtype against an allow-list and normalized rules,
then outputs a structured JSON payload that a downstream (GPU) node can use
to perform the actual loading. This reduces graph clutter by consolidating
validation into a single node while keeping the actual I/O in a separate,
GPU-aware stage.

Inputs:
  - model_path (STRING): Path to the diffusion model file.
  - vae_path (STRING): Path to the VAE file.
  - dtype (COMBO): Data type for loading ("fp16", "fp32", "bf16").
  - allowed_dirs (STRING, optional): Comma-separated list of allowed directory prefixes.
  - allowed_extensions (STRING, optional): Comma-separated list of allowed file extensions.

Outputs:
  - payload (STRING): JSON string containing validated paths, dtype, and metadata.
  - valid (BOOLEAN): Whether the inputs passed validation.
  - reason (STRING): Human-readable reason for validation failure, or "ok".
"""

import json
import re
from psn import expr, orchestration as _orch

CAT = "ParametricStudio/UnifiedLoader"

# Allowed data types
_DTYPE_CHOICES = ["fp16", "fp32", "bf16"]

# Default allowed extensions if none specified
_DEFAULT_ALLOWED_EXTENSIONS = [".safetensors", ".ckpt", ".pt", ".bin"]

# Default allowed directory prefixes (empty means no restriction by default,
# but in production this should be set to a safe base directory)
_DEFAULT_ALLOWED_DIRS = []


def _normalize_dtype(dtype_str):
    """Normalize dtype string to a canonical form."""
    if not isinstance(dtype_str, str):
        return None
    dtype_lower = dtype_str.strip().lower()
    if dtype_lower in _DTYPE_CHOICES:
        return dtype_lower
    # Handle common aliases
    aliases = {
        "float16": "fp16",
        "half": "fp16",
        "float32": "fp32",
        "float": "fp32",
        "bfloat16": "bf16",
    }
    return aliases.get(dtype_lower, None)


def _validate_path(path, allowed_dirs, allowed_extensions):
    """
    Validate a file path against allowed directories and extensions.
    Returns (is_valid, reason).
    """
    if not isinstance(path, str) or not path.strip():
        return False, "Path must be a non-empty string"

    path = path.strip()

    # Check for path traversal attempts
    if ".." in path:
        return False, "Path traversal detected"

    # Check allowed directories
    if allowed_dirs:
        path_lower = path.lower()
        matched = False
        for dir_prefix in allowed_dirs:
            dir_prefix = dir_prefix.strip().lower()
            if dir_prefix and path_lower.startswith(dir_prefix):
                matched = True
                break
        if not matched:
            return False, f"Path not in allowed directories: {allowed_dirs}"

    # Check allowed extensions
    if allowed_extensions:
        ext = None
        # Find the last dot
        last_dot = path.rfind(".")
        if last_dot != -1:
            ext = path[last_dot:].lower()
        if ext is None or ext not in allowed_extensions:
            return False, f"Extension not allowed. Allowed: {allowed_extensions}"

    return True, "ok"


def _build_payload(model_path, vae_path, dtype, allowed_dirs, allowed_extensions):
    """Build the JSON payload for downstream loading."""
    return {
        "model_path": model_path,
        "vae_path": vae_path,
        "dtype": dtype,
        "allowed_dirs": allowed_dirs,
        "allowed_extensions": allowed_extensions,
        "node_type": "PSN_Unified_Model_VAE_Loader",
        "version": "1.0",
    }


class PSN_Unified_Model_VAE_Loader:
    """
    Unified loader for model and VAE with pure-logic validation.
    Outputs a JSON payload for downstream GPU loading.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {"default": "", "multiline": False}),
                "vae_path": ("STRING", {"default": "", "multiline": False}),
                "dtype": (_DTYPE_CHOICES,),
            },
            "optional": {
                "allowed_dirs": ("STRING", {"default": "", "multiline": False}),
                "allowed_extensions": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("payload", "valid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_path, vae_path, dtype, allowed_dirs="", allowed_extensions=""):
        # Parse allowed directories
        allowed_dirs_list = []
        if allowed_dirs and allowed_dirs.strip():
            allowed_dirs_list = [d.strip() for d in allowed_dirs.split(",") if d.strip()]

        # Parse allowed extensions
        allowed_ext_list = []
        if allowed_extensions and allowed_extensions.strip():
            allowed_ext_list = [e.strip().lower() for e in allowed_extensions.split(",") if e.strip()]
        else:
            allowed_ext_list = _DEFAULT_ALLOWED_EXTENSIONS

        # Normalize dtype
        normalized_dtype = _normalize_dtype(dtype)
        if normalized_dtype is None:
            return (json.dumps({"error": "Invalid dtype"}), False, f"Invalid dtype: {dtype}")

        # Validate model path
        model_valid, model_reason = _validate_path(model_path, allowed_dirs_list, allowed_ext_list)
        if not model_valid:
            return (json.dumps({"error": model_reason}), False, f"Model path invalid: {model_reason}")

        # Validate VAE path
        vae_valid, vae_reason = _validate_path(vae_path, allowed_dirs_list, allowed_ext_list)
        if not vae_valid:
            return (json.dumps({"error": vae_reason}), False, f"VAE path invalid: {vae_reason}")

        # Build payload
        payload = _build_payload(
            model_path.strip(),
            vae_path.strip(),
            normalized_dtype,
            allowed_dirs_list,
            allowed_ext_list,
        )

        return (json.dumps(payload), True, "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_Unified_Model_VAE_Loader": PSN_Unified_Model_VAE_Loader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Unified_Model_VAE_Loader": "Unified Model VAE Loader (Validation)",
}
