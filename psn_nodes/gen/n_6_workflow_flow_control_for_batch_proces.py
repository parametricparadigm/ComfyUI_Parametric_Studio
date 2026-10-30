"""
PSN Workflow Flow Control for Batch Processing (pure-logic core).

This module implements the *logic* of batch conditioning loops and conditioning
variation generation without any GPU/torch/ComfyUI internals. Because the real
nodes require torch tensors (CONDITIONING, LATENT, MODEL, IMAGE), this module
exposes only the secure, pure-Python parts:

  * PSN_Conditioning_Variation_Generator: builds a deterministic list of
    "variation specs" (dicts) from a base conditioning description.
  * PSN_Batch_Conditioning_Loop: validates a batch of conditioning specs and
    produces a *plan* (list of per-item sampling configs) that a real sampler
    would execute. It never touches a GPU.

All functions take plain values (numbers, strings, lists, dicts) and return
plain values. No network, no file I/O, no subprocess, no torch.
"""

import math
import random

CAT = "ParametricStudio/FlowControl"

# Allowed variation types
_VARIATION_TYPES = ["noise", "scale", "shift"]


def _clamp(value, lo, hi):
    """Clamp value into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _validate_positive_int(value, name):
    """Validate that value is a positive integer (>=1)."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value}")
    return value


