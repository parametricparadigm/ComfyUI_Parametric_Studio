"""
PSN StyleGAN Explore - Pure logic implementation for StyleGAN2 latent space exploration.

This module implements the pure-logic parts of the StyleGAN2 explorer:
- PSN_StyleGAN_Load: Validates model path format (no actual file loading).
- PSN_StyleGAN_Slerp: Performs spherical linear interpolation (slerp) between two latent vectors.
- PSN_StyleGAN_Generate: Validates latent tensor shape (no actual image generation).

NOTE: This implementation does NOT use torch, ComfyUI, or any GPU operations.
It operates on plain Python lists/tuples representing latent vectors.
The slerp function works on 1D vectors (flattened latents) and returns a list of interpolated vectors.
"""

import math
import json

CAT = "ParametricStudio/StyleGAN"

# Allowed model path extensions for validation
ALLOWED_MODEL_EXTENSIONS = (".pt", ".pth", ".ckpt", ".bin")


def _validate_model_path(model_path):
    """Validate that model_path is a string with an allowed extension."""
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if not model_path:
        return False, "model_path must not be empty"
    # Check extension
    lower_path = model_path.lower()
    if not any(lower_path.endswith(ext) for ext in ALLOWED_MODEL_EXTENSIONS):
        return False, f"model_path must end with one of {ALLOWED_MODEL_EXTENSIONS}"
    return True, "valid"


def _slerp_single(v1, v2, t):
    """
    Perform slerp between two 1D vectors v1 and v2 at parameter t.
    Returns a list of floats.
    """
    n = len(v1)
    if n != len(v2):
        raise ValueError("Vectors must have the same length")
    
    # Compute dot product
    dot = sum(a * b for a, b in zip(v1, v2))
    
    # Compute norms
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    
    # Handle edge cases
    if norm1 < 1e-10 or norm2 < 1e-10:
        # If either vector is near zero, fall back to linear interpolation
        return [a + t * (b - a) for a, b in zip(v1, v2)]
    
    # Normalize dot product
    dot = max(-1.0, min(1.0, dot / (norm1 * norm2)))
    
    theta = math.acos(dot)
    
    if theta < 1e-10:
        # Vectors are nearly parallel, use linear interpolation
        return [a + t * (b - a) for a, b in zip(v1, v2)]
    
    sin_theta = math.sin(theta)
    
    # Slerp formula
    result = []
    for a, b in zip(v1, v2):
        coeff1 = math.sin((1 - t) * theta) / sin_theta
        coeff2 = math.sin(t * theta) / sin_theta
        result.append(coeff1 * a + coeff2 * b)
    
    return result


def _slerp_sequence(latent_a, latent_b, num_frames, t_start, t_end):
    """
    Generate a sequence of slerp-interpolated vectors between latent_a and latent_b.
    
    Args:
        latent_a: list of floats (1D vector)
        latent_b: list of floats (1D vector)
        num_frames: int, number of frames to generate
        t_start: float, starting parameter (0.0)
        t_end: float, ending parameter (1.0)
    
    Returns:
        list of lists, each inner list is a 1D vector
    """
    if num_frames < 1:
        raise ValueError("num_frames must be at least 1")
    
    frames = []
    for i in range(num_frames):
        if num_frames == 1:
            t = t_start
        else:
            t = t_start + (t_end - t_start) * i / (num_frames - 1)
        frames.append(_slerp_single(latent_a, latent_b, t))
    
    return frames


