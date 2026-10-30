"""
PSN_FluxNAG: Pure-logic configuration and validation for Normalized Attention Guidance (NAG).

This module implements the secure-by-design, pure-Python logic portion of the NAG node.
It does NOT touch torch, ComfyUI internals, or GPU memory. Instead, it validates the
NAG parameters, computes the effective guidance scale, and produces a JSON-serializable
configuration payload that a downstream (torch-based) wrapper would consume to patch
the model's attention hooks.

The node accepts plain values (floats, booleans, strings) and returns a validated
configuration dict plus a human-readable status string.
"""

import json
import math

CAT = "ParametricStudio/Flux"

# Allow-list of model families that support NAG
_SUPPORTED_MODELS = ("flux", "flux2klein", "anima")

# Valid NAG scale bounds
_NAG_SCALE_MIN = 0.0
_NAG_SCALE_MAX = 10.0


def _validate_nag_scale(nag_scale):
    """Validate nag_scale is a finite number within bounds. Returns (ok, value, reason)."""
    if not isinstance(nag_scale, (int, float)):
        return False, 1.0, "nag_scale must be a number"
    if isinstance(nag_scale, float) and (math.isnan(nag_scale) or math.isinf(nag_scale)):
        return False, 1.0, "nag_scale must be finite"
    if nag_scale < _NAG_SCALE_MIN or nag_scale > _NAG_SCALE_MAX:
        return False, 1.0, f"nag_scale must be in [{_NAG_SCALE_MIN}, {_NAG_SCALE_MAX}]"
    return True, float(nag_scale), "ok"


def _validate_model_family(model_family):
    """Validate model family is in the allow-list. Returns (ok, normalized, reason)."""
    if not isinstance(model_family, str):
        return False, "flux", "model_family must be a string"
    normalized = model_family.strip().lower()
    if normalized not in _SUPPORTED_MODELS:
        return False, "flux", f"model_family '{model_family}' not supported; use one of {list(_SUPPORTED_MODELS)}"
    return True, normalized, "ok"


def _build_nag_config(nag_scale, enable_negative, model_family):
    """
    Build the NAG configuration payload.
    
    NAG normalizes attention maps before applying guidance. For Flow Matching models
    like Flux, this avoids the over-saturation that standard CFG can cause.
    
    The effective guidance scale is computed as:
        effective_scale = nag_scale * (1.0 if enable_negative else 0.85)
    
    The 0.85 factor accounts for the reduced guidance signal when negative prompts
    are disabled (Flux is typically distilled and works well without them).
    """
    effective_scale = nag_scale * (1.0 if enable_negative else 0.85)
    
    config = {
        "nag_scale": nag_scale,
        "effective_scale": round(effective_scale, 6),
        "enable_negative": bool(enable_negative),
        "model_family": model_family,
        "normalization": "attention_l2",
        "guidance_method": "nag",
        "supported": True,
    }
    return config


class PSN_FluxNAG:
    """
    Applies Normalized Attention Guidance (NAG) configuration for Flux 2 Klein and Anima models.
    
    This node validates NAG parameters and produces a configuration payload.
    The actual model patching (attention hook injection) is performed by a
    downstream torch-based wrapper that consumes this configuration.
    
    Inputs:
        model_family (STRING): The model family identifier (e.g., "flux", "flux2klein", "anima").
        nag_scale (FLOAT): Strength of NAG (default 1.0, range [0.0, 10.0]).
        enable_negative (BOOLEAN): Whether to use negative prompts.
    
    Outputs:
        config (STRING): JSON-serialized NAG configuration payload.
        status (STRING): Human-readable status message.
        effective_scale (FLOAT): The computed effective guidance scale.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_family": (list(_SUPPORTED_MODELS), {"default": "flux"}),
                "nag_scale": ("FLOAT", {"default": 1.0, "min": _NAG_SCALE_MIN, "max": _NAG_SCALE_MAX, "step": 0.01}),
                "enable_negative": ("BOOLEAN", {"default": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("config", "status", "effective_scale")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_family, nag_scale, enable_negative):
        # Validate model family
        model_ok, model_norm, model_reason = _validate_model_family(model_family)
        
        # Validate nag_scale
        scale_ok, scale_val, scale_reason = _validate_nag_scale(nag_scale)
        
        # Validate enable_negative
        if not isinstance(enable_negative, bool):
            enable_negative = bool(enable_negative)
        
        if not model_ok:
            status = f"ERROR: {model_reason}"
            config = json.dumps({"supported": False, "error": model_reason})
            return (config, status, 0.0)
        
        if not scale_ok:
            status = f"ERROR: {scale_reason}"
            config = json.dumps({"supported": False, "error": scale_reason})
            return (config, status, 0.0)
        
        # Build configuration
        config = _build_nag_config(scale_val, enable_negative, model_norm)
        config_json = json.dumps(config, indent=2)
        
        status = (
            f"NAG configured for {model_norm}: "
            f"scale={scale_val}, effective={config['effective_scale']}, "
            f"negative={'enabled' if enable_negative else 'disabled'}"
        )
        
        return (config_json, status, config["effective_scale"])


NODE_CLASS_MAPPINGS = {
    "PSN_FluxNAG": PSN_FluxNAG,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FluxNAG": "Flux NAG (Normalized Attention Guidance)",
}
