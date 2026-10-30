"""ParametricStudio - Photoshop-style compositing layers.

PSN_LayerComposite: composites a top image over a base image using a
standard blend mode (Normal, Multiply, Screen, Overlay, Soft_Light,
Hard_Light) with optional per-pixel mask and opacity.

All math is done in torch on CPU/GPU tensors. Inputs are never modified
in place.
"""

import torch

CAT = "ParametricStudio/Compositing"

BLEND_MODES = ["Normal", "Multiply", "Screen", "Overlay", "Soft_Light", "Hard_Light"]


def _as_tensor(x):
    if isinstance(x, torch.Tensor):
        return x
    raise TypeError("expected a torch.Tensor")


def _clamp01(t):
    return torch.clamp(t, 0.0, 1.0)


def _blend(b, t, mode):
    """Blend top `t` over base `b` per channel. Both in [0,1]."""
    if mode == "Normal":
        return t
    if mode == "Multiply":
        return b * t
    if mode == "Screen":
        return 1.0 - (1.0 - b) * (1.0 - t)
    if mode == "Overlay":
        # base < 0.5 -> 2*b*t else 1 - 2*(1-b)*(1-t)
        return torch.where(b < 0.5, 2.0 * b * t, 1.0 - 2.0 * (1.0 - b) * (1.0 - t))
    if mode == "Soft_Light":
        # Standard soft light: if t < 0.5: b - (1 - 2t)*b*(1-b) else b + (2t-1)*(b' - b)
        # where b' = 2b if b <= 0.25 else sqrt(b)
        b2 = torch.where(b <= 0.25, 2.0 * b, torch.sqrt(b))
        low = b - (1.0 - 2.0 * t) * b * (1.0 - b)
        high = b + (2.0 * t - 1.0) * (b2 - b)
        return torch.where(t < 0.5, low, high)
    if mode == "Hard_Light":
        # top acts as light: if t < 0.5 -> 2*b*t else 1 - 2*(1-b)*(1-t)
        return torch.where(t < 0.5, 2.0 * b * t, 1.0 - 2.0 * (1.0 - b) * (1.0 - t))
    raise ValueError(f"unknown blend mode: {mode!r}")


class PSN_LayerComposite:
    """Composite a top image over a base image with a blend mode, mask and opacity."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_image": ("IMAGE",),
                "top_image": ("IMAGE",),
                "blend_mode": (BLEND_MODES,),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base_image, top_image, blend_mode, opacity, mask=None):
        b = _as_tensor(base_image).float()
        t = _as_tensor(top_image).float()
        if b.dim() != 4 or t.dim() != 4:
            raise ValueError("images must be [B,H,W,C]")
        if b.shape != t.shape:
            raise ValueError(f"shape mismatch: base {tuple(b.shape)} vs top {tuple(t.shape)}")
        if not (0.0 <= float(opacity) <= 1.0):
            raise ValueError("opacity must be in [0,1]")
        if blend_mode not in BLEND_MODES:
            raise ValueError(f"unknown blend mode: {blend_mode!r}")

        b = _clamp01(b)
        t = _clamp01(t)

        blended = _blend(b, t, blend_mode)

        # Apply mask (per-pixel alpha for the top layer) if provided.
        if mask is not None:
            m = _as_tensor(mask).float()
            if m.dim() == 4 and m.shape[-1] == 1:
                m = m[..., 0]
            if m.dim() != 3:
                raise ValueError("mask must be [B,H,W] or [B,H,W,1]")
            if m.shape[0] != b.shape[0] or m.shape[1] != b.shape[1] or m.shape[2] != b.shape[2]:
                raise ValueError(f"mask shape {tuple(m.shape)} incompatible with image {tuple(b.shape)}")
            m = _clamp01(m)
            # alpha = mask * opacity
            alpha = m * float(opacity)
            # expand to [B,H,W,1]
            alpha = alpha.unsqueeze(-1)
            out = b * (1.0 - alpha) + blended * alpha
        else:
            out = b * (1.0 - float(opacity)) + blended * float(opacity)

        return (_clamp01(out),)


NODE_CLASS_MAPPINGS = {
    "PSN_LayerComposite": PSN_LayerComposite,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LayerComposite": "Layer Composite (Blend Mode)",
}
