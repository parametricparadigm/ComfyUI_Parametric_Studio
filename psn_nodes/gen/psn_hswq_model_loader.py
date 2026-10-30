"""
PSN_HSWQ_Model_Loader: Pure-logic validation and estimation for Hybrid-Sensitivity-Weighted-Quantization (HSWQ) model loading.

This module does NOT load models, access files, or use GPU/torch/onnxruntime.
It provides secure-by-design validation of HSWQ model configuration parameters
and estimation of VRAM usage based on model size and quantization bit width.

Inputs are plain values (strings, ints, floats). No network, file I/O, or subprocess.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/ModelLoading"

# Allowed quantization bit widths
ALLOWED_BITS = [2, 4, 8, 16]

# Allowed devices
ALLOWED_DEVICES = ["cuda", "cpu"]

# Maximum allowed model size in GB for safety (prevent absurd inputs)
MAX_MODEL_SIZE_GB = 100.0


def _validate_model_path(model_path: str) -> tuple:
    """
    Validate the model path string.
    Returns (is_valid: bool, reason: str).
    """
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if len(model_path) == 0:
        return False, "model_path must not be empty"
    if len(model_path) > 1024:
        return False, "model_path exceeds maximum length of 1024 characters"
    # Basic sanity: no null bytes
    if "\x00" in model_path:
        return False, "model_path contains null bytes"
    return True, "ok"


def _validate_quantization_bit(quantization_bit: int) -> tuple:
    """
    Validate the quantization bit width.
    Returns (is_valid: bool, reason: str).
    """
    if not isinstance(quantization_bit, int):
        return False, "quantization_bit must be an integer"
    if quantization_bit not in ALLOWED_BITS:
        return False, f"quantization_bit must be one of {ALLOWED_BITS}, got {quantization_bit}"
    return True, "ok"


def _validate_device(device: str) -> tuple:
    """
    Validate the target device.
    Returns (is_valid: bool, reason: str).
    """
    if not isinstance(device, str):
        return False, "device must be a string"
    if device not in ALLOWED_DEVICES:
        return False, f"device must be one of {ALLOWED_DEVICES}, got {device!r}"
    return True, "ok"


def _estimate_vram_usage(model_size_gb: float, quantization_bit: int, device: str) -> float:
    """
    Estimate VRAM usage in GB based on model size and quantization bit width.
    
    The base model size is assumed to be in FP16 (16 bits).
    VRAM usage scales linearly with bit width relative to 16 bits.
    For CPU device, we estimate the same but note it's not VRAM.
    
    Args:
        model_size_gb: Size of the model in GB at FP16 precision.
        quantization_bit: Target quantization bit width.
        device: Target device ("cuda" or "cpu").
    
    Returns:
        Estimated memory usage in GB.
    """
    if model_size_gb <= 0:
        return 0.0
    # Scale factor: quantization_bit / 16 (since base is FP16)
    scale = quantization_bit / 16.0
    estimated = model_size_gb * scale
    # Clamp to reasonable range
    estimated = max(0.0, min(estimated, MAX_MODEL_SIZE_GB))
    return round(estimated, 4)


class PSN_HSWQ_Model_Loader:
    """
    Validates HSWQ model loading configuration and estimates VRAM usage.
    
    This node does NOT actually load models. It performs:
    - Validation of model_path, quantization_bit, and device
    - Estimation of VRAM usage based on model size and bit width
    - Reports pass/fail with reasons
    
    For actual model loading, use the corresponding GPU-enabled node.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {"default": "", "multiline": False}),
                "quantization_bit": (ALLOWED_BITS, {"default": 4}),
                "device": (ALLOWED_DEVICES, {"default": "cuda"}),
            },
            "optional": {
                "model_size_gb": ("FLOAT", {"default": 6.5, "min": 0.0, "max": MAX_MODEL_SIZE_GB, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "FLOAT", "STRING")
    RETURN_NAMES = ("valid", "vram_usage", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_path, quantization_bit, device, model_size_gb=6.5):
        """
        Validate HSWQ model configuration and estimate VRAM usage.
        
        Args:
            model_path: Path to the HSWQ quantized model file.
            quantization_bit: Bit width for quantization (2, 4, 8, or 16).
            device: Target device ("cuda" or "cpu").
            model_size_gb: Size of the model in GB at FP16 precision (for estimation).
        
        Returns:
            tuple: (valid: bool, vram_usage: float, reason: str)
        """
        # Validate model_path
        path_ok, path_reason = _validate_model_path(model_path)
        if not path_ok:
            return (False, 0.0, path_reason)

        # Validate quantization_bit
        bit_ok, bit_reason = _validate_quantization_bit(quantization_bit)
        if not bit_ok:
            return (False, 0.0, bit_reason)

        # Validate device
        dev_ok, dev_reason = _validate_device(device)
        if not dev_ok:
            return (False, 0.0, dev_reason)

        # Validate model_size_gb
        if not isinstance(model_size_gb, (int, float)):
            return (False, 0.0, "model_size_gb must be a number")
        if model_size_gb < 0:
            return (False, 0.0, "model_size_gb must be non-negative")
        if model_size_gb > MAX_MODEL_SIZE_GB:
            return (False, 0.0, f"model_size_gb exceeds maximum of {MAX_MODEL_SIZE_GB} GB")

        # Estimate VRAM usage
        vram = _estimate_vram_usage(float(model_size_gb), quantization_bit, device)

        return (True, vram, "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_HSWQ_Model_Loader": PSN_HSWQ_Model_Loader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_HSWQ_Model_Loader": "HSWQ Model Loader (Validation & VRAM Estimation)",
}