class PSN_StyleGAN_Load:
    """
    Validates a StyleGAN2 model path. Does NOT actually load the model.
    Returns a placeholder model descriptor (JSON string) for downstream nodes.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {"default": "stylegan2.pt", "multiline": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("model",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, model_path):
        valid, reason = _validate_model_path(model_path)
        if not valid:
            raise ValueError(f"Invalid model path: {reason}")
        
        # Return a placeholder model descriptor
        model_descriptor = json.dumps({
            "type": "stylegan2",
            "path": model_path,
            "status": "validated"
        })
        return (model_descriptor,)


class PSN_StyleGAN_Slerp:
    """
    Performs spherical linear interpolation (slerp) between two latent vectors.
    Input latents are expected as JSON strings representing 1D vectors (lists of floats).
    Output is a JSON string representing a list of interpolated vectors.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_a": ("STRING", {"default": "[1.0, 0.0, 0.0]", "multiline": False}),
                "latent_b": ("STRING", {"default": "[0.0, 1.0, 0.0]", "multiline": False}),
                "num_frames": ("INT", {"default": 10, "min": 1, "max": 1000, "step": 1}),
                "t_start": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "t_end": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("latents",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, latent_a, latent_b, num_frames, t_start, t_end):
        # Parse JSON vectors
        try:
            vec_a = json.loads(latent_a)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("latent_a must be a valid JSON array of numbers")
        
        try:
            vec_b = json.loads(latent_b)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("latent_b must be a valid JSON array of numbers")
        
        # Validate vectors
        if not isinstance(vec_a, list) or not all(isinstance(x, (int, float)) for x in vec_a):
            raise ValueError("latent_a must be a JSON array of numbers")
        if not isinstance(vec_b, list) or not all(isinstance(x, (int, float)) for x in vec_b):
            raise ValueError("latent_b must be a JSON array of numbers")
        if len(vec_a) != len(vec_b):
            raise ValueError("latent_a and latent_b must have the same length")
        if len(vec_a) == 0:
            raise ValueError("Latent vectors must not be empty")
        
        # Validate t range
        if t_start < 0.0 or t_start > 1.0:
            raise ValueError("t_start must be between 0.0 and 1.0")
        if t_end < 0.0 or t_end > 1.0:
            raise ValueError("t_end must be between 0.0 and 1.0")
        
        # Perform slerp
        frames = _slerp_sequence(vec_a, vec_b, num_frames, t_start, t_end)
        
        # Return as JSON string
        return (json.dumps(frames),)


class PSN_StyleGAN_Generate:
    """
    Validates latent tensor shape. Does NOT actually generate images.
    Returns a placeholder image descriptor (JSON string).
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("STRING", {"default": "{}", "multiline": False}),
                "latents": ("STRING", {"default": "[]", "multiline": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("images",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, model, latents):
        # Validate model descriptor
        try:
            model_data = json.loads(model)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("model must be a valid JSON object")
        
        if not isinstance(model_data, dict):
            raise ValueError("model must be a JSON object")
        
        # Validate latents
        try:
            latent_frames = json.loads(latents)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("latents must be a valid JSON array")
        
        if not isinstance(latent_frames, list):
            raise ValueError("latents must be a JSON array")
        
        if len(latent_frames) == 0:
            raise ValueError("latents must contain at least one frame")
        
        # Validate each frame is a list of numbers
        for i, frame in enumerate(latent_frames):
            if not isinstance(frame, list):
                raise ValueError(f"Frame {i} must be a JSON array of numbers")
            if not all(isinstance(x, (int, float)) for x in frame):
                raise ValueError(f"Frame {i} must contain only numbers")
        
        # Return placeholder image descriptor
        image_descriptor = json.dumps({
            "type": "stylegan2_output",
            "num_frames": len(latent_frames),
            "latent_dim": len(latent_frames[0]),
            "status": "validated"
        })
        return (image_descriptor,)


NODE_CLASS_MAPPINGS = {
    "PSN_StyleGAN_Load": PSN_StyleGAN_Load,
    "PSN_StyleGAN_Slerp": PSN_StyleGAN_Slerp,
    "PSN_StyleGAN_Generate": PSN_StyleGAN_Generate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StyleGAN_Load": "PSN StyleGAN Load",
    "PSN_StyleGAN_Slerp": "PSN StyleGAN Slerp",
    "PSN_StyleGAN_Generate": "PSN StyleGAN Generate",
}
