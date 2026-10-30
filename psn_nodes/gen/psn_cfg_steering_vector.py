"""PSN_CFG_Steering_Vector: pure-logic CFG steering vector computation.

This module implements the mathematical core of a CFG (Classifier-Free Guidance)
steering vector injection without any GPU/torch/ComfyUI dependencies.

In a real ComfyUI node, a steering vector would be added to the model's
unconditional prediction to bias generation toward a specific direction.
The CFG formula is:

    output = uncond + strength * (cond - uncond)

With a steering vector `s` of magnitude `strength`, the effective
unconditional prediction becomes:

    uncond_eff = uncond + strength * s

So the final output becomes:

    output = (uncond + strength * s) + strength * (cond - uncond)
           = uncond + strength * s + strength * cond - strength * uncond
           = strength * cond + (1 - strength) * uncond + strength * s

This module provides:
  - PSN_CFG_Steering_Vector: a node that computes the effective CFG output
    given cond, uncond, strength, and a steering vector (all as plain
    numbers or JSON-encoded lists for multi-dimensional vectors).
  - Helper functions for validation and computation.

All inputs are plain Python values (floats, ints, strings containing JSON
lists). No torch, no ComfyUI, no file/network I/O.
"""

import json
import math

CAT = "ParametricStudio/CFG"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_vector(value):
    """Parse a steering vector from a float or a JSON list string.

    Returns a list of floats. Raises ValueError on bad input.
    """
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise ValueError("steering_vector string is empty")
        try:
            parsed = json.loads(s)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"steering_vector is not valid JSON: {exc}") from exc
        if isinstance(parsed, (int, float)):
            return [float(parsed)]
        if isinstance(parsed, list):
            out = []
            for i, item in enumerate(parsed):
                if not isinstance(item, (int, float)):
                    raise ValueError(
                        f"steering_vector element {i} is not a number: {type(item).__name__}"
                    )
                if isinstance(item, float) and (math.isnan(item) or math.isinf(item)):
                    raise ValueError(f"steering_vector element {i} is NaN or Inf")
                out.append(float(item))
            if not out:
                raise ValueError("steering_vector list is empty")
            return out
        raise ValueError(
            f"steering_vector JSON must be a number or list of numbers, got {type(parsed).__name__}"
        )
    raise ValueError(
        f"steering_vector must be a number or a JSON string, got {type(value).__name__}"
    )


def _validate_strength(strength):
    """Validate the strength parameter. Returns float or raises ValueError."""
    if not isinstance(strength, (int, float)):
        raise ValueError(f"strength must be a number, got {type(strength).__name__}")
    s = float(strength)
    if math.isnan(s) or math.isinf(s):
        raise ValueError("strength must be finite")
    return s


def _validate_cond_uncond(cond, uncond):
    """Validate cond and uncond values. Returns (cond_list, uncond_list)."""
    def _to_list(v, name):
        if isinstance(v, (int, float)):
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                raise ValueError(f"{name} must be finite")
            return [fv]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                raise ValueError(f"{name} string is empty")
            try:
                parsed = json.loads(s)
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(f"{name} is not valid JSON: {exc}") from exc
            if isinstance(parsed, (int, float)):
                fv = float(parsed)
                if math.isnan(fv) or math.isinf(fv):
                    raise ValueError(f"{name} must be finite")
                return [fv]
            if isinstance(parsed, list):
                out = []
                for i, item in enumerate(parsed):
                    if not isinstance(item, (int, float)):
                        raise ValueError(f"{name} element {i} is not a number")
                    fv = float(item)
                    if math.isnan(fv) or math.isinf(fv):
                        raise ValueError(f"{name} element {i} is NaN or Inf")
                    out.append(fv)
                if not out:
                    raise ValueError(f"{name} list is empty")
                return out
            raise ValueError(f"{name} JSON must be a number or list of numbers")
        raise ValueError(f"{name} must be a number or JSON string, got {type(v).__name__}")

    cond_list = _to_list(cond, "cond")
    uncond_list = _to_list(uncond, "uncond")
    if len(cond_list) != len(uncond_list):
        raise ValueError(
            f"cond and uncond must have the same dimensionality: "
            f"{len(cond_list)} vs {len(uncond_list)}"
        )
    return cond_list, uncond_list


def compute_cfg_with_steering(cond, uncond, strength, steering_vector):
    """Compute the effective CFG output with a steering vector.

    Formula:
        output[i] = strength * cond[i] + (1 - strength) * uncond[i] + strength * s[i]

    where s is the steering vector (broadcast if scalar).

    Returns a list of floats.
    """
    cond_list, uncond_list = _validate_cond_uncond(cond, uncond)
    s = _parse_vector(steering_vector)
    st = _validate_strength(strength)

    dim = len(cond_list)
    # Broadcast steering vector if it is a single element
    if len(s) == 1 and dim > 1:
        s = [s[0]] * dim
    elif len(s) != dim:
        raise ValueError(
            f"steering_vector dimension ({len(s)}) must match cond/uncond "
            f"dimension ({dim}) or be a scalar"
        )

    result = []
    for i in range(dim):
        val = st * cond_list[i] + (1.0 - st) * uncond_list[i] + st * s[i]
        result.append(val)
    return result


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_CFG_Steering_Vector:
    """Computes the effective CFG output with a steering vector injected.

    Pure-logic implementation: takes cond, uncond, strength, and steering
    vector as plain numbers or JSON-encoded lists, and returns the computed
    output as a JSON string. No torch, no ComfyUI model patching.

    In a full ComfyUI integration this would patch the model's CFG hook,
    but here we expose the math so it can be tested and composed safely.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "cond": (
                    "FLOAT",
                    {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001},
                ),
                "uncond": (
                    "FLOAT",
                    {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001},
                ),
                "strength": (
                    "FLOAT",
                    {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001},
                ),
                "steering_vector": (
                    "STRING",
                    {"default": "0.0", "multiline": False},
                ),
            },
            "optional": {
                "cond_json": (
                    "STRING",
                    {"default": "", "multiline": False},
                ),
                "uncond_json": (
                    "STRING",
                    {"default": "", "multiline": False},
                ),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("output_json", "output_scalar")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, cond, uncond, strength, steering_vector, cond_json="", uncond_json=""):
        """Compute CFG output with steering vector.

        If cond_json / uncond_json are provided (non-empty), they override
        the scalar cond/uncond inputs and are parsed as JSON lists.
        Otherwise cond and uncond are treated as scalars.

        Returns:
            output_json: JSON string of the result list.
            output_scalar: the first element of the result (for scalar use).
        """
        # Determine effective cond and uncond
        if cond_json and cond_json.strip():
            cond_val = cond_json
        else:
            cond_val = cond

        if uncond_json and uncond_json.strip():
            uncond_val = uncond_json
        else:
            uncond_val = uncond

        result = compute_cfg_with_steering(cond_val, uncond_val, strength, steering_vector)
        output_json = json.dumps(result)
        output_scalar = result[0]
        return (output_json, output_scalar)


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_CFG_Steering_Vector": PSN_CFG_Steering_Vector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CFG_Steering_Vector": "CFG Steering Vector",
}
