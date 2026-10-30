"""
PSN Semantic Conditioning Subtraction and Clamping Nodes.

This module implements the pure-logic, secure-by-design portion of the
"Semantic Conditioning Subtraction for Negative Prompts" specification.

Because the full specification requires GPU/torch/ComfyUI internals (specifically
the `CONDITIONING` tensor type and `torch` operations), this implementation
operates on plain Python lists of floats (representing the conditioning vectors)
and standard Python types. It performs the mathematical operations (subtraction,
scaling, clamping) without relying on external libraries like `torch`.

Nodes:
1. PSN_Conditioning_Subtract: Subtracts one vector from another with optional auto-scaling.
2. PSN_Conditioning_Clamp: Clamps vector values to a specified range using linear or tanh methods.
"""

import math
import json

# Define the category for these nodes
CAT = "ParametricStudio/Semantic"

# Helper function to calculate the mean magnitude (L2 norm) of a vector
def _mean_magnitude(vec):
    if not vec:
        return 0.0
    return math.sqrt(sum(x * x for x in vec))

# Helper function to perform element-wise subtraction
def _subtract_vectors(base, sub, strength):
    if len(base) != len(sub):
        raise ValueError("Vectors must have the same length for subtraction")
    return [b - (s * strength) for b, s in zip(base, sub)]

# Helper function to clamp values
def _clamp_vector(vec, min_val, max_val, method):
    if min_val > max_val:
        raise ValueError("min_val must be less than or equal to max_val")
    
    clamped = []
    for v in vec:
        if method == "linear":
            # Hard clamp
            if v < min_val:
                clamped.append(min_val)
            elif v > max_val:
                clamped.append(max_val)
            else:
                clamped.append(v)
        elif method == "tanh":
            # Smooth clamp using tanh
            # Map the range [min_val, max_val] to a smooth transition
            # We use a scaled tanh to approximate clamping
            # Center the range
            center = (min_val + max_val) / 2.0
            half_range = (max_val - min_val) / 2.0
            
            if half_range == 0:
                clamped.append(center)
            else:
                # Normalize to [-1, 1]
                normalized = (v - center) / half_range
                # Apply tanh to smooth the edges
                smoothed = math.tanh(normalized)
                # Map back to [min_val, max_val]
                clamped.append(center + smoothed * half_range)
        else:
            raise ValueError(f"Unknown clamp method: {method}")
    return clamped

def _parse_vector_json(json_str):
    """
    Safely parses a JSON string representing a list of numbers.
    Returns a list of floats.
    """
    if not json_str or not json_str.strip():
        return []
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    if not isinstance(data, list):
        raise ValueError("Parsed JSON must be a list")
    
    # Ensure all elements are numbers
    parsed_vec = []
    for item in data:
        if isinstance(item, (int, float)):
            parsed_vec.append(float(item))
        else:
            raise ValueError("All elements in the vector must be numbers")
            
    return parsed_vec


class PSN_Conditioning_Subtract:
    """
    Subtracts one conditioning vector from another.
    
    Computes: base_conditioning - (subtract_conditioning * strength)
    If auto_scale is true, scales the subtraction vector to match the base vector's norm.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_conditioning": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "subtract_conditioning": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "auto_scale": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "base_vector": ("STRING", {"default": "[]", "multiline": True}),
                "subtract_vector": ("STRING", {"default": "[]", "multiline": True}),
            }
        }
    
    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("result_vector", "result_json")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, base_conditioning, subtract_conditioning, strength, auto_scale, base_vector="[]", subtract_vector="[]"):
        # Parse the vectors from JSON strings
        base_vec = _parse_vector_json(base_vector)
        sub_vec = _parse_vector_json(subtract_vector)
        
        # Ensure vectors are lists of floats (already done by parser)
        
        if len(base_vec) != len(sub_vec):
            raise ValueError("Vectors must have the same length")
        
        # Calculate auto_scale if needed
        effective_strength = strength
        if auto_scale:
            base_norm = _mean_magnitude(base_vec)
            sub_norm = _mean_magnitude(sub_vec)
            if sub_norm > 0:
                effective_strength = strength * (base_norm / sub_norm)
        
        # Perform subtraction
        result_vec = _subtract_vectors(base_vec, sub_vec, effective_strength)
        
        # Return as JSON string and a representative float (e.g., first element or 0.0)
        result_json = json.dumps(result_vec)
        result_float = result_vec[0] if result_vec else 0.0
        
        return (result_float, result_json)


class PSN_Conditioning_Clamp:
    """
    Clamps the values of a conditioning vector to a specified range.
    
    Uses linear or tanh methods for clamping.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_val": ("FLOAT", {"default": -1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "max_val": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "method": (["linear", "tanh"],),
                "vector": ("STRING", {"default": "[]", "multiline": True}),
            }
        }
    
    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("result_vector", "result_json")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, min_val, max_val, method, vector="[]"):
        # Parse the vector from JSON string
        vec = _parse_vector_json(vector)
        
        # Clamp the vector
        result_vec = _clamp_vector(vec, min_val, max_val, method)
        
        # Return as JSON string and a representative float
        result_json = json.dumps(result_vec)
        result_float = result_vec[0] if result_vec else 0.0
        
        return (result_float, result_json)


# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_Conditioning_Subtract": PSN_Conditioning_Subtract,
    "PSN_Conditioning_Clamp": PSN_Conditioning_Clamp,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Conditioning_Subtract": "PSN Conditioning Subtract",
    "PSN_Conditioning_Clamp": "PSN Conditioning Clamp",
}
