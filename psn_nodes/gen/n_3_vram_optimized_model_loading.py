"""
VRAM-Optimized Model Loading (pure-logic, secure-by-design).

This module implements the *planning and reporting* logic for VRAM-optimized
model loading. It does NOT load models, touch GPU memory, or import torch/comfy.
Instead, it operates on a plain JSON text description of a model's state dict
and produces a pruned/quantized plan plus a human-readable memory report.

The node takes plain values (strings, numbers, booleans) and returns plain
values (strings, booleans). No file I/O, no network, no subprocess, no eval.
"""

import json
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Keys that are considered non-essential and can be pruned.
# In a real diffusion model these might be VAE decoder buffers, EMA weights,
# or optimizer state that is not needed at inference time.
_PRUNABLE_KEY_PATTERNS = [
    r"^vae\.decoder\.",
    r"^vae\.encoder\.",
    r"^ema\.",
    r"^optimizer\.",
    r"^_buffers\.",
    r"^\.metadata$",
]

# Quantization modes and their simulated bytes-per-parameter.
# "none"  -> 4 bytes (fp32)
# "w8a8"  -> 1 byte  (int8 weight + int8 activation)
# "int8"  -> 1 byte  (int8 weight, fp32 activation)
_QUANT_BYTES_PER_PARAM = {
    "none": 4,
    "w8a8": 1,
    "int8": 1,
}

_QUANT_MODES = ["none", "w8a8", "int8"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_state_dict_json(state_dict_json: str) -> dict:
    """
    Parse a JSON string representing a state dict.
    Expected format: {"key1": {"num_params": 12345}, "key2": {"num_params": 67890}, ...}
    Returns a dict of key -> num_params (int).
    Raises ValueError on malformed input.
    """
    if not isinstance(state_dict_json, str):
        raise ValueError("state_dict_json must be a string")
    try:
        data = json.loads(state_dict_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in state_dict_json: {e}")
    if not isinstance(data, dict):
        raise ValueError("state_dict_json must decode to a JSON object")
    result = {}
    for key, val in data.items():
        if not isinstance(key, str):
            raise ValueError(f"State dict key must be a string, got {type(key)}")
        if isinstance(val, dict):
            np_ = val.get("num_params", 0)
        elif isinstance(val, (int, float)):
            np_ = val
        else:
            raise ValueError(f"Invalid value for key '{key}': expected int, float, or object with 'num_params'")
        if not isinstance(np_, (int, float)) or np_ < 0:
            raise ValueError(f"num_params for key '{key}' must be a non-negative number")
        result[key] = int(np_)
    return result


def _is_prunable(key: str) -> bool:
    """Check if a key matches any prunable pattern."""
    for pattern in _PRUNABLE_KEY_PATTERNS:
        if re.match(pattern, key):
            return True
    return False


def _compute_memory_gb(num_params: int, bytes_per_param: float) -> float:
    """Compute memory in GB for given number of params and bytes per param."""
    return (num_params * bytes_per_param) / (1024 ** 3)


def _build_report(
    original_params: int,
    pruned_params: int,
    quantized_params: int,
    quant_mode: str,
    target_vram_gb: float,
    final_memory_gb: float,
    pruned_keys: list,
) -> str:
    """Build a human-readable memory report string."""
    lines = []
    lines.append("=== VRAM Optimization Report ===")
    lines.append(f"Original parameters:   {original_params:,}")
    lines.append(f"Pruned parameters:     {pruned_params:,}")
    lines.append(f"Quantized parameters:  {quantized_params:,}")
    lines.append(f"Quantization mode:     {quant_mode}")
    lines.append(f"Final memory estimate: {final_memory_gb:.4f} GB")
    lines.append(f"Target VRAM:           {target_vram_gb:.4f} GB")
    if final_memory_gb <= target_vram_gb:
        lines.append("Status: FITS within target VRAM")
    else:
        lines.append("Status: EXCEEDS target VRAM")
    if pruned_keys:
        lines.append(f"Pruned keys ({len(pruned_keys)}):")
        for k in pruned_keys[:20]:
            lines.append(f"  - {k}")
        if len(pruned_keys) > 20:
            lines.append(f"  ... and {len(pruned_keys) - 20} more")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_Model_Vram_Optimizer:
    """
    Inspect and prune unnecessary keys from a model state dict and simulate
    quantization to fit within GPU memory constraints.

    Pure-logic: operates on a JSON text description of the state dict.
    No torch, no GPU, no file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state_dict_json": ("STRING", {
                    "default": "{}",
                    "multiline": True,
                    "tooltip": "JSON object mapping state-dict keys to param counts",
                }),
                "prune_keys": ("BOOLEAN", {"default": True}),
                "quantize_mode": (_QUANT_MODES,),
                "target_vram_gb": ("FLOAT", {
                    "default": 8.0,
                    "min": 0.1,
                    "max": 256.0,
                    "step": 0.1,
                }),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("fits_vram", "optimized_state_dict_json", "memory_report")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/VRAM"

    def run(self, state_dict_json, prune_keys, quantize_mode, target_vram_gb):
        # Validate quantize_mode
        if quantize_mode not in _QUANT_MODES:
            raise ValueError(f"quantize_mode must be one of {_QUANT_MODES}, got '{quantize_mode}'")

        # Parse state dict
        state_dict = _parse_state_dict_json(state_dict_json)

        original_params = sum(state_dict.values())

        # Step 1: Prune keys
        pruned_keys = []
        pruned_params = 0
        remaining = {}
        if prune_keys:
            for key, np_ in state_dict.items():
                if _is_prunable(key):
                    pruned_keys.append(key)
                    pruned_params += np_
                else:
                    remaining[key] = np_
        else:
            remaining = dict(state_dict)

        # Step 2: Quantize
        bytes_per_param = _QUANT_BYTES_PER_PARAM[quantize_mode]
        quantized_params = sum(remaining.values())

        # Step 3: Compute final memory
        final_memory_gb = _compute_memory_gb(quantized_params, bytes_per_param)
        fits = final_memory_gb <= target_vram_gb

        # Build optimized state dict JSON (only remaining keys, with quantization info)
        optimized = {}
        for key, np_ in remaining.items():
            optimized[key] = {
                "num_params": np_,
                "bytes_per_param": bytes_per_param,
                "quantized": quantize_mode != "none",
            }
        optimized_json = json.dumps(optimized, indent=2)

        # Build report
        report = _build_report(
            original_params=original_params,
            pruned_params=pruned_params,
            quantized_params=quantized_params,
            quant_mode=quantize_mode,
            target_vram_gb=target_vram_gb,
            final_memory_gb=final_memory_gb,
            pruned_keys=pruned_keys,
        )

        return (fits, optimized_json, report)


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Model_Vram_Optimizer": PSN_Model_Vram_Optimizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Model_Vram_Optimizer": "Model VRAM Optimizer",
}
