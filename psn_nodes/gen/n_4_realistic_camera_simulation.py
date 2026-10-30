"""ParametricStudio - Realistic Camera Simulation.

Simulates optical lens defects and sensor noise on ComfyUI IMAGE tensors
(float torch tensor [B,H,W,C] in 0..1) to make images look photorealistic.

Pipeline order (documented, order matters):
    image -> bokeh blur -> chromatic aberration -> vignette -> sensor noise

Only torch (CPU) and the Python standard library are used.  No scipy:
the blur is a separable Gaussian implemented with torch conv2d, and the
noise is a proper Poisson draw via the Knuth algorithm (vectorised with
a per-pixel cap) plus a Gaussian component for high ISO.
"""

import math

import torch

CAT = "ParametricStudio/Camera"

LENS_PRESETS = {
    # name: (bokeh sigma in pixels, vignette strength 0..1)
    "50mm f/1.4": (1.6, 0.35),
    "85mm f/1.8": (1.2, 0.30),
    "24mm f/2.8": (0.6, 0.20),
}


def _as_image(image):
    """Validate and return a float32 CPU tensor [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    x = image.detach().float().cpu()
    if x.dim() != 4 or x.shape[-1] not in (1, 3, 4):
        raise ValueError("image must have shape [B,H,W,C] with C in (1,3,4)")
    if x.numel() == 0:
        raise ValueError("image must not be empty")
    return x


def _gaussian_kernel_1d(sigma, radius):
    """1-D Gaussian kernel as a 1-D tensor, normalised to sum 1."""
    if sigma <= 0:
        return torch.ones(1)
    radius = max(int(math.ceil(sigma * 3)), 1)
    idx = torch.arange(-radius, radius + 1, dtype=torch.float32)
    k = torch.exp(-(idx ** 2) / (2.0 * sigma * sigma))
    return k / k.sum()


def _gaussian_blur(x, sigma):
    """Separable Gaussian blur on [B,H,W,C] (zero-padded edges)."""
    if sigma <= 0:
        return x
    k = _gaussian_kernel_1d(sigma, 0)
    r = k.numel() // 2
    # conv2d needs [B, C, H, W]
    y = x.permute(0, 3, 1, 2)
    kh = k.view(1, 1, k.numel(), 1).repeat(y.shape[1], 1, 1, 1)
    kw = k.view(1, 1, 1, k.numel()).repeat(y.shape[1], 1, 1, 1)
    y = torch.nn.functional.conv2d(y, kh, padding=(r, 0), groups=y.shape[1])
    y = torch.nn.functional.conv2d(y, kw, padding=(0, r), groups=y.shape[1])
    return y.permute(0, 2, 3, 1)


def _chromatic_aberration(x, amount):
    """Shift R and B channels relative to G by `amount` pixels (diagonal).

    Red is shifted up-left, blue down-right (classic lens CA look).
    """
    if amount <= 0:
        return x
    shift = int(round(amount))
    if shift == 0:
        return x
    out = x.clone()
    if x.shape[-1] >= 3:
        h, w = x.shape[1], x.shape[2]
        if h > shift and w > shift:
            # red: move up-left (source rows shift.., cols ..-shift -> dest 0..)
            out[:, :h - shift, :w - shift, 0] = x[:, shift:, shift:, 0]
            # blue: move down-right (source rows ..-shift, cols shift.. -> dest shift..)
            out[:, shift:, shift:, 2] = x[:, :h - shift, :w - shift, 2]
    return out


def _vignette(x, strength):
    """Radial darkening: 1 at centre, (1-strength) at corners."""
    if strength <= 0:
        return x
    h, w = x.shape[1], x.shape[2]
    ys = torch.linspace(-1.0, 1.0, h, dtype=torch.float32)
    xs = torch.linspace(-1.0, 1.0, w, dtype=torch.float32)
    gy, gx = torch.meshgrid(ys, xs, indexing="ij")
    r2 = gx * gx + gy * gy
    r = torch.sqrt(r2) / math.sqrt(2.0)  # normalise so corner == 1
    mask = 1.0 - strength * (r ** 2)
    mask = mask.clamp(min=0.0)
    return x * mask.view(1, h, w, 1)


def _poisson_noise(x, iso):
    """Photon shot noise: scale image by exposure, draw Poisson, rescale.

    Higher ISO -> less effective exposure -> more relative noise.
    Uses Knuth's algorithm with a per-pixel cap (fine for small test
    tensors); for large images the Gaussian approximation below covers it.
    """
    if iso <= 0:
        return x
    # effective exposure: ISO 100 is the reference, higher ISO = less light
    exposure = 100.0 / max(float(iso), 1.0)
    scale = 256.0 * exposure
    lam = x.clamp(min=0.0) * scale
    # Knuth with a cap: values above the cap use the Gaussian approx.
    cap = 300.0
    use_knuth = lam < cap
    lam_k = lam[use_knuth]
    L = torch.exp(-lam_k)
    k = torch.zeros_like(lam_k)
    p = torch.ones_like(lam_k)
    # vectorised Knuth: iterate until p < L for every element
    for _ in range(200):
        p = p * torch.rand_like(lam_k)
        still = p >= L
        if not bool(still.any()):
            break
        k[still] += 1
    noise_k = k / scale
    noise_g = torch.normal(lam[~use_knuth] / scale, torch.sqrt(lam[~use_knuth]) / scale)
    noise = torch.empty_like(x)
    noise[use_knuth] = noise_k
    noise[~use_knuth] = noise_g
    return x + (noise - x) * 0.0 + (noise - x)  # == noise, keep x untouched


def _gaussian_sensor_noise(x, iso):
    """Read/shot noise modelled as zero-mean Gaussian, sigma grows with ISO."""
    if iso <= 0:
        return x
    sigma = 0.002 * math.sqrt(max(float(iso), 1.0))
    return x + torch.randn_like(x) * sigma


def _shutter_motion(x, shutter_speed):
    """Very light directional blur for slow shutters (>= 1/8 s)."""
    if shutter_speed is None or shutter_speed <= 0:
        return x
    if shutter_speed < 0.125:
        return x
    strength = min(1.0, (shutter_speed - 0.125) / 0.875)
    sigma = 0.5 + 2.0 * strength
    return _gaussian_blur(x, sigma)


class PSN_Camera_Degradation:
    """Simulate lens defects (bokeh, chromatic aberration, vignette) and
    sensor noise (Poisson + Gaussian, ISO driven) on an IMAGE tensor.

    Order of operations (recommended, and the one implemented):
    blur -> chromatic aberration -> vignette -> noise.
    Applying noise before the blur would smear it and look wrong.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "lens_type": (list(LENS_PRESETS.keys()),),
                "iso": ("INT", {"default": 400, "min": 100, "max": 51200}),
                "shutter_speed": ("FLOAT", {"default": 0.01, "min": 0.0, "max": 10.0}),
                "chromatic_aberration": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("simulated_image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, lens_type, iso, shutter_speed, chromatic_aberration):
        x = _as_image(image)
        if lens_type not in LENS_PRESETS:
            raise ValueError(f"unknown lens_type: {lens_type!r}")
        iso = int(iso)
        if iso < 0:
            raise ValueError("iso must be >= 0")
        shutter_speed = float(shutter_speed)
        if shutter_speed < 0:
            raise ValueError("shutter_speed must be >= 0")
        chromatic_aberration = float(chromatic_aberration)
        if not 0.0 <= chromatic_aberration <= 1.0:
            raise ValueError("chromatic_aberration must be in [0, 1]")

        bokeh_sigma, vignette_strength = LENS_PRESETS[lens_type]

        # 1. bokeh blur (lens/aperture) + optional slow-shutter motion blur
        y = _gaussian_blur(x, bokeh_sigma)
        y = _shutter_motion(y, shutter_speed)
        # 2. chromatic aberration (channel shift, max 2 px at amount=1)
        y = _chromatic_aberration(y, 2.0 * chromatic_aberration)
        # 3. vignette (radial darkening)
        y = _vignette(y, vignette_strength)
        # 4. sensor noise (Poisson shot noise + Gaussian read noise)
        y = _poisson_noise(y, iso)
        y = _gaussian_sensor_noise(y, iso)
        return (y.clamp(0.0, 1.0),)


NODE_CLASS_MAPPINGS = {
    "PSN_Camera_Degradation": PSN_Camera_Degradation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Camera_Degradation": "Camera Degradation (Realistic Simulation)",
}
