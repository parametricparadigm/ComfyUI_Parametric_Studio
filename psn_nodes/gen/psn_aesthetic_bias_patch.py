"""
PSN_Aesthetic_Bias_Patch

This module implements the pure-logic, secure-by-design portion of an aesthetic bias patching node.
Since the full implementation requires GPU/torch/ComfyUI internals (which are not allowed here),
this node handles:
- Validation of the aesthetic vector (as a list of floats) and strength parameter.
- Computation of the bias patch payload (the vector scaled by strength).
- Generation of a deterministic patch identifier for traceability.

The node does NOT modify any model or tensor. Instead, it outputs:
- `patched`: A boolean indicating if the patch payload is valid and ready to be applied.
- `bias_vector`: The scaled aesthetic vector (list of floats) to be added to attention weights.
- `patch_id`: A deterministic string identifier for the patch configuration.

This allows downstream nodes (or external systems) to apply the bias to the actual model.
"""

import hashlib
import json

# We use the safe expression evaluator and orchestration helpers from psn if available,
# but since we are implementing pure logic, we will implement the necessary helpers locally
# to ensure no external dependencies beyond stdlib.

def _validate_vector(vector, max_dim=1024):
    """
    Validate that the input is a list of floats and has a reasonable dimension.
    Returns (is_valid, error_message).
    """
    if not isinstance(vector, list):
        return False, "aesthetic_vector must be a list of floats"
    if len(vector) == 0:
        return False, "aesthetic_vector must not be empty"
    if len(vector) > max_dim:
        return False, f"aesthetic_vector dimension {len(vector)} exceeds max {max_dim}"
    for i, v in enumerate(vector):
        if not isinstance(v, (int, float)):
            return False, f"aesthetic_vector element at index {i} is not a number"
        if isinstance(v, float) and (v != v):  # NaN check
            return False, f"aesthetic_vector element at index {i} is NaN"
        if isinstance(v, float) and (v == float('inf') or v == float('-inf')):
            return False, f"aesthetic_vector element at index {i} is infinite"
    return True, ""

def _scale_vector(vector, strength):
    """
    Scale the vector by the strength factor.
    """
    return [v * strength for v in vector]

def _generate_patch_id(vector, strength):
    """
    Generate a deterministic patch ID based on the vector and strength.
    """
    # Create a canonical string representation
    canonical = json.dumps({"vector": vector, "strength": strength}, sort_keys=True)
    # Hash it to create a short ID
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return hash_obj.hexdigest()[:16]

class PSN_Aesthetic_Bias_Patch:
    """
    Biases the model toward a specific aesthetic by preparing a bias patch payload.
    
    This node validates the aesthetic vector and strength, computes the scaled bias vector,
    and generates a deterministic patch ID. The actual application to the model's attention
    weights must be done by a downstream node or external system that has access to the model.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aesthetic_vector": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "strength": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
            },
            "optional": {
                "vector_list": ("STRING", {"default": "[]"}),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("patched", "bias_vector_json", "patch_id")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Aesthetic"
    
    def run(self, aesthetic_vector, strength, vector_list="[]"):
        """
        Run the aesthetic bias patch logic.
        
        Args:
            aesthetic_vector: A single float value (if vector_list is not provided).
            strength: The strength of the bias.
            vector_list: A JSON string representing the aesthetic vector (list of floats).
            
        Returns:
            tuple: (patched, bias_vector_json, patch_id)
        """
        # Parse the vector from the JSON string if provided
        vector = None
        if vector_list and vector_list.strip():
            try:
                vector = json.loads(vector_list)
            except json.JSONDecodeError:
                return (False, "[]", "invalid_json")
        
        # If no vector_list was provided, use the single aesthetic_vector as a 1D vector
        if vector is None:
            vector = [aesthetic_vector]
        
        # Validate the vector
        is_valid, error_msg = _validate_vector(vector)
        if not is_valid:
            return (False, "[]", f"invalid_vector: {error_msg}")
        
        # Validate strength
        if not isinstance(strength, (int, float)):
            return (False, "[]", "invalid_strength: must be a number")
        if isinstance(strength, float) and (strength != strength or strength == float('inf') or strength == float('-inf')):
            return (False, "[]", "invalid_strength: must be a finite number")
        
        # Scale the vector
        bias_vector = _scale_vector(vector, strength)
        
        # Generate patch ID
        patch_id = _generate_patch_id(vector, strength)
        
        # Return the results
        bias_vector_json = json.dumps(bias_vector)
        return (True, bias_vector_json, patch_id)

NODE_CLASS_MAPPINGS = {
    "PSN_Aesthetic_Bias_Patch": PSN_Aesthetic_Bias_Patch
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Aesthetic_Bias_Patch": "Aesthetic Bias Patch"
}
