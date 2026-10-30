"""
PSN_HDR_Color_Manager: Pure-logic color management and HDR tone mapping configuration.

This module implements the secure, pure-logic portion of a color-managed video export
node for HDR content. It does NOT perform actual pixel manipulation, file I/O, or GPU
operations. Instead, it validates ICC profile names, target color spaces, and HDR
settings, and computes deterministic tone-mapping parameters (e.g., exposure, gamma,
clipping thresholds) that a downstream GPU/CPU renderer would use.

Inputs are plain values (strings, booleans, numbers). The node outputs a configuration
dictionary (as a JSON string) and a boolean indicating whether the configuration is
valid.

Dependencies: Pure Python standard library only.
"""

import json
import math

# Allowed ICC profile names (allow-list to prevent arbitrary file paths)
ALLOWED_ICC_PROFILES = [
    "sRGB",
    "Display P3",
    "Rec.2020",
    "Adobe RGB",
    "ProPhoto RGB",
    "DCI-P3",
]

# Allowed target color spaces
ALLOWED_TARGET_COLORSPACES = [
    "sRGB",
    "Display P3",
    "Rec.2020",
]

# HDR tone mapping modes
HDR_TONE_MAPPING_MODES = [
    "Reinhard",
    "ToneMapping",
    "ACES",
    "None",
]

# Default tone mapping parameters
DEFAULT_TONE_MAPPING_PARAMS = {
    "Reinhard": {"white_point": 1.0, "adapt_luminance": 0.18},
    "ToneMapping": {"white_point": 1.0, "adapt_luminance": 0.18},
    "ACES": {"white_point": 1.0, "adapt_luminance": 0.18},
    "None": {"white_point": 1.0, "adapt_luminance": 0.18},
}


def validate_icc_profile(icc_profile: str) -> tuple:
    """
    Validate the ICC profile name against the allow-list.
    Returns (is_valid: bool, reason: str).
    """
    if not isinstance(icc_profile, str):
        return False, "ICC profile must be a string"
    if icc_profile not in ALLOWED_ICC_PROFILES:
        return False, f"ICC profile '{icc_profile}' not in allow-list: {ALLOWED_ICC_PROFILES}"
    return True, "Valid ICC profile"


def validate_target_colorspace(target_colorspace: str) -> tuple:
    """
    Validate the target colorspace against the allow-list.
    Returns (is_valid: bool, reason: str).
    """
    if not isinstance(target_colorspace, str):
        return False, "Target colorspace must be a string"
    if target_colorspace not in ALLOWED_TARGET_COLORSPACES:
        return False, f"Target colorspace '{target_colorspace}' not in allow-list: {ALLOWED_TARGET_COLORSPACES}"
    return True, "Valid target colorspace"


def compute_tone_mapping_params(hdr_mode: bool, tone_mapping_mode: str, exposure: float, gamma: float) -> dict:
    """
    Compute tone mapping parameters based on HDR mode and settings.
    Returns a dictionary of parameters.
    """
    if not hdr_mode:
        return {
            "enabled": False,
            "mode": "None",
            "exposure": 1.0,
            "gamma": 1.0,
            "white_point": 1.0,
            "adapt_luminance": 0.18,
        }

    if tone_mapping_mode not in HDR_TONE_MAPPING_MODES:
        tone_mapping_mode = "Reinhard"

    base_params = DEFAULT_TONE_MAPPING_PARAMS.get(tone_mapping_mode, DEFAULT_TONE_MAPPING_PARAMS["Reinhard"]).copy()

    # Clamp exposure and gamma to reasonable ranges
    exposure = max(0.1, min(10.0, exposure))
    gamma = max(0.1, min(10.0, gamma))

    return {
        "enabled": True,
        "mode": tone_mapping_mode,
        "exposure": exposure,
        "gamma": gamma,
        "white_point": base_params["white_point"],
        "adapt_luminance": base_params["adapt_luminance"],
    }


def build_color_config(icc_profile: str, target_colorspace: str, hdr_mode: bool, tone_mapping_mode: str, exposure: float, gamma: float) -> tuple:
    """
    Build the full color management configuration.
    Returns (is_valid: bool, config_dict: dict, reason: str).
    """
    # Validate ICC profile
    icc_valid, icc_reason = validate_icc_profile(icc_profile)
    if not icc_valid:
        return False, {}, icc_reason

    # Validate target colorspace
    cs_valid, cs_reason = validate_target_colorspace(target_colorspace)
    if not cs_valid:
        return False, {}, cs_reason

    # Compute tone mapping parameters
    tone_params = compute_tone_mapping_params(hdr_mode, tone_mapping_mode, exposure, gamma)

    config = {
        "icc_profile": icc_profile,
        "target_colorspace": target_colorspace,
        "hdr_mode": hdr_mode,
        "tone_mapping": tone_params,
        "color_conversion": {
            "source": icc_profile,
            "target": target_colorspace,
            "method": "matrix" if icc_profile == target_colorspace else "lut",
        },
    }

    return True, config, "Configuration valid"


class PSN_HDR_Color_Manager:
    """
    Color-Managed Video Export for HDR Content.

    Validates ICC profile, target colorspace, and HDR tone mapping settings.
    Outputs a JSON configuration string that a downstream renderer would use
    to perform actual color conversion and tone mapping.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "icc_profile": (ALLOWED_ICC_PROFILES,),
                "target_colorspace": (ALLOWED_TARGET_COLORSPACES,),
                "hdr_mode": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "tone_mapping_mode": (HDR_TONE_MAPPING_MODES,),
                "exposure": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.01}),
                "gamma": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("valid", "config_json", "reason")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Color"

    def run(self, icc_profile, target_colorspace, hdr_mode, tone_mapping_mode="Reinhard", exposure=1.0, gamma=1.0):
        is_valid, config, reason = build_color_config(
            icc_profile=icc_profile,
            target_colorspace=target_colorspace,
            hdr_mode=hdr_mode,
            tone_mapping_mode=tone_mapping_mode,
            exposure=exposure,
            gamma=gamma,
        )
        config_json = json.dumps(config, indent=2) if is_valid else "{}"
        return (is_valid, config_json, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_HDR_Color_Manager": PSN_HDR_Color_Manager,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_HDR_Color_Manager": "HDR Color Manager",
}
