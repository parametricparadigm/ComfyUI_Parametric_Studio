"""
PSN_ACES_OutputTransform

Pure-logic, secure-by-design implementation of the ACES2065-1 -> display-space
output transform pipeline.

Because the real pipeline requires OpenColorIO and torch (GPU), this module
implements ONLY the pure-logic, secure-by-design parts:
  * config validation (output space, tone mapping, exposure),
  * allow-list checks,
  * exposure / tone-mapping math on plain Python floats,
  * a deterministic dithering helper for low-bit-depth quantization,
  * a small, dependency-free sRGB <-> linear <-> ACES2065-1 color-space
    conversion used for round-trip testing.

It never opens a socket, never touches the file system, never imports torch
or comfy, and never performs network / subprocess / eval / exec. All public
functions take plain values (numbers, strings, JSON text) and return plain
values.
"""

import json
import math

# ---------------------------------------------------------------------------
# Constants / allow-lists
# ---------------------------------------------------------------------------

OUTPUT_SPACES = ("sRGB", "Display_P3", "HDR10_PQ", "HLG")
TONE_MAPPINGS = ("None", "Reinhard", "ACES_RRT", "Narkowicz")

# ACES2065-1 (AP0) -> linear sRGB (AP1-ish) 3x3 matrix (approx, for testing).
# These are representative matrices; the real pipeline uses OCIO.
_AP0_TO_AP1 = (
    (1.4514393161271527, -0.23631404356986798, -0.21512527255728473),
    (-0.07655377038290472, 1.1369642154724523, -0.06041044508954758),
    (-0.018257334884137926, -0.11510967829050776, 1.1333670131746456),
)
_AP1_TO_AP0 = (
    (0.6954522474069378, 0.1406783980923273, 0.16386943005510455),
    (0.04479456337200708, 0.8596711184976778, 0.09551431813031508),
    (0.0, 0.0, 0.8248792024535458),
)

# sRGB transfer function constants
_SRGB_K = 0.055
_SRGB_C = 1.0 + _SRGB_K


def _clamp01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _srgb_to_linear(c):
    c = _clamp01(c)
    if c <= 0.04045:
        return c / 12.92
    return ((c + _SRGB_K) / _SRGB_C) ** 2.4


def _linear_to_srgb(c):
    if c <= 0.0031308:
        return 12.92 * c
    return _SRGB_C * (c ** (1.0 / 2.4)) - _SRGB_K


def _mat3_mul(m, v):
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def aces_to_srgb_linear(rgb):
    """Convert ACES2065-1 (AP0) linear RGB to linear sRGB."""
    return _mat3_mul(_AP0_TO_AP1, rgb)


def srgb_linear_to_aces(rgb):
    """Convert linear sRGB to ACES2065-1 (AP0) linear RGB."""
    return _mat3_mul(_AP1_TO_AP0, rgb)


# ---------------------------------------------------------------------------
# Tone mapping (pure float math)
# ---------------------------------------------------------------------------

def tone_map_reinhard(x, exposure=0.0):
    """Reinhard tone mapping: x / (1 + x)."""
    return x / (1.0 + x)


def tone_map_narkowicz(x, exposure=0.0):
    """Narkowicz (Uncharted 2) tone mapping."""
    a, b, c, d, e, f = 2.51, 0.03, 2.43, 2.4, 0.59, 0.14
    return ((x * (a * x + c * b) + d * e) / (x * (a * x + b * b) + d * f)) - (e / f)


def tone_map_aces_rrt(x, exposure=0.0):
    """
    Simplified ACES RRT (Reference Rendering Transform) approximation.
    This is a pure-math stand-in for the full ACES RRT spline.
    """
    # ACES RRT approx: a smooth shoulder that compresses highlights.
    # Use a simple filmic curve: x * (1 + x) / (1 + 2x) style.
    return (x * (1.0 + x)) / (1.0 + 2.0 * x)


_TONE_MAP_FUNCS = {
    "None": lambda x, e: x,
    "Reinhard": tone_map_reinhard,
    "ACES_RRT": tone_map_aces_rrt,
    "Narkowicz": tone_map_narkowicz,
}


def apply_tone_mapping(x, tone_mapping, exposure=0.0):
    """Apply the selected tone mapping to a single float value."""
    if tone_mapping not in _TONE_MAP_FUNCS:
        raise ValueError("Unknown tone mapping: %r" % (tone_mapping,))
    # Apply exposure in linear space (stops -> multiplier)
    if exposure != 0.0:
        x = x * (2.0 ** exposure)
    return _TONE_MAP_FUNCS[tone_mapping](x, exposure)


# ---------------------------------------------------------------------------
# Dithering helper (deterministic, pure Python)
# ---------------------------------------------------------------------------

