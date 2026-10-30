"""PSN_AutoColorAdapt: rule-based automatic color grading for ComfyUI.

Analyzes the input image (mean luminance, contrast, saturation, dominant
channel balance) and applies bounded exposure / contrast / saturation /
tint adjustments tuned per model family and target style.  Pure torch on
CPU; no heavy dependencies.
"""

import json
import math

import torch

CAT = "ParametricStudio/Color"

MODEL_FAMILIES = ["SDXL", "Flux.1", "SD1.5", "Custom"]
TARGET_STYLES = ["Neutral", "Vibrant", "Moody", "Cinematic"]

# Per-style target means for (exposure, contrast, saturation, tint) in a
# normalized space.  Tint is a small blue-warm bias in [-1, 1].
_STYLE_TARGETS = {
    "Neutral":    {"exposure": 0.0,  "contrast": 0.0,  "saturation": 0.0,  "tint": 0.0},
    "Vibrant":    {"exposure": 0.05, "contrast": 0.15, "saturation": 0.35, "tint": 0.0},
    "Moody":      {"exposure": -0.10, "contrast": 0.25, "saturation": -0.20, "tint": -0.15},
    "Cinematic":  {"exposure": -0.05, "contrast": 0.20, "saturation": 0.10, "tint": 0.10},
}

# Per-model-family gain: some families tend to output flatter / brighter
# images, so we scale the corrective term accordingly.
_FAMILY_GAIN = {
    "SDXL": 1.0,
    "Flux.1": 0.9,
    "SD1.5": 1.1,
    "Custom": 1.0,
}

# Hard caps to avoid over-correction (risk mitigation from the spec).
_MAX_EXPOSURE = 0.6
_MAX_CONTRAST = 0.6
_MAX_SATURATION = 0.6
_MAX_TINT = 0.3


def _as_image(image):
    """Validate and return a float tensor [B,H,W,C] in 0..1 (a copy)."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image must be 4D [B,H,W,C], got %dD" % image.dim())
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError("image channels must be 1, 3 or 4, got %d" % image.shape[-1])
    if image.shape[1] < 1 or image.shape[2] < 1:
        raise ValueError("image spatial dims must be >= 1")
    x = image.detach().to(torch.float32).clone()
    return x


def _rgb(x):
    """Return a [B,H,W,3] float tensor from a 1/3/4-channel image."""
    c = x.shape[-1]
    if c == 3:
        return x
    if c == 1:
        return x.expand(-1, -1, -1, 3).contiguous()
    return x[..., :3]


def _analyze(rgb):
    """Compute simple statistics of the image (all on CPU, no in-place ops)."""
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mean_lum = float(lum.mean().item())
    std_lum = float(lum.std().item()) if lum.numel() > 1 else 0.0
    # Saturation: mean of (max-min) per pixel.
    mx = rgb.max(dim=-1).values
    mn = rgb.min(dim=-1).values
    mean_sat = float((mx - mn).mean().item())
    # Channel balance: mean R - mean B (positive = warm).
    balance = float((r.mean() - b.mean()).item())
    return {
        "mean_lum": mean_lum,
        "std_lum": std_lum,
        "mean_sat": mean_sat,
        "balance": balance,
    }


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _compute_params(stats, model_family, target_style):
    """Rule-based parameter selection.

    Returns a dict with exposure, contrast, saturation, tint in bounded
    ranges.  The corrective term pushes the image toward a neutral
    mid-tone baseline, then the style target is added on top.
    """
    fam = _FAMILY_GAIN.get(model_family, 1.0)
    tgt = _STYLE_TARGETS.get(target_style, _STYLE_TARGETS["Neutral"])

    # Exposure: push mean luminance toward 0.5 (neutral baseline).
    exposure_corr = (0.5 - stats["mean_lum"]) * 1.2 * fam
    # Contrast: push std toward ~0.18 (typical photographic contrast).
    contrast_corr = (0.18 - stats["std_lum"]) * 1.5 * fam
    # Saturation: push mean saturation toward ~0.35.
    saturation_corr = (0.35 - stats["mean_sat"]) * 1.0 * fam
    # Tint: counteract strong warm/cool cast, then add style tint.
    tint_corr = -stats["balance"] * 0.8 * fam

    exposure = _clamp(exposure_corr + tgt["exposure"], -_MAX_EXPOSURE, _MAX_EXPOSURE)
    contrast = _clamp(contrast_corr + tgt["contrast"], -_MAX_CONTRAST, _MAX_CONTRAST)
    saturation = _clamp(saturation_corr + tgt["saturation"], -_MAX_SATURATION, _MAX_SATURATION)
    tint = _clamp(tint_corr + tgt["tint"], -_MAX_TINT, _MAX_TINT)

    return {
        "exposure": round(exposure, 4),
        "contrast": round(contrast, 4),
        "saturation": round(saturation, 4),
        "tint": round(tint, 4),
        "model_family": model_family,
        "target_style": target_style,
        "stats": {
            "mean_lum": round(stats["mean_lum"], 4),
            "std_lum": round(stats["std_lum"], 4),
            "mean_sat": round(stats["mean_sat"], 4),
            "balance": round(stats["balance"], 4),
        },
    }


def _apply_params(rgb, params):
    """Apply the graded parameters to a [B,H,W,3] float tensor (0..1).

    Returns a new tensor; never mutates the input.
    """
    x = rgb.clone()
    # Exposure: linear gain around 0.5 pivot.
    exp = params["exposure"]
    x = x + exp
    # Contrast: scale around 0.5 pivot.
    con = params["contrast"]
    x = 0.5 + (x - 0.5) * (1.0 + con)
    # Saturation: blend toward luminance.
    sat = params["saturation"]
    lum = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
    x = x + (lum.unsqueeze(-1) - x) * sat
    # Tint: shift R and B oppositely (positive = warm).
    t = params["tint"]
    x[..., 0] = x[..., 0] + t * 0.5
    x[..., 2] = x[..., 2] - t * 0.5
    return x.clamp(0.0, 1.0)


class PSN_AutoColorAdapt:
    """Automatically adjust color grading parameters from image statistics."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "model_family": (MODEL_FAMILIES,),
                "target_style": (TARGET_STYLES,),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "params_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, model_family, target_style):
        x = _as_image(image)
        rgb = _rgb(x)
        stats = _analyze(rgb)
        params = _compute_params(stats, model_family, target_style)
        graded_rgb = _apply_params(rgb, params)

        # Rebuild the output image with the original channel count.
        c = x.shape[-1]
        if c == 1:
            out = graded_rgb[..., 0:1]
        elif c == 3:
            out = graded_rgb
        else:
            alpha = x[..., 3:4]
            out = torch.cat([graded_rgb, alpha], dim=-1)

        params_json = json.dumps(params, sort_keys=True)
        return (out, params_json)


NODE_CLASS_MAPPINGS = {
    "PSN_AutoColorAdapt": PSN_AutoColorAdapt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AutoColorAdapt": "Auto Color Adapt (ParametricStudio)",
}