def _validate_float(value, name, lo, hi):
    """Validate that value is a float within [lo, hi]."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    v = float(value)
    if v < lo or v > hi:
        raise ValueError(f"{name} must be in [{lo}, {hi}], got {v}")
    return v


def _validate_steps(steps):
    """Validate sampler steps."""
    if not isinstance(steps, int) or isinstance(steps, bool):
        raise ValueError(f"steps must be an integer, got {type(steps).__name__}")
    if steps < 1:
        raise ValueError(f"steps must be >= 1, got {steps}")
    if steps > 1000:
        raise ValueError(f"steps must be <= 1000, got {steps}")
    return steps


def _validate_cfg(cfg):
    """Validate CFG scale."""
    if isinstance(cfg, bool) or not isinstance(cfg, (int, float)):
        raise ValueError(f"cfg must be a number, got {type(cfg).__name__}")
    v = float(cfg)
    if v < 0.0:
        raise ValueError(f"cfg must be >= 0.0, got {v}")
    if v > 100.0:
        raise ValueError(f"cfg must be <= 100.0, got {v}")
    return v


def _normalize_conditioning(base_conditioning):
    """
    Normalize a base conditioning input into a dict with expected keys.
    Accepts either a dict or a string (treated as prompt).
    """
    if isinstance(base_conditioning, str):
        return {"prompt": base_conditioning, "weight": 1.0, "bias": 0.0}
    if isinstance(base_conditioning, dict):
        result = {}
        result["prompt"] = str(base_conditioning.get("prompt", ""))
        result["weight"] = float(base_conditioning.get("weight", 1.0))
        result["bias"] = float(base_conditioning.get("bias", 0.0))
        return result
    raise ValueError(
        f"base_conditioning must be a string or dict, got {type(base_conditioning).__name__}"
    )


def _apply_variation(base, variation_type, magnitude, index, rng):
    """
    Apply a single variation to the base conditioning dict.
    Returns a new dict representing the varied conditioning.
    """
    varied = dict(base)
    varied["variation_index"] = index
    varied["variation_type"] = variation_type
    varied["magnitude"] = magnitude

    if variation_type == "noise":
        # Add small random noise to weight and bias
        noise_w = rng.uniform(-magnitude, magnitude)
        noise_b = rng.uniform(-magnitude, magnitude)
        varied["weight"] = _clamp(base["weight"] + noise_w, 0.0, 10.0)
        varied["bias"] = _clamp(base["bias"] + noise_b, -10.0, 10.0)
    elif variation_type == "scale":
        # Scale the weight by (1 + magnitude * random_factor)
        factor = 1.0 + rng.uniform(-magnitude, magnitude)
        factor = _clamp(factor, 0.0, 10.0)
        varied["weight"] = _clamp(base["weight"] * factor, 0.0, 10.0)
    elif variation_type == "shift":
        # Shift the bias by a random amount
        shift = rng.uniform(-magnitude, magnitude)
        varied["bias"] = _clamp(base["bias"] + shift, -10.0, 10.0)
    else:
        raise ValueError(f"Unknown variation_type: {variation_type}")

    return varied


class PSN_Conditioning_Variation_Generator:
    """
    Generates multiple variations of a base conditioning by applying
    deterministic (seeded) perturbations or scaling factors.

    Pure-logic: returns a list of conditioning spec dicts.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_conditioning": ("STRING", {"default": "a cat", "multiline": True}),
                "variation_type": (_VARIATION_TYPES,),
                "num_variations": ("INT", {"default": 4, "min": 1, "max": 100}),
                "magnitude": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1}),
            },
            "optional": {
                "base_weight": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "base_bias": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("CONDITIONING_LIST",)
    RETURN_NAMES = ("conditioning_list",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base_conditioning, variation_type, num_variations, magnitude, seed,
            base_weight=None, base_bias=None):
        # Validate inputs
        if variation_type not in _VARIATION_TYPES:
            raise ValueError(f"variation_type must be one of {_VARIATION_TYPES}, got {variation_type}")
        num_variations = _validate_positive_int(num_variations, "num_variations")
        magnitude = _validate_float(magnitude, "magnitude", 0.0, 1.0)
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
        if seed < 0:
            raise ValueError(f"seed must be >= 0, got {seed}")

        # Normalize base conditioning
        if isinstance(base_conditioning, dict):
            base = _normalize_conditioning(base_conditioning)
        else:
            base = _normalize_conditioning(str(base_conditioning))

        # Override weight/bias if provided
        if base_weight is not None:
            base["weight"] = _validate_float(base_weight, "base_weight", 0.0, 10.0)
        if base_bias is not None:
            base["bias"] = _validate_float(base_bias, "base_bias", -10.0, 10.0)

        # Generate variations with a seeded RNG for determinism
        rng = random.Random(seed)
        variations = []
        for i in range(num_variations):
            varied = _apply_variation(base, variation_type, magnitude, i, rng)
            variations.append(varied)

        return (variations,)


class PSN_Batch_Conditioning_Loop:
    """
    Validates a batch of conditioning specs and produces a sampling plan.

    Pure-logic: does NOT run a sampler. Returns a list of per-item sampling
    configs (dicts) that a real GPU sampler node would execute. This allows
    the graph to be validated and planned without torch.

    Inputs:
      conditioning_list: list of conditioning spec dicts (from generator or manual)
      steps: INT
      cfg: FLOAT
      seed: INT (base seed; each item gets seed + index)

    Outputs:
      plan: list of dicts, one per conditioning item, with keys:
        index, prompt, weight, bias, steps, cfg, seed
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning_list": ("CONDITIONING_LIST",),
                "steps": ("INT", {"default": 20, "min": 1, "max": 1000}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1}),
            },
            "optional": {
                "max_batch_size": ("INT", {"default": 64, "min": 1, "max": 256}),
            },
        }

    RETURN_TYPES = ("BATCH_PLAN", "INT")
    RETURN_NAMES = ("plan", "batch_size")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, conditioning_list, steps, cfg, seed, max_batch_size=None):
        # Validate steps and cfg
        steps = _validate_steps(steps)
        cfg = _validate_cfg(cfg)
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
        if seed < 0:
            raise ValueError(f"seed must be >= 0, got {seed}")

        # Validate conditioning_list
        if not isinstance(conditioning_list, (list, tuple)):
            raise ValueError(
                f"conditioning_list must be a list or tuple, got {type(conditioning_list).__name__}"
            )
        if len(conditioning_list) == 0:
            raise ValueError("conditioning_list must not be empty")

        # Validate max_batch_size
        if max_batch_size is not None:
            max_batch_size = _validate_positive_int(max_batch_size, "max_batch_size")
            if len(conditioning_list) > max_batch_size:
                raise ValueError(
                    f"conditioning_list length {len(conditioning_list)} exceeds max_batch_size {max_batch_size}"
                )

        # Build plan
        plan = []
        for i, cond in enumerate(conditioning_list):
            if isinstance(cond, str):
                spec = _normalize_conditioning(cond)
            elif isinstance(cond, dict):
                spec = _normalize_conditioning(cond)
            else:
                raise ValueError(
                    f"conditioning_list[{i}] must be a string or dict, got {type(cond).__name__}"
                )

            plan.append({
                "index": i,
                "prompt": spec["prompt"],
                "weight": spec["weight"],
                "bias": spec["bias"],
                "steps": steps,
                "cfg": cfg,
                "seed": seed + i,
            })

        return (plan, len(plan))


NODE_CLASS_MAPPINGS = {
    "PSN_Conditioning_Variation_Generator": PSN_Conditioning_Variation_Generator,
    "PSN_Batch_Conditioning_Loop": PSN_Batch_Conditioning_Loop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Conditioning_Variation_Generator": "PSN Conditioning Variation Generator",
    "PSN_Batch_Conditioning_Loop": "PSN Batch Conditioning Loop",
}
