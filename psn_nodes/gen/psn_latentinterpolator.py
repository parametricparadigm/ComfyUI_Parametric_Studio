"""
PSN_LatentInterpolator: Pure-logic latent interpolation.

This module implements the mathematical core of latent interpolation (lerp and slerp)
using only the Python standard library. It operates on lists of floats representing
latent vectors, avoiding any dependency on torch or GPU tensors.

Inputs:
- latent_a: List of floats (vector A)
- latent_b: List of floats (vector B)
- t: Float in [0, 1] (interpolation factor)
- method: String ("lerp" or "slerp")

Outputs:
- latent_out: List of floats (interpolated vector)
- valid: Boolean (whether the operation was valid)
- reason: String (explanation if invalid)
"""

import math

CAT = "ParametricStudio/Latent"

class PSN_LatentInterpolator:
    """
    Interpolates between two latent vectors using linear (lerp) or spherical (slerp) methods.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_a": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "latent_b": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "t": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "method": (["lerp", "slerp"],),
            },
            "optional": {
                "latent_a_list": ("STRING", {"default": "[]", "multiline": True}),
                "latent_b_list": ("STRING", {"default": "[]", "multiline": True}),
            }
        }

    RETURN_TYPES = ("FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("latent_out_first", "valid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def _parse_vector(self, vec_str, fallback_val):
        """
        Parses a JSON-like string of floats into a list.
        If parsing fails or list is empty, returns a single-element list with fallback_val.
        """
        try:
            # Simple JSON parse for list of numbers
            if not vec_str or vec_str.strip() == "[]":
                return [fallback_val]
            
            # Remove whitespace and parse
            cleaned = vec_str.strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                cleaned = cleaned[1:-1]
            
            parts = [p.strip() for p in cleaned.split(",") if p.strip()]
            if not parts:
                return [fallback_val]
                
            vec = []
            for p in parts:
                try:
                    vec.append(float(p))
                except ValueError:
                    return [fallback_val]
            return vec
        except Exception:
            return [fallback_val]

    def _lerp(self, a, b, t):
        """Linear interpolation between two vectors."""
        return [a[i] + (b[i] - a[i]) * t for i in range(len(a))]

    def _slerp(self, a, b, t):
        """
        Spherical linear interpolation between two vectors.
        Requires normalized vectors. If vectors are not normalized, they are normalized first.
        If vectors are nearly parallel or anti-parallel, falls back to lerp.
        """
        # Normalize vectors
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a < 1e-10 or norm_b < 1e-10:
            # Zero vector, cannot slerp
            return self._lerp(a, b, t)
        
        a_norm = [x / norm_a for x in a]
        b_norm = [x / norm_b for x in b]
        
        # Calculate dot product
        dot = sum(a_norm[i] * b_norm[i] for i in range(len(a_norm)))
        
        # Clamp dot product to [-1, 1] to avoid math domain errors
        dot = max(-1.0, min(1.0, dot))
        
        # If vectors are nearly parallel or anti-parallel, use lerp
        if abs(dot) > 0.9999:
            return self._lerp(a, b, t)
        
        theta_0 = math.acos(dot)
        theta = theta_0 * t
        
        sin_theta_0 = math.sin(theta_0)
        if sin_theta_0 < 1e-10:
            return self._lerp(a, b, t)
        
        s_a = math.sin((1.0 - t) * theta_0) / sin_theta_0
        s_b = math.sin(t * theta_0) / sin_theta_0
        
        result = [a_norm[i] * s_a + b_norm[i] * s_b for i in range(len(a_norm))]
        
        # Re-normalize to ensure unit length (numerical stability)
        norm_result = math.sqrt(sum(x * x for x in result))
        if norm_result > 1e-10:
            result = [x / norm_result for x in result]
            
        return result

    def run(self, latent_a, latent_b, t, method, latent_a_list=None, latent_b_list=None):
        # Parse vectors from string inputs if provided, otherwise use scalar inputs as single-element vectors
        if latent_a_list is not None and latent_a_list.strip():
            vec_a = self._parse_vector(latent_a_list, latent_a)
        else:
            vec_a = [latent_a]
            
        if latent_b_list is not None and latent_b_list.strip():
            vec_b = self._parse_vector(latent_b_list, latent_b)
        else:
            vec_b = [latent_b]
            
        # Validate lengths
        if len(vec_a) != len(vec_b):
            return (0.0, False, "Vector lengths must match")
            
        # Validate t
        if t < 0.0 or t > 1.0:
            return (0.0, False, "t must be between 0 and 1")
            
        # Perform interpolation
        try:
            if method == "lerp":
                result = self._lerp(vec_a, vec_b, t)
            elif method == "slerp":
                result = self._slerp(vec_a, vec_b, t)
            else:
                return (0.0, False, f"Unknown method: {method}")
                
            # Return first element as FLOAT output, but the full vector is conceptually the output
            # Since RETURN_TYPES is FLOAT, we return the first element. 
            # In a real ComfyUI node with LATENT types, we'd return the tensor.
            # Here we return the first element to satisfy the FLOAT return type.
            return (result[0], True, "Success")
            
        except Exception as e:
            return (0.0, False, f"Error: {str(e)}")

NODE_CLASS_MAPPINGS = {
    "PSN_LatentInterpolator": PSN_LatentInterpolator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LatentInterpolator": "PSN Latent Interpolator"
}
