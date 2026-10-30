"""ParametricStudio - Image Quality Metrics for QA.

Computes full-reference image quality metrics (SSIM, PSNR, and a lightweight
perceptual proxy labelled DISTS) between an image and a reference image.

Implemented with pure torch (CPU) so no third-party metric libraries are
required.  The DISTS entry is a *proxy* perceptual score (multi-scale
gradient + luminance energy) because the real DISTS model (a trained CNN)
cannot be bundled here.
"""

import torch

CAT = "ParametricStudio/Quality"

_EPS = 1e-8


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_image_tensor(x, name="image"):
    """Validate and return a float32 CPU tensor of shape [B,H,W,C] in 0..1."""
    if not isinstance(x, torch.Tensor):
        raise ValueError(f"{name} must be a torch.Tensor, got {type(x).__name__}")
    t = x.detach().to(dtype=torch.float32, device="cpu")
    if t.dim() != 4:
        raise ValueError(f"{name} must have shape [B,H,W,C], got {tuple(t.shape)}")
    if t.shape[-1] not in (1, 3, 4):
        raise ValueError(f"{name} last dim must be 1/3/4 channels, got {t.shape[-1]}")
    if t.shape[1] < 1 or t.shape[2] < 1:
        raise ValueError(f"{name} spatial dims must be >= 1, got {tuple(t.shape)}")
    return t


def _match_size(img, ref):
    """Resize `ref` to the spatial size of `img` (and channel count) if needed.

    Returns (img, ref) as new tensors; inputs are never modified.
    """
    if img.shape[1] != ref.shape[1] or img.shape[2] != ref.shape[2]:
        ref = torch.nn.functional.interpolate(
            ref.permute(0, 3, 1, 2),
            size=(img.shape[1], img.shape[2]),
            mode="bilinear",
            align_corners=False,
        ).permute(0, 2, 3, 1)
    if img.shape[0] != ref.shape[0]:
        # broadcast the smaller batch to the larger one
        n = max(img.shape[0], ref.shape[0])
        if img.shape[0] == 1 and n > 1:
            img = img.repeat(n, 1, 1, 1)
        if ref.shape[0] == 1 and n > 1:
            ref = ref.repeat(n, 1, 1, 1)
    if img.shape[3] != ref.shape[3]:
        # align channel counts by taking the first min channels of each
        c = min(img.shape[3], ref.shape[3])
        img = img[..., :c]
        ref = ref[..., :c]
    return img, ref


def _gaussian_kernel2d(size, sigma, device):
    """Symmetric 2-D Gaussian kernel normalised to sum to 1."""
    coords = torch.arange(size, dtype=torch.float32, device=device) - (size - 1) / 2.0
    g = torch.exp(-(coords ** 2) / (2.0 * sigma * sigma))
    k = torch.outer(g, g)
    return k / k.sum()


def _ssim_map(img, ref, win_size=11, sigma=1.5):
    """Return per-pixel SSIM map [B,H,W] (averaged over channels)."""
    c = img.shape[3]
    x = img.permute(0, 3, 1, 2)  # [B,C,H,W]
    y = ref.permute(0, 3, 1, 2)
    kernel = _gaussian_kernel2d(win_size, sigma, device=x.device)
    pad = win_size // 2
    # conv2d groups=C so each channel is filtered independently
    k = kernel.view(1, 1, win_size, win_size).expand(c, 1, win_size, win_size)
    mu_x = torch.nn.functional.conv2d(x, k, padding=pad, groups=c)
    mu_y = torch.nn.functional.conv2d(y, k, padding=pad, groups=c)
    mu_x2 = mu_x * mu_x
    mu_y2 = mu_y * mu_y
    mu_xy = mu_x * mu_y
    sigma_x2 = torch.nn.functional.conv2d(x * x, k, padding=pad, groups=c) - mu_x2
    sigma_y2 = torch.nn.functional.conv2d(y * y, k, padding=pad, groups=c) - mu_y2
    sigma_xy = torch.nn.functional.conv2d(x * y, k, padding=pad, groups=c) - mu_xy
    c1 = (0.01 * 1.0) ** 2
    c2 = (0.03 * 1.0) ** 2
    num = (2.0 * mu_xy + c1) * (2.0 * sigma_xy + c2)
    den = (mu_x2 + mu_y2 + c1) * (sigma_x2 + sigma_y2 + c2)
    ssim = num / (den + _EPS)
    return ssim.mean(dim=1)  # [B,H,W]


