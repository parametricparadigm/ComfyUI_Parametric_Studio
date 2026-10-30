"""
PSN_Regional_Noise_Perturbation: Applies localized noise perturbations to conditioning data.

This module implements a pure-logic, secure-by-design version of a regional noise
perturbation node. Since the original spec requires GPU/torch tensors (CONDITIONING,
MASK), this implementation operates on plain Python data structures (lists of numbers
representing flattened tensors) and JSON-serializable inputs.

The node generates deterministic pseudo-random noise (Gaussian, Perlin-like, or White)
based on a seed, applies it only to regions where the mask is non-zero, scales by
noise_strength, and adds it to the input conditioning values.

No torch, no numpy, no file I/O, no network. Pure standard library only.
"""

import math
import random
import json

# Allowed noise types
_NOISE_TYPES = ["gaussian", "perlin", "white"]

# Category for the node
CAT = "ParametricStudio/Noise"


def _generate_noise(size, noise_type, seed):
    """
    Generate a list of noise values of the given size.
    
    Args:
        size: int, number of noise values to generate
        noise_type: str, one of "gaussian", "perlin", "white"
        seed: int, random seed for reproducibility
    
    Returns:
        list of floats
    """
    rng = random.Random(seed)
    noise = []
    
    if noise_type == "white":
        # Uniform random in [-1, 1]
        for _ in range(size):
            noise.append(rng.uniform(-1.0, 1.0))
    
    elif noise_type == "gaussian":
        # Approximate Gaussian using Box-Muller transform
        for _ in range(size):
            u1 = rng.random()
            u2 = rng.random()
            # Avoid log(0)
            if u1 < 1e-10:
                u1 = 1e-10
            z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
            # Clamp to reasonable range
            z = max(-4.0, min(4.0, z))
            noise.append(z)
    
    elif noise_type == "perlin":
        # Simplified 1D Perlin-like noise: smooth interpolation of random values
        # Generate a set of random control points and interpolate
        num_points = max(2, size // 4 + 2)
        control_points = [rng.uniform(-1.0, 1.0) for _ in range(num_points)]
        
        for i in range(size):
            # Map index to position in control point space
            pos = (i / max(1, size - 1)) * (num_points - 1)
            idx = int(pos)
            frac = pos - idx
            
            # Smoothstep interpolation
            t = frac * frac * (3 - 2 * frac)
            
            if idx < num_points - 1:
                val = control_points[idx] * (1 - t) + control_points[idx + 1] * t
            else:
                val = control_points[-1]
            
            noise.append(val)
    
    else:
        raise ValueError(f"Unknown noise type: {noise_type}")
    
    return noise


def _apply_regional_noise(conditioning, mask, noise_strength, noise_type, seed):
    """
    Apply regional noise perturbation to conditioning data.
    
    Args:
        conditioning: list of floats (flattened tensor)
        mask: list of floats (flattened mask, same length as conditioning)
        noise_strength: float, scale factor for noise
        noise_type: str, one of "gaussian", "perlin", "white"
        seed: int, random seed
    
    Returns:
        tuple: (perturbed_conditioning, reason_string)
    """
    # Validate inputs
    if not isinstance(conditioning, list):
        raise TypeError("conditioning must be a list of numbers")
    if not isinstance(mask, list):
        raise TypeError("mask must be a list of numbers")
    if len(conditioning) != len(mask):
        raise ValueError("conditioning and mask must have the same length")
    if not isinstance(noise_strength, (int, float)):
        raise TypeError("noise_strength must be a number")
    if noise_type not in _NOISE_TYPES:
        raise ValueError(f"noise_type must be one of {_NOISE_TYPES}")
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    
    size = len(conditioning)
    if size == 0:
        return (conditioning, "Empty input, no perturbation applied")
    
    # Generate noise
    noise = _generate_noise(size, noise_type, seed)
    
    # Apply noise only where mask is non-zero
    perturbed = []
    masked_count = 0
    for i in range(size):
        if mask[i] != 0.0:
            perturbed.append(conditioning[i] + noise[i] * noise_strength)
            masked_count += 1
        else:
            perturbed.append(conditioning[i])
    
    reason = f"Applied {noise_type} noise to {masked_count}/{size} elements with strength {noise_strength}"
    return (perturbed, reason)


class PSN_Regional_Noise_Perturbation:
    """
    Applies localized noise perturbations to conditioning data within masked regions.
    
    This node generates deterministic pseudo-random noise and adds it to the conditioning
    values only where the mask is non-zero. The noise is scaled by noise_strength.
    
    Inputs:
        conditioning: list of floats (flattened conditioning tensor)
        mask: list of floats (flattened mask, same length as conditioning)
        noise_strength: float, scale factor for the noise
        noise_type: str, one of "gaussian", "perlin", "white"
        seed: int, random seed for reproducibility
    
    Outputs:
        conditioning: list of floats (perturbed conditioning)
        reason: str, description of what was applied
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("LIST", {"default": []}),
                "mask": ("LIST", {"default": []}),
                "noise_strength": ("FLOAT", {"default": 0.1, "min": -1e9, "max": 1e9, "step": 0.001}),
                "noise_type": (_NOISE_TYPES,),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**31 - 1}),
            },
            "optional": {}
        }
    
    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("conditioning", "reason")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, conditioning, mask, noise_strength, noise_type, seed):
        perturbed, reason = _apply_regional_noise(
            conditioning, mask, noise_strength, noise_type, seed
        )
        return (perturbed, reason)


# Module-level mappings
NODE_CLASS_MAPPINGS = {
    "PSN_Regional_Noise_Perturbation": PSN_Regional_Noise_Perturbation
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Regional_Noise_Perturbation": "Regional Noise Perturbation"
}
