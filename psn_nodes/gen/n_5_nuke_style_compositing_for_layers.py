import torch

CAT = "ParametricStudio/Nuke"

BLEND_MODES = ("Normal", "Screen", "Multiply", "Overlay")


def _img(t):
    """Validate an IMAGE tensor: [B,H,W,C] float in 0..1."""
    if not isinstance(t, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if t.dim() != 4:
        raise ValueError("IMAGE must be [B,H,W,C], got shape %s" % (tuple(t.shape),))
    x = t.detach().float().clone()
    return x


def _mask(t):
    """Validate a MASK tensor: [B,H,W] float in 0..1."""
    if not isinstance(t, torch.Tensor):
        raise TypeError("MASK input must be a torch.Tensor")
    if t.dim() != 3:
        raise ValueError("MASK must be [B,H,W], got shape %s" % (tuple(t.shape),))
    m = t.detach().float().clone()
    return m


def _clamp01(x):
    return torch.clamp(x, 0.0, 1.0)


def _blend(base, top, mode):
    """Apply a blend mode formula element-wise. base/top are [B,H,W,C] in 0..1."""
    if mode == "Normal":
        return top
    if mode == "Screen":
        return 1.0 - (1.0 - base) * (1.0 - top)
    if mode == "Multiply":
        return base * top
    if mode == "Overlay":
        # Overlay: where base < 0.5 -> 2*base*top, else 1 - 2*(1-base)*(1-top)
        out = torch.where(
            base < 0.5,
            2.0 * base * top,
            1.0 - 2.0 * (1.0 - base) * (1.0 - top),
        )
        return out
    raise ValueError("Unknown blend mode: %r" % (mode,))


class PSN_Nuke_Composite:
    """Nuke-style compositing: blend an overlay over a base with a mask and opacity."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_image": ("IMAGE",),
                "overlay_image": ("IMAGE",),
                "mask": ("MASK",),
                "blend_mode": (BLEND_MODES,),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("composite_image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base_image, overlay_image, mask, blend_mode, opacity):
        base = _img(base_image)
        top = _img(overlay_image)
        m = _mask(mask)

        if base.shape != top.shape:
            raise ValueError(
                "base_image and overlay_image must share shape, got %s vs %s"
                % (tuple(base.shape), tuple(top.shape))
            )
        b, h, w, c = base.shape
        if m.shape[0] != b:
            raise ValueError(
                "mask batch %d does not match image batch %d" % (m.shape[0], b)
            )
        if m.shape[1] != h or m.shape[2] != w:
            raise ValueError(
                "mask spatial %s does not match image %s" % (tuple(m.shape[1:]), (h, w))
            )
        if not (0.0 <= float(opacity) <= 1.0):
            raise ValueError("opacity must be in [0,1], got %r" % (opacity,))
        if blend_mode not in BLEND_MODES:
            raise ValueError("Unknown blend mode: %r" % (blend_mode,))

        # Apply mask to overlay: mask is [B,H,W] -> [B,H,W,1]
        m4 = m.unsqueeze(-1)
        masked_top = top * m4

        # Blend base with masked overlay
        blended = _blend(base, masked_top, blend_mode)

        # Opacity: final = base * (1 - opacity) + blended * opacity
        op = float(opacity)
        out = base * (1.0 - op) + blended * op
        out = _clamp01(out)
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_Nuke_Composite": PSN_Nuke_Composite,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Nuke_Composite": "Nuke Composite (Layers)",
}