def _psnr(img, ref, max_val=1.0):
    """PSNR in dB; returns float('inf') when images are identical."""
    mse = torch.mean((img - ref) ** 2).item()
    if mse <= _EPS:
        return float("inf")
    return float(10.0 * torch.log10(torch.tensor(max_val ** 2) / torch.tensor(mse)).item())


def _dists_proxy(img, ref):
    """Lightweight perceptual proxy (NOT the real DISTS model).

    Combines a multi-scale gradient-energy difference with a luminance-energy
    difference.  Lower is better; 0.0 means identical images.
    """
    x = img.permute(0, 3, 1, 2)
    y = ref.permute(0, 3, 1, 2)
    total = 0.0
    n_scales = 0
    xs, ys = x, y
    for _ in range(3):
        # gradient energy (Sobel-like via simple differences)
        gx = xs[:, :, 1:, :] - xs[:, :, :-1, :]
        gy = xs[:, :, :, 1:] - xs[:, :, :, :-1]
        gyx = ys[:, :, 1:, :] - ys[:, :, :-1, :]
        gyy = ys[:, :, :, 1:] - ys[:, :, :, :-1]
        grad_diff = torch.mean((gx - gyx) ** 2) + torch.mean((gy - gyy) ** 2)
        # luminance energy difference
        lum_diff = torch.mean((xs - ys) ** 2)
        total += grad_diff.item() + lum_diff.item()
        n_scales += 1
        # downsample by 2
        if xs.shape[2] > 2 and xs.shape[3] > 2:
            xs = torch.nn.functional.interpolate(xs, scale_factor=0.5, mode="area")
            ys = torch.nn.functional.interpolate(ys, scale_factor=0.5, mode="area")
        else:
            break
    return float(total / max(n_scales, 1))


def _error_map(img, ref):
    """Return a [B,H,W,3] float tensor in 0..1 visualising per-pixel error."""
    diff = torch.abs(img - ref)
    # normalise to 0..1 across the whole tensor
    dmax = diff.max().item()
    if dmax <= _EPS:
        return torch.zeros_like(diff[..., :1]).expand(-1, -1, -1, 3)
    normed = diff / dmax
    # grayscale -> 3 channel
    if normed.shape[3] == 1:
        normed = normed.expand(-1, -1, -1, 3)
    else:
        normed = normed.mean(dim=3, keepdim=True).expand(-1, -1, -1, 3)
    return normed


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------

class PSN_Quality_Metrics:
    """Compute a full-reference image quality metric (SSIM / PSNR / DISTS-proxy)
    between `image` and `reference`, returning a scalar score and an optional
    visual error map."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "reference": ("IMAGE",),
                "metrics": ("SSIM", "PSNR", "DISTS"),
            },
            "optional": {
                "return_map": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("FLOAT", "IMAGE")
    RETURN_NAMES = ("score", "map")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, reference, metrics, return_map=True):
        img = _as_image_tensor(image, "image")
        ref = _as_image_tensor(reference, "reference")
        img, ref = _match_size(img, ref)

        if metrics == "SSIM":
            smap = _ssim_map(img, ref)
            score = float(smap.mean().item())
        elif metrics == "PSNR":
            score = _psnr(img, ref)
            smap = None
        elif metrics == "DISTS":
            score = _dists_proxy(img, ref)
            smap = None
        else:
            raise ValueError(f"unknown metric: {metrics!r}")

        if return_map:
            emap = _error_map(img, ref)
        else:
            emap = torch.zeros(1, 1, 1, 3, dtype=torch.float32)

        return (score, emap)


NODE_CLASS_MAPPINGS = {
    "PSN_Quality_Metrics": PSN_Quality_Metrics,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Quality_Metrics": "Quality Metrics (QA)",
}
