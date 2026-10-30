"""PBR Material Baking for 3D (ParametricStudio).

Bakes Albedo, Normal and Roughness maps from a 2D AI-generated image so the
result can be dropped into a 3D engine or Substance Designer.

All heavy lifting is done with plain torch on CPU.  No external models are
required: the normal map is estimated with Sobel filters on the luminance
channel and the roughness map is derived from local pixel variance.
"""

import torch

CAT = "ParametricStudio/PBR"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_image(img):
    """Validate and return a float32 CPU tensor of shape [B,H,W,C] in 0..1."""
    if not isinstance(img, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    x = img.detach().float().cpu()
    if x.dim() != 4 or x.shape[-1] < 1:
        raise ValueError("image must have shape [B,H,W,C]")
    if not torch.isfinite(x).all():
        raise ValueError("image contains NaN or Inf values")
    return x.clamp_(0.0, 1.0)


def _out(img, tensor):
    """Return a new IMAGE tensor (clipped to 0..1, contiguous)."""
    return tensor.detach().float().clamp(0.0, 1.0).contiguous()


def _srgb_to_linear(x):
    """Convert sRGB [0..1] to linear [0..1] (per-channel)."""
    return torch.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(x):
    """Convert linear [0..1] to sRGB [0..1] (per-channel)."""
    return torch.where(x <= 0.0031308, x * 12.92, 1.055 * (x ** (1.0 / 2.4)) - 0.055)


def _luminance(x):
    """Rec.709 luminance of an [B,H,W,C] tensor -> [B,H,W,1]."""
    c = x[..., :3]
    return 0.2126 * c[..., 0:1] + 0.7152 * c[..., 1:2] + 0.0722 * c[..., 2:3]


def _box_blur(x, radius):
    """Simple separable box blur on the spatial dims of [B,H,W,C]."""
    if radius < 1:
        return x
    b, h, w, c = x.shape
    # [B,H,W,C] -> [B,C,H,W]
    y = x.permute(0, 3, 1, 2)
    # build depthwise kernels: [C,1,k,1] and [C,1,1,k]
    kh = torch.ones(c, 1, 2 * radius + 1, 1, device=x.device) / (2 * radius + 1)
    kw = torch.ones(c, 1, 1, 2 * radius + 1, device=x.device) / (2 * radius + 1)
    # blur H (vertical)
    y = torch.nn.functional.conv2d(y, kh, padding=(radius, 0), groups=c)
    # blur W (horizontal)
    y = torch.nn.functional.conv2d(y, kw, padding=(0, radius), groups=c)
    # [B,C,H,W] -> [B,H,W,C]
    return y.permute(0, 2, 3, 1)


def _local_variance(x, radius):
    """Local variance of a [B,H,W,1] tensor using a box window."""
    if radius < 1:
        radius = 1
    # x is [B,H,W,1] -> squeeze last dim -> [B,H,W] -> unsqueeze -> [B,1,H,W]
    h = x.squeeze(-1).unsqueeze(1)  # [B,1,H,W]
    mean = torch.nn.functional.avg_pool2d(h, 2 * radius + 1, stride=1, padding=radius)
    mean_sq = torch.nn.functional.avg_pool2d(h * h, 2 * radius + 1, stride=1, padding=radius)
    var = (mean_sq - mean * mean).clamp(min=0.0)
    return var.squeeze(1)  # [B,H,W]


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

class PSN_PBR_Bake_Albedo:
    """Convert an image to a clean linear Albedo map (sRGB or Linear input)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "color_space": (["sRGB", "Linear"], {"default": "sRGB"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("albedo_map",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, color_space="sRGB"):
        x = _as_image(image)
        if color_space == "sRGB":
            x = _srgb_to_linear(x)
        # slight denoise: small box blur
        x = _box_blur(x, 1)
        return (_out(image, x),)


class PSN_PBR_Bake_Normal:
    """Estimate a tangent-space normal map from image luminance (Sobel)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
                "smoothness": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("normal_map",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, strength=1.0, smoothness=1.0):
        x = _as_image(image)
        lum = _luminance(x)  # [B,H,W,1]
        # smooth the height field
        blur_r = max(1, int(round(smoothness)))
        lum = _box_blur(lum, blur_r)
        # Sobel gradients on [B,H,W,1] -> treat as [B,1,H,W]
        h = lum.squeeze(-1).unsqueeze(1)  # [B,1,H,W]
        sobel_x = torch.tensor(
            [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32
        ).view(1, 1, 3, 3)
        sobel_y = sobel_x.transpose(2, 3).contiguous()
        gx = torch.nn.functional.conv2d(h, sobel_x, padding=1)  # [B,1,H,W]
        gy = torch.nn.functional.conv2d(h, sobel_y, padding=1)
        # normal = normalize(-gx*s, -gy*s, 1)
        z = torch.ones_like(gx)
        inv = 1.0 / torch.sqrt(gx * gx + gy * gy + z * z + 1e-8)
        nx = -gx * strength * inv
        ny = -gy * strength * inv
        nz = z * inv
        # map [-1,1] -> [0,1]
        nx = (nx + 1.0) * 0.5
        ny = (ny + 1.0) * 0.5
        nz = (nz + 1.0) * 0.5
        normal = torch.cat([nx, ny, nz], dim=1)  # [B,3,H,W]
        normal = normal.permute(0, 2, 3, 1)  # [B,H,W,3]
        return (_out(image, normal),)


class PSN_PBR_Bake_Roughness:
    """Generate a roughness map from local pixel variance."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "min_roughness": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0}),
                "max_roughness": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("roughness_map",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, min_roughness=0.1, max_roughness=0.9):
        x = _as_image(image)
        if min_roughness > max_roughness:
            raise ValueError("min_roughness must be <= max_roughness")
        lum = _luminance(x)  # [B,H,W,1]
        var = _local_variance(lum, radius=2)  # [B,H,W]
        # normalise variance to [0,1] per batch element
        vmax = var.amax(dim=(1, 2), keepdim=True).clamp(min=1e-8)
        t = (var / vmax).clamp(0.0, 1.0)
        rough = min_roughness + t * (max_roughness - min_roughness)
        # replicate to 3 channels
        rough = rough.unsqueeze(-1).expand(-1, -1, -1, 3)
        return (_out(image, rough),)


NODE_CLASS_MAPPINGS = {
    "PSN_PBR_Bake_Albedo": PSN_PBR_Bake_Albedo,
    "PSN_PBR_Bake_Normal": PSN_PBR_Bake_Normal,
    "PSN_PBR_Bake_Roughness": PSN_PBR_Bake_Roughness,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PBR_Bake_Albedo": "PBR Bake Albedo",
    "PSN_PBR_Bake_Normal": "PBR Bake Normal",
    "PSN_PBR_Bake_Roughness": "PBR Bake Roughness",
}
