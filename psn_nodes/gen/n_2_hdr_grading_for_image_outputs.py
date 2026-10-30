"""ParametricStudio: HDR tone mapping and color grading for image outputs.

Applies a tone mapping operator (Reinhard, ACES approximation, or Filmic) to
high-dynamic-range images (values may exceed 1.0), then applies exposure and
saturation adjustments, and clamps the result to [0, 1] for display.
"""

import torch

CAT = "ParametricStudio/Color"


def _as_tensor(image):
    """Validate and return a float32 torch tensor for an IMAGE input."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image must have shape [B, H, W, C]")
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError("image channels must be 1, 3 or 4")
    return image.detach().to(torch.float32).clone()


def _srgb_to_linear(x):
    """Convert sRGB-encoded values to linear light (vectorized)."""
    return torch.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(x):
    """Convert linear light values to sRGB-encoded values (vectorized)."""
    return torch.where(
        x <= 0.0031308,
        12.92 * x,
        1.055 * (x.clamp(min=0.0) ** (1.0 / 2.4)) - 0.055,
    )


def _reinhard(x):
    """Reinhard tone mapping: x / (1 + x)."""
    return x / (1.0 + x)


def _aces_approx(x):
    """Narkowicz ACES filmic approximation (per channel)."""
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14
    return ((x * (a * x + b)) / (x * (c * x + d) + e)).clamp(min=0.0)


def _filmic(x):
    """Simple filmic curve: smoothstep-like S-curve with soft highlights."""
    # Normalize-ish: map 0..1 through an S-curve, keep >1 values compressed.
    # Use a soft knee: x * (1 - x/(1+x)) style, then S-curve.
    soft = x / (1.0 + x)  # compresses highlights
    # Apply a gentle S-curve for contrast
    s = soft * soft * (3.0 - 2.0 * soft)  # smoothstep
    return s


def _apply_tone_map(x, mode):
    """Apply the selected tone mapping operator to linear-light values."""
    if mode == "Reinhard":
        return _reinhard(x)
    if mode == "ACES":
        return _aces_approx(x)
    if mode == "Filmic":
        return _filmic(x)
    raise ValueError(f"unknown tone_map_mode: {mode!r}")


def _apply_saturation(x, saturation):
    """Adjust saturation around the luma axis (per pixel)."""
    if saturation == 1.0:
        return x
    # Luma weights (Rec. 709)
    if x.shape[-1] == 1:
        return x
    if x.shape[-1] == 4:
        rgb = x[..., :3]
        alpha = x[..., 3:]
    else:
        rgb = x
        alpha = None
    luma = (0.2126 * rgb[..., 0:1] + 0.7152 * rgb[..., 1:2] + 0.0722 * rgb[..., 2:3])
    out = luma + saturation * (rgb - luma)
    if alpha is not None:
        out = torch.cat([out, alpha], dim=-1)
    return out


class PSN_HDR_Tone_Map:
    """Tone map and color grade HDR images to display range [0, 1]."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "tone_map_mode": ("Reinhard", "ACES", "Filmic"),
                "exposure": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 16.0}),
                "saturation": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 4.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("graded_image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, tone_map_mode, exposure, saturation):
        x = _as_tensor(image)
        # 1. Convert to linear light (assume input is sRGB-encoded).
        linear = _srgb_to_linear(x.clamp(min=0.0))
        # 2. Apply exposure (linear light).
        linear = linear * float(exposure)
        # 3. Tone map.
        mapped = _apply_tone_map(linear, tone_map_mode)
        # 4. Convert back to sRGB.
        srgb = _linear_to_srgb(mapped)
        # 5. Saturation.
        srgb = _apply_saturation(srgb, float(saturation))
        # 6. Clamp to [0, 1].
        out = srgb.clamp(0.0, 1.0)
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_HDR_Tone_Map": PSN_HDR_Tone_Map,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_HDR_Tone_Map": "HDR Tone Map (ParametricStudio)",
}
