"""
PSN_GeneralizedGuidance: Pure-logic implementation of generalized guidance forms.

This module implements the mathematical core of Power Law CFG and CFG++ methods
without requiring torch or ComfyUI. It operates on plain Python lists of floats
representing the conditional and unconditional noise vectors.

The actual model patching in ComfyUI would wrap these pure functions.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Guidance"

# Allowed methods
_METHODS = ["Standard", "PowerLaw", "CFG++"]

# Allowed power range
_POWER_MIN = 0.0
_POWER_MAX = 10.0

# Allowed CFG scale range
_CFG_MIN = 0.0
_CFG_MAX = 100.0


def _validate_inputs(cond, uncond, method, power, cfg_scale):
    """Validate all inputs and return (ok, error_message)."""
    if not isinstance(cond, (list, tuple)):
        return False, "cond must be a list or tuple of numbers"
    if not isinstance(uncond, (list, tuple)):
        return False, "uncond must be a list or tuple of numbers"
    if len(cond) != len(uncond):
        return False, "cond and uncond must have the same length"
    if len(cond) == 0:
        return False, "cond and uncond must not be empty"
    for i, (c, u) in enumerate(zip(cond, uncond)):
        if not isinstance(c, (int, float)):
            return False, f"cond[{i}] must be a number, got {type(c).__name__}"
        if not isinstance(u, (int, float)):
            return False, f"uncond[{i}] must be a number, got {type(u).__name__}"
    if method not in _METHODS:
        return False, f"method must be one of {_METHODS}, got {method!r}"
    if not isinstance(power, (int, float)):
        return False, f"power must be a number, got {type(power).__name__}"
    if power < _POWER_MIN or power > _POWER_MAX:
        return False, f"power must be in [{_POWER_MIN}, {_POWER_MAX}], got {power}"
    if not isinstance(cfg_scale, (int, float)):
        return False, f"cfg_scale must be a number, got {type(cfg_scale).__name__}"
    if cfg_scale < _CFG_MIN or cfg_scale > _CFG_MAX:
        return False, f"cfg_scale must be in [{_CFG_MIN}, {_CFG_MAX}], got {cfg_scale}"
    return True, ""


def _apply_standard(cond, uncond, cfg_scale):
    """Standard CFG: noise = uncond + cfg * (cond - uncond)."""
    return [u + cfg_scale * (c - u) for c, u in zip(cond, uncond)]


def _apply_power_law(cond, uncond, cfg_scale, power):
    """Power Law CFG: noise = uncond + cfg * (cond - uncond)^power.
    
    For negative differences, we use sign-preserving power:
    (x)^power = sign(x) * |x|^power
    """
    result = []
    for c, u in zip(cond, uncond):
        diff = c - u
        if diff >= 0:
            powered = diff ** power
        else:
            powered = -(abs(diff) ** power)
        result.append(u + cfg_scale * powered)
    return result


def _apply_cfg_plus_plus(cond, uncond, cfg_scale, power):
    """CFG++: Balances positive and negative contributions.
    
    Formula: noise = uncond + cfg * (cond - uncond) * (1 + power * |cond - uncond|)
    This amplifies guidance where the difference is large.
    """
    result = []
    for c, u in zip(cond, uncond):
        diff = c - u
        magnitude = abs(diff)
        factor = 1.0 + power * magnitude
        result.append(u + cfg_scale * diff * factor)
    return result


def compute_guidance(cond, uncond, method, power, cfg_scale):
    """Compute the guided noise vector using the specified method.
    
    Args:
        cond: list of floats - conditional noise
        uncond: list of floats - unconditional noise
        method: str - one of "Standard", "PowerLaw", "CFG++"
        power: float - exponent for Power Law (default 1.0)
        cfg_scale: float - base CFG scale
    
    Returns:
        tuple: (ok, result_or_error, reason)
            ok: bool - whether computation succeeded
            result_or_error: list of floats or str error message
            reason: str - empty on success, error description on failure
    """
    ok, err = _validate_inputs(cond, uncond, method, power, cfg_scale)
    if not ok:
        return False, err, err
    
    if method == "Standard":
        result = _apply_standard(cond, uncond, cfg_scale)
    elif method == "PowerLaw":
        result = _apply_power_law(cond, uncond, cfg_scale, power)
    elif method == "CFG++":
        result = _apply_cfg_plus_plus(cond, uncond, cfg_scale, power)
    else:
        return False, f"Unknown method: {method}", f"Unknown method: {method}"
    
    return True, result, ""


class PSN_GeneralizedGuidance:
    """Applies Power Law CFG and CFG++ methods for alternative guidance approaches.
    
    Pure-logic implementation operating on plain Python lists of floats.
    In ComfyUI, this would patch a MODEL; here it computes the guided noise vector.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "cond": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "uncond": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "method": (_METHODS,),
                "power": ("FLOAT", {"default": 1.0, "min": _POWER_MIN, "max": _POWER_MAX, "step": 0.01}),
                "cfg_scale": ("FLOAT", {"default": 7.5, "min": _CFG_MIN, "max": _CFG_MAX, "step": 0.1}),
            },
            "optional": {
                "cond_vector": ("STRING", {"default": "[]", "multiline": True}),
                "uncond_vector": ("STRING", {"default": "[]", "multiline": True}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("success", "result_json", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, cond, uncond, method, power, cfg_scale, cond_vector=None, uncond_vector=None):
        """Run the generalized guidance computation.
        
        If cond_vector and uncond_vector are provided as JSON strings, they take
        precedence over the scalar cond/uncond inputs (which are then ignored).
        Otherwise, scalar cond/uncond are treated as single-element vectors.
        """
        import json

        # Determine the actual vectors to use
        if cond_vector is not None and uncond_vector is not None:
            try:
                cond_list = json.loads(cond_vector)
                uncond_list = json.loads(uncond_vector)
                if not isinstance(cond_list, list) or not isinstance(uncond_list, list):
                    return (False, "", "cond_vector and uncond_vector must be JSON arrays")
            except (json.JSONDecodeError, TypeError) as e:
                return (False, "", f"Failed to parse vector JSON: {e}")
        else:
            cond_list = [float(cond)]
            uncond_list = [float(uncond)]

        ok, result, reason = compute_guidance(cond_list, uncond_list, method, power, cfg_scale)
        if not ok:
            return (False, "", reason)

        result_json = json.dumps(result)
        return (True, result_json, "")


NODE_CLASS_MAPPINGS = {
    "PSN_GeneralizedGuidance": PSN_GeneralizedGuidance,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_GeneralizedGuidance": "PSN Generalized Guidance",
}