def dither_quantize(value, bit_depth=8, seed=0):
    """
    Deterministic ordered dithering for a single scalar value.
    Uses a simple 2x2 Bayer matrix pattern based on the seed.
    Returns a quantized value in [0, 1].
    """
    if bit_depth < 1 or bit_depth > 32:
        raise ValueError("bit_depth must be in [1, 32]")
    levels = (1 << bit_depth) - 1
    # 2x2 Bayer matrix
    bayer = (0, 2, 1, 3)
    idx = seed % 4
    threshold = (bayer[idx] + 0.5) / 4.0
    # Add dither offset
    dithered = value + (threshold - 0.5) / levels
    dithered = _clamp01(dithered)
    return round(dithered * levels) / levels


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def validate_config(output_space, tone_mapping, exposure):
    """
    Validate the output transform configuration.
    Returns (ok: bool, reason: str).
    """
    if output_space not in OUTPUT_SPACES:
        return False, "output_space must be one of %s" % (OUTPUT_SPACES,)
    if tone_mapping not in TONE_MAPPINGS:
        return False, "tone_mapping must be one of %s" % (TONE_MAPPINGS,)
    if not isinstance(exposure, (int, float)):
        return False, "exposure must be a number"
    if math.isnan(exposure) or math.isinf(exposure):
        return False, "exposure must be finite"
    if exposure < -30.0 or exposure > 30.0:
        return False, "exposure out of range [-30, 30] stops"
    return True, "ok"


def parse_config_json(json_text):
    """
    Parse and validate a JSON config string.
    Returns (ok: bool, config_dict_or_None, reason: str).
    """
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return False, None, "invalid JSON"
    if not isinstance(data, dict):
        return False, None, "config must be a JSON object"
    output_space = data.get("output_space", "sRGB")
    tone_mapping = data.get("tone_mapping", "None")
    exposure = data.get("exposure", 0.0)
    ok, reason = validate_config(output_space, tone_mapping, exposure)
    if not ok:
        return False, None, reason
    config = {
        "output_space": output_space,
        "tone_mapping": tone_mapping,
        "exposure": float(exposure),
    }
    return True, config, "ok"


# ---------------------------------------------------------------------------
# Core transform (pure float, single pixel)
# ---------------------------------------------------------------------------

def transform_pixel(rgb_aces, output_space, tone_mapping, exposure=0.0,
                    bit_depth=8, dither_seed=0):
    """
    Transform a single ACES2065-1 linear RGB pixel to the target display space.
    rgb_aces: tuple of 3 floats in ACES2065-1 linear space.
    Returns tuple of 3 floats in the target display space (gamma-encoded for
    sRGB/Display_P3, linear for HDR10_PQ/HLG).
    """
    ok, reason = validate_config(output_space, tone_mapping, exposure)
    if not ok:
        raise ValueError(reason)

    # Apply tone mapping in ACES linear space
    mapped = tuple(
        apply_tone_mapping(c, tone_mapping, exposure) for c in rgb_aces
    )

    # Convert to linear sRGB
    linear_srgb = aces_to_srgb_linear(mapped)

    if output_space == "sRGB":
        out = tuple(_linear_to_srgb(c) for c in linear_srgb)
    elif output_space == "Display_P3":
        # Approximate: same gamma as sRGB, slightly wider gamut (approximated
        # here as sRGB gamma for pure-logic purposes)
        out = tuple(_linear_to_srgb(c) for c in linear_srgb)
    elif output_space == "HDR10_PQ":
        # HDR10: keep linear, no gamma. Values can exceed 1.0.
        out = linear_srgb
    elif output_space == "HLG":
        # HLG: approximate with a gamma-like curve
        out = tuple(_linear_to_srgb(c) for c in linear_srgb)
    else:
        raise ValueError("Unknown output space: %r" % (output_space,))

    # Dither and quantize for low-bit-depth output
    if bit_depth < 32:
        out = tuple(
            dither_quantize(c, bit_depth, dither_seed + i) for i, c in enumerate(out)
        )

    return out


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/Color"


class PSN_ACES_OutputTransform:
    """
    Converts images from ACES2065-1 working space to a target display space
    (sRGB, P3, HDR10, HLG) with tone mapping.

    NOTE: This is a pure-logic, secure-by-design implementation. It does NOT
    perform actual GPU image processing. It validates configuration, applies
    tone-mapping math, and provides a deterministic dithering helper. For
    real image processing, use OpenColorIO + torch.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_space": (list(OUTPUT_SPACES),),
                "tone_mapping": (list(TONE_MAPPINGS),),
                "exposure": ("FLOAT", {"default": 0.0, "min": -30.0, "max": 30.0, "step": 0.01}),
            },
            "optional": {
                "image": (None,),  # IMAGE placeholder; not used in pure-logic mode
                "config_json": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("status", "reason", "exposure_applied")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, output_space, tone_mapping, exposure, image=None, config_json=""):
        # If config_json is provided, parse and validate it
        if config_json:
            ok, config, reason = parse_config_json(config_json)
            if not ok:
                return ("error", reason, 0.0)
            output_space = config["output_space"]
            tone_mapping = config["tone_mapping"]
            exposure = config["exposure"]

        ok, reason = validate_config(output_space, tone_mapping, exposure)
        if not ok:
            return ("error", reason, 0.0)

        # In a real implementation, we would process the image here.
        # For pure-logic mode, we just report success and the applied exposure.
        return ("ok", reason, float(exposure))


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ACES_OutputTransform": PSN_ACES_OutputTransform,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ACES_OutputTransform": "ACES Output Transform",
}
