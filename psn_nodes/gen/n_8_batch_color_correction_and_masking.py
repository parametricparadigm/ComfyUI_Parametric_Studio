"""ParametricStudio: batch color correction with optional masking.

Applies per-image color corrections (auto white balance, auto contrast,
custom multipliers/offsets) to a batch of images, blending the corrected
result with the original according to a per-pixel mask.
"""

import json

import torch

CAT = "ParametricStudio/Color"

_CORRECTION_TYPES = ["Auto_White_Balance", "Auto_Contrast", "Custom"]


def _as_image(images):
    """Validate and return a float tensor of shape [B, H, W, C]."""
    if not isinstance(images, torch.Tensor):
        raise TypeError("images must be a torch.Tensor")
    if images.dim() != 4:
        raise ValueError("images must have shape [B, H, W, C]")
    if images.shape[-1] not in (1, 3, 4):
        raise ValueError("images must have 1, 3 or 4 channels")
    return images.float().clone()


def _as_mask(masks, batch, height, width):
    """Validate/normalise masks to [B, H, W] float in 0..1."""
    if masks is None:
        return torch.ones(batch, height, width)
    if not isinstance(masks, torch.Tensor):
        raise TypeError("masks must be a torch.Tensor or None")
    m = masks.float().clone()
    if m.dim() == 4 and m.shape[-1] == 1:
        m = m[..., 0]
    if m.dim() != 3:
        raise ValueError("masks must have shape [B, H, W] or [B, H, W, 1]")
    if m.shape[0] == 1 and batch != 1:
        m = m.expand(batch, m.shape[1], m.shape[2])
    if m.shape[0] != batch:
        raise ValueError("masks batch size must match images batch size")
    if m.shape[1] != height or m.shape[2] != width:
        raise ValueError("masks spatial size must match images spatial size")
    return m.clamp(0.0, 1.0)


def _parse_params(params_json):
    """Parse the custom-params JSON string into a dict (empty on bad input)."""
    if not params_json:
        return {}
    if not isinstance(params_json, str):
        raise TypeError("params_json must be a string")
    try:
        data = json.loads(params_json)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _auto_white_balance(img):
    """Per-channel gain that pushes the mean of each channel to the overall mean."""
    # img: [H, W, C]
    c = img.shape[-1]
    if c < 3:
        return img
    rgb = img[..., :3]
    channel_means = rgb.mean(dim=(0, 1))  # [3]
    overall = channel_means.mean()
    if overall <= 1e-8:
        return img
    gains = (overall / channel_means.clamp_min(1e-8)).clamp(0.0, 4.0)
    out = img.clone()
    out[..., :3] = rgb * gains
    return out


def _auto_contrast(img, strength=1.0):
    """Stretch each channel to [0, 1] using its own min/max, blended by strength."""
    c = img.shape[-1]
    out = img.clone()
    for ch in range(min(c, 3)):
        plane = img[..., ch]
        lo = plane.min()
        hi = plane.max()
        span = hi - lo
        if span <= 1e-8:
            continue
        stretched = (plane - lo) / span
        out[..., ch] = plane + strength * (stretched - plane)
    return out.clamp(0.0, 1.0)


def _custom(img, params):
    """Apply per-channel multipliers and offsets from parsed params."""
    out = img.clone()
    c = img.shape[-1]
    mult = params.get("multipliers")
    if isinstance(mult, (list, tuple)):
        for ch, v in enumerate(mult):
            if ch >= c:
                break
            try:
                out[..., ch] = out[..., ch] * float(v)
            except (TypeError, ValueError):
                pass
    offset = params.get("offsets")
    if isinstance(offset, (list, tuple)):
        for ch, v in enumerate(offset):
            if ch >= c:
                break
            try:
                out[..., ch] = out[..., ch] + float(v)
            except (TypeError, ValueError):
                pass
    return out


class PSN_BatchColorMod:
    """Apply a color correction to a batch of images, masked per pixel."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "correction_type": (_CORRECTION_TYPES,),
                "params_json": ("STRING", {"default": "{}"}),
            },
            "optional": {
                "masks": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, images, correction_type, params_json, masks=None):
        img = _as_image(images)
        batch, height, width, _ = img.shape
        mask = _as_mask(masks, batch, height, width)
        params = _parse_params(params_json)

        out = img.clone()
        for i in range(batch):
            corrected = img[i]
            if correction_type == "Auto_White_Balance":
                corrected = _auto_white_balance(corrected)
            elif correction_type == "Auto_Contrast":
                corrected = _auto_contrast(corrected, float(params.get("strength", 1.0)))
            elif correction_type == "Custom":
                corrected = _custom(corrected, params)
            else:
                raise ValueError("unknown correction_type: %r" % (correction_type,))
            m = mask[i].unsqueeze(-1)
            out[i] = corrected * m + img[i] * (1.0 - m)
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_BatchColorMod": PSN_BatchColorMod,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_BatchColorMod": "Batch Color Correction and Masking (ParametricStudio)",
}
