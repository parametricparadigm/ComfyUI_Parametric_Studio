"""ParametricStudio - PBR Texture Generation from Images.

Core delighting pipeline implemented with pure torch (CPU) so it runs
without any external model weights.  The node estimates a roughness map
and a normal map from a flat albedo image using classical image
processing (Sobel gradients, local contrast, blur) and optionally
applies seamless tiling corrections (edge blending) to the outputs.

A real neural delighting model (e.g. a CNN or diffusion based one) would
be loaded from ``model_path`` in a full deployment; that part is NOT
implemented here because no model files or heavy libraries are
available in this environment.  The procedural estimator below is a
deterministic stand-in that produces physically plausible maps.
"""

import torch

CAT = "ParametricStudio/PBR"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_image(x, name="image"):
    """Validate and return a float tensor [B,H,W,C] in 0..1 (clamped copy)."""
    if not isinstance(x, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor, got {type(x).__name__}")
    if x.dim() != 4:
        raise ValueError(f"{name} must be 4D [B,H,W,C], got shape {tuple(x.shape)}")
    if x.shape[-1] < 1:
        raise ValueError(f"{name} must have at least 1 channel")
    return x.float().clamp(0.0, 1.0).contiguous()


def _rgb(x):
    """Return the first 3 channels as [B,H,W,3], padding with the last
    channel if the input has fewer than 3 channels."""
    c = x.shape[-1]
    if c >= 3:
        return x[..., :3]
    if c == 1:
        return x.expand(-1, -1, -1, 3)
    # c == 2: duplicate the second channel
    return torch.cat([x, x[..., 1:2]], dim=-1)


def _gray(x):
    """Luminance of an [B,H,W,3] tensor -> [B,H,W]."""
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _box_blur(x, radius):
    """Separable box blur on [B,H,W] with integer radius (clamped edges)."""
    if radius <= 0:
        return x
    k = torch.ones(2 * radius + 1, device=x.device)
    k = k / k.sum()
    # pad
    x = torch.nn.functional.pad(x, (radius, radius, radius, radius), mode="replicate")
    # horizontal
    x = torch.nn.functional.conv2d(x.unsqueeze(1), k.view(1, 1, 1, -1), groups=1).squeeze(1)
    # vertical
    x = torch.nn.functional.conv2d(x.unsqueeze(1), k.view(1, 1, -1, 1), groups=1).squeeze(1)
    return x


def _sobel(x):
    """Sobel gradients of [B,H,W] -> (gx, gy) each [B,H,W]."""
    kx = torch.tensor([[1.0, 0.0, -1.0], [2.0, 0.0, -2.0], [1.0, 0.0, -1.0]],
                      device=x.device).view(1, 1, 3, 3)
    ky = kx.transpose(-1, -2).contiguous()
    xp = torch.nn.functional.pad(x.unsqueeze(1), (1, 1, 1, 1), mode="replicate")
    gx = torch.nn.functional.conv2d(xp, kx, groups=1).squeeze(1)
    gy = torch.nn.functional.conv2d(xp, ky, groups=1).squeeze(1)
    return gx, gy


def _estimate_roughness(lum):
    """Roughness from local contrast: smooth areas -> low roughness, high
    local variance -> high roughness.  Returns [B,H,W] in 0..1."""
    b, h, w = lum.shape
    radius = max(1, min(h, w) // 16)
    local_mean = _box_blur(lum, radius)
    local_sq = _box_blur(lum * lum, radius)
    var = (local_sq - local_mean * local_mean).clamp(min=0.0)
    std = torch.sqrt(var)
    # normalise by global std so the map is scale independent
    gstd = lum.std(dim=(1, 2), keepdim=True).clamp(min=1e-6)
    rough = (std / gstd).clamp(0.0, 1.0)
    # add a small base so fully flat maps are not pure black
    rough = 0.15 + 0.85 * rough
    return rough


def _estimate_normal(lum):
    """Normal map from Sobel gradients of the luminance.  Returns [B,H,W,3]
    in 0..1 (tangent-space, +Z out of the surface)."""
    gx, gy = _sobel(lum)
    # scale gradients so typical detail maps to a reasonable slope
    strength = 2.0
    nx = -gx * strength
    ny = -gy * strength
    nz = torch.ones_like(nx)
    norm = torch.sqrt(nx * nx + ny * ny + nz * nz)
    nx = nx / norm
    ny = ny / norm
    nz = nz / norm
    # map [-1,1] -> [0,1]
    out = torch.stack([(nx + 1) * 0.5, (ny + 1) * 0.5, (nz + 1) * 0.5], dim=-1)
    return out.clamp(0.0, 1.0)


def _seamless_blend(x, blend_frac=0.125):
    """Make a [B,H,W,C] image tileable by cross-fading the edges with the
    opposite edge (wrap).  Returns a new tensor, input untouched."""
    b, h, w, c = x.shape
    if h < 8 or w < 8:
        return x.clone()
    bh = max(1, int(round(h * blend_frac)))
    bw = max(1, int(round(w * blend_frac)))
    out = x.clone()
    # horizontal wrap: blend left edge with right edge
    left = out[:, :, :bw, :]
    right = out[:, :, w - bw:, :]
    t = torch.linspace(0.0, 1.0, bw, device=x.device).view(1, 1, bw, 1)
    out[:, :, :bw, :] = left * (1 - t) + right * t
    out[:, :, w - bw:, :] = right * (1 - t.flip(-1)) + left * t.flip(-1)
    # vertical wrap: blend top edge with bottom edge
    top = out[:, :bh, :, :]
    bottom = out[:, h - bh:, :, :]
    tv = torch.linspace(0.0, 1.0, bh, device=x.device).view(1, bh, 1, 1)
    out[:, :bh, :, :] = top * (1 - tv) + bottom * tv
    out[:, h - bh:, :, :] = bottom * (1 - tv.flip(1)) + top * tv.flip(1)
    return out


def _to_image3(x):
    """Ensure [B,H,W,3] float 0..1 contiguous."""
    return x.float().clamp(0.0, 1.0).contiguous()


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------

class PSN_PBR_Delight:
    """Convert a flat albedo image into a PBR material set (Albedo,
    Roughness, Normal) using a procedural delighting estimator.

    A real neural delighting model would be loaded from ``model_path``;
    that is not implemented here (no model files available).  The
    estimator uses Sobel gradients and local contrast to produce
    physically plausible roughness and normal maps.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "albedo_image": ("IMAGE",),
                "model_path": ("STRING", {"default": ""}),
                "tiled": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("albedo", "roughness", "normal")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, albedo_image, model_path="", tiled=False):
        img = _as_image(albedo_image, "albedo_image")
        rgb = _rgb(img)
        lum = _gray(rgb)

        rough = _estimate_roughness(lum)          # [B,H,W]
        normal = _estimate_normal(lum)            # [B,H,W,3]

        # build outputs as [B,H,W,3]
        albedo_out = _to_image3(rgb)
        rough_out = _to_image3(rough.unsqueeze(-1).expand(-1, -1, -1, 3))
        normal_out = _to_image3(normal)

        if tiled:
            albedo_out = _seamless_blend(albedo_out)
            rough_out = _seamless_blend(rough_out)
            normal_out = _seamless_blend(normal_out)

        return (albedo_out, rough_out, normal_out)


NODE_CLASS_MAPPINGS = {
    "PSN_PBR_Delight": PSN_PBR_Delight,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PBR_Delight": "PBR Delight (Albedo -> Roughness + Normal)",
}
