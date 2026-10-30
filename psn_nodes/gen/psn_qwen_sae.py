"""
PSN Qwen SAE Nodes (Pure Logic)

This module implements the pure-logic components for Sparse Autoencoder (SAE) analysis
on Qwen models. It does NOT load models or run inference. Instead, it provides:
1. Secure validation of SAE configuration paths and parameters.
2. Analysis of activation values (provided as lists) to identify top features.

Use these nodes in conjunction with external tools that provide the actual tensor data
as lists of floats.
"""

import json
import re
from typing import Any, List, Tuple

# Simulate the psn module imports as per convention, but we will implement the logic
# inline to ensure no external dependencies are actually required for the core logic
# if psn is not available in the test environment. However, the prompt says we MAY use it.
# To be safe and self-contained for the "pure logic" requirement, I will implement
# the necessary helpers locally if they are simple, or assume psn exists.
# The prompt says: "You may use `from psn import expr, orchestration`".
# I will assume psn.orchestration exists for gate logic if needed, but for top-k,
# standard python is better.

# Since I cannot guarantee psn is installed in the test env for the "pure logic" part
# unless it's part of the standard library (it's not), I will implement the logic
# directly in the node methods to ensure the code is runnable with stdlib only.
# The prompt says "pure Python standard library only". So I will NOT import psn
# unless it's strictly necessary and I can mock it. But the prompt says "You may use".
# To be safe, I will implement the logic without psn imports to ensure it runs
# in a standard pytest environment without the custom psn package.

class PSN_SAE_ConfigValidator:
    """
    Validates SAE configuration parameters.
    
    Inputs:
        sae_path (STRING): The path to the SAE model file.
        layer (INT): The layer index to analyze.
        max_layer (INT): The maximum valid layer index for the model.
    
    Outputs:
        valid (BOOLEAN): Whether the configuration is valid.
        reason (STRING): Explanation of validation result.
        safe_path (STRING): The validated path (redacted if invalid).
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sae_path": ("STRING", {"default": "/models/sae/qwen_sae.safetensors"}),
                "layer": ("INT", {"default": 10, "min": 0, "max": 1000}),
                "max_layer": ("INT", {"default": 32, "min": 1, "max": 1000}),
            },
            "optional": {
                "allowed_dirs": ("STRING", {"default": "/models/sae"}),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("valid", "reason", "safe_path")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/SAE"
    
    def run(self, sae_path: str, layer: int, max_layer: int, allowed_dirs: str = "/models/sae") -> Tuple[bool, str, str]:
        # Validate layer
        if layer < 0:
            return (False, "Layer must be non-negative", "")
        if layer > max_layer:
            return (False, f"Layer {layer} exceeds max layer {max_layer}", "")
        
        # Validate path
        if not sae_path:
            return (False, "SAE path is empty", "")
        
        # Basic path security check: no traversal
        if ".." in sae_path:
            return (False, "Path traversal detected", "")
        
        # Check if path starts with allowed dirs
        allowed_dirs = allowed_dirs.rstrip("/")
        if allowed_dirs and not sae_path.startswith(allowed_dirs):
            return (False, f"Path not in allowed directories: {allowed_dirs}", "")
        
        # Check file extension
        if not sae_path.endswith(".safetensors") and not sae_path.endswith(".pt"):
            return (False, "Invalid file extension. Must be .safetensors or .pt", "")
        
        return (True, "Configuration valid", sae_path)


class PSN_SAE_TopFeatureAnalyzer:
    """
    Analyzes activation values to identify top features.
    
    Inputs:
        activations (STRING): JSON string of a list of floats representing activations.
        top_k (INT): Number of top features to return.
        threshold (FLOAT): Minimum activation value to consider.
    
    Outputs:
        top_features (STRING): JSON string of top features (indices and values).
        count (INT): Number of features above threshold.
        max_value (FLOAT): The maximum activation value.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "activations": ("STRING", {"default": "[]"}),
                "top_k": ("INT", {"default": 5, "min": 1, "max": 100}),
                "threshold": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "FLOAT")
    RETURN_NAMES = ("top_features", "count", "max_value")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/SAE"
    
    def run(self, activations: str, top_k: int, threshold: float) -> Tuple[str, int, float]:
        # Parse JSON
        try:
            data = json.loads(activations)
            if not isinstance(data, list):
                return ("[]", 0, 0.0)
            # Ensure all elements are numeric
            values = [float(x) for x in data]
        except (json.JSONDecodeError, ValueError, TypeError):
            return ("[]", 0, 0.0)
        
        if not values:
            return ("[]", 0, 0.0)
        
        # Find max
        max_val = max(values)
        
        # Filter by threshold
        above_threshold = [(i, v) for i, v in enumerate(values) if v >= threshold]
        
        # Sort by value descending
        above_threshold.sort(key=lambda x: x[1], reverse=True)
        
        # Take top_k
        top_items = above_threshold[:top_k]
        
        # Format output
        result = [{"index": i, "value": v} for i, v in top_items]
        
        return (json.dumps(result), len(above_threshold), max_val)


NODE_CLASS_MAPPINGS = {
    "PSN_SAE_ConfigValidator": PSN_SAE_ConfigValidator,
    "PSN_SAE_TopFeatureAnalyzer": PSN_SAE_TopFeatureAnalyzer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SAE_ConfigValidator": "SAE Config Validator",
    "PSN_SAE_TopFeatureAnalyzer": "SAE Top Feature Analyzer",
}
