"""ParametricStudio: LAB-space product recoloring node.

Converts an IMAGE (float tensor [B,H,W,C] in 0..1) to CIE-LAB, shifts the
L/A/B channels toward target values, and converts back to RGB.  An optional
MASK ([B,H,W]) restricts the recoloring to a region; unmasked pixels are
left untouched.  All math is done with torch on CPU; inputs are never
modified in place.
"""

import torch

CAT = "ParametricStudio/Color"

# ---------------------------------------------------------------------------
# sRGB <-> linear <-> XYZ <-> LAB helpers (pure torch, CPU)
# ---------------------------------------------------------------------------

# D65 reference white (XYZ)
_XYZ_W = torch.tensor([0.95047, 1.0, 1.08883], dtype=torch.float32)


def _srgb_to_linear(rgb: torch.Tensor) -> torch.Tensor:
    """rgb: [..., 3] in 0..1 sRGB -> linear-light RGB."""
    low = rgb / 12.92
    high = torch.pow((rgb + 0.055) / 1.055, 2.4)
    return torch.where(rgb <= 0.04045, low, high)


def _linear_to_srgb(rgb: torch.Tensor) -> torch.Tensor:
    """linear-light RGB -> sRGB 0..1 (clamped)."""
    rgb = rgb.clamp(min=0.0)
    low = rgb * 12.92
    high = 1.055 * torch.pow(rgb.clamp(min=1e-12), torch.tensor(1.0 / 2.4, dtype=rgb.dtype)) - 0.055
    return torch.where(rgb <= 0.0031308, low, high).clamp(0.0, 1.0)


def _rgb_to_xyz(rgb: torch.Tensor) -> torch.Tensor:
    """rgb: [..., 3] linear sRGB -> XYZ (D65)."""
    m = torch.tensor([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ], dtype=rgb.dtype, device=rgb.device)
    return rgb @ m.t()


def _xyz_to_rgb(xyz: torch.Tensor) -> torch.Tensor:
    """XYZ (D65) -> linear sRGB [..., 3]."""
    m = torch.tensor([
        [ 3.2404542, -1.5371385, -0.4985314],
        [-0.9692660,  1.8760108,  0.0415560],
        [ 0.0556434, -0.2040259,  1.0572252],
    ], dtype=xyz.dtype, device=xyz.device)
    return xyz @ m.t()


def _f_inv(t: torch.Tensor) -> torch.Tensor:
    """Inverse of the LAB f() piecewise function."""
    delta = torch.tensor(6.0 / 29.0, dtype=t.dtype, device=t.device)
    delta3 = delta ** 3
    return torch.where(t > delta, t ** 3, 3.0 * delta ** 2 * (t - 4.0 / 29.0))


def _rgb_to_lab(rgb: torch.Tensor) -> torch.Tensor:
    """rgb: [..., 3] sRGB 0..1 -> LAB [..., 3] (L in 0..100, A/B roughly -128..127)."""
    lin = _srgb_to_linear(rgb)
    xyz = _rgb_to_xyz(lin)
    xyz_n = xyz / _XYZ_W.to(xyz.device)
    delta = torch.tensor(6.0 / 29.0, dtype=xyz_n.dtype, device=xyz_n.device)
    delta3 = delta ** 3
    f = torch.where(xyz_n > delta3, torch.pow(xyz_n.clamp(min=1e-12), torch.tensor(1.0 / 3.0, dtype=xyz_n.dtype)),
                    (xyz_n / (3.0 * delta ** 2) + 4.0 / 29.0))
    L = 116.0 * f[..., 1:2] - 16.0
    A = 500.0 * (f[..., 0:1] - f[..., 1:2])
    B = 200.0 * (f[..., 1:2] - f[..., 2:3])
    return torch.cat([L, A, B], dim=-1)


def _lab_to_rgb(lab: torch.Tensor) -> torch.Tensor:
    """LAB [..., 3] -> sRGB 0..1 [..., 3] (clamped)."""
    L = lab[..., 0:1]
    A = lab[..., 1:2]
    B = lab[..., 2:3]
    fy = (L + 16.0) / 116.0
    fx = fy + A / 500.0
    fz = fy - B / 200.0
    xyz_n = torch.cat([_f_inv(fx), _f_inv(fy), _f_inv(fz)], dim=-1)
    xyz = xyz_n * _XYZ_W.to(xyz_n.device)
    lin = _xyz_to_rgb(xyz)
    return _linear_to_srgb(lin)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_LAB_Recolor:
    """Recolor an image in CIE-LAB space toward target L/A/B values.

    The shift is applied as a weighted blend: each LAB channel moves toward
    its target by `strength` (0..1).  An optional MASK limits the effect to
    masked pixels (mask > 0.5).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "target_L": ("FLOAT", {"default": 50.0, "min": 0.0, "max": 100.0}),
                "target_A": ("FLOAT", {"default": 0.0, "min": -128.0, "max": 128.0}),
                "target_B": ("FLOAT", {"default": 0.0, "min": -128.0, "max": 128.0}),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0}),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, target_L, target_A, target_B, strength, mask=None):
        if not isinstance(image, torch.Tensor):
            raise TypeError("image must be a torch.Tensor")
        if image.dim() != 4 or image.shape[-1] != 3:
            raise ValueError("image must have shape [B,H,W,3]")
        if mask is not None and not isinstance(mask, torch.Tensor):
            raise TypeError("mask must be a torch.Tensor or None")
        if mask is not None and mask.dim() != 3:
            raise ValueError("mask must have shape [B,H,W]")

        img = image.detach().clone().float().clamp(0.0, 1.0)
        lab = _rgb_to_lab(img)

        targets = torch.tensor([target_L, target_A, target_B], dtype=lab.dtype, device=lab.device)
        shifted = lab + (targets - lab) * float(strength)

        out = _lab_to_rgb(shifted)

        if mask is not None:
            m = mask.detach().clone().float().clamp(0.0, 1.0)
            if m.shape[0] == 1 and img.shape[0] > 1:
                m = m.expand(img.shape[0], -1, -1)
            m = m.unsqueeze(-1)  # [B,H,W,1]
            out = m * out + (1.0 - m) * img

        return (out.clamp(0.0, 1.0),)


NODE_CLASS_MAPPINGS = {
    "PSN_LAB_Recolor": PSN_LAB_Recolor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LAB_Recolor": "LAB Space Recolor (ParametricStudio)",
}
