"""PSN_Latent_Diff: Compares two latent tensors to quantify divergence (e.g., for A/B testing models).

This module implements the pure-logic, secure-by-design part of the latent diff node.
Since the spec requires `torch` (GPU/torch/ComfyUI internals), we implement ONLY the
pure-logic part: message/payload formatting, config validation, allow-list checks,
rate limiting, token redaction, parsing; never open a socket as functions and node
wrappers that take plain values (numbers, strings, JSON text) and say so in a module
docstring.

The node accepts latent data as JSON text (a list of numbers representing the flattened
latent tensor) and computes MSE and Max Absolute Difference.
"""

import json
import math

CAT = "ParametricStudio/Latent"


def _parse_latent_json(latent_json: str):
    """Parse a JSON string representing a latent tensor (list of numbers).
    
    Returns a list of floats, or raises ValueError if invalid.
    """
    if not isinstance(latent_json, str):
        raise ValueError("latent must be a JSON string")
    try:
        data = json.loads(latent_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    if not isinstance(data, list):
        raise ValueError("Latent JSON must be a list of numbers")
    
    result = []
    for i, item in enumerate(data):
        if isinstance(item, bool):
            raise ValueError(f"Item at index {i} is a boolean, expected a number")
        if not isinstance(item, (int, float)):
            raise ValueError(f"Item at index {i} is not a number: {type(item).__name__}")
        if isinstance(item, float) and (math.isnan(item) or math.isinf(item)):
            raise ValueError(f"Item at index {i} is NaN or Inf")
        result.append(float(item))
    
    return result


def _compute_mse(a: list, b: list) -> float:
    """Compute Mean Squared Error between two lists of numbers."""
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {len(a)} vs {len(b)}")
    if len(a) == 0:
        return 0.0
    total = 0.0
    for x, y in zip(a, b):
        diff = x - y
        total += diff * diff
    return total / len(a)


def _compute_max_diff(a: list, b: list) -> float:
    """Compute Max Absolute Difference between two lists of numbers."""
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {len(a)} vs {len(b)}")
    if len(a) == 0:
        return 0.0
    max_d = 0.0
    for x, y in zip(a, b):
        d = abs(x - y)
        if d > max_d:
            max_d = d
    return max_d


class PSN_LatentDiff:
    """Compares two latent tensors to quantify divergence (e.g., for A/B testing models).
    
    Inputs are latent data as JSON strings (list of numbers representing flattened latent).
    Outputs: mse (FLOAT), max_diff (FLOAT), report (STRING).
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_a": ("STRING", {"default": "[]", "multiline": True}),
                "latent_b": ("STRING", {"default": "[]", "multiline": True}),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("FLOAT", "FLOAT", "STRING")
    RETURN_NAMES = ("mse", "max_diff", "report")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, latent_a: str, latent_b: str):
        """Compute MSE and Max Absolute Difference between two latents given as JSON strings."""
        try:
            a = _parse_latent_json(latent_a)
            b = _parse_latent_json(latent_b)
        except ValueError as e:
            return (0.0, 0.0, f"Error: {e}")
        
        if len(a) != len(b):
            return (0.0, 0.0, f"Error: Length mismatch: latent_a has {len(a)} elements, latent_b has {len(b)} elements")
        
        if len(a) == 0:
            return (0.0, 0.0, "OK: Both latents are empty, MSE=0.0, MaxDiff=0.0")
        
        mse = _compute_mse(a, b)
        max_diff = _compute_max_diff(a, b)
        
        report = f"OK: MSE={mse:.6f}, MaxDiff={max_diff:.6f}, Elements={len(a)}"
        return (mse, max_diff, report)


NODE_CLASS_MAPPINGS = {
    "PSN_LatentDiff": PSN_LatentDiff,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LatentDiff": "PSN Latent Diff",
}
