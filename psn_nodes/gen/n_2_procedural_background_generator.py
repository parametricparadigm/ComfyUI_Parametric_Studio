"""ParametricStudio procedural background generator nodes.

CPU-only procedural pattern and optical-illusion generators built on torch.
Outputs are ComfyUI IMAGE tensors: float32 [B, H, W, C] in 0..1.
"""

import math

import torch

CAT = "ParametricStudio/Procedural"


def _clamp01(t):
    return t.clamp(0.0, 1.0)


def _to_image(t):
    """Promote a [H,W] or [H,W,C] tensor to a batched [1,H,W,C] float image in 0..1."""
    t = t.detach().float().contiguous()
    if t.dim() == 2:
        t = t.unsqueeze(-1)
    if t.dim() == 3:
        t = t.unsqueeze(0)
    if t.shape[-1] == 1:
        t = t.expand(t.shape[0], t.shape[1], t.shape[2], 3)
    return _clamp01(t)


def _validate_size(width, height):
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("width and height must be integers")
    if width < 1 or height < 1:
        raise ValueError("width and height must be >= 1")
    if width > 8192 or height > 8192:
        raise ValueError("width and height must be <= 8192")
    return width, height


def _checker(w, h, param_1, param_2, seed):
    """Checkerboard. param_1 = cell size (px), param_2 = phase offset (0..1)."""
    cell = max(1.0, float(param_1))
    phase = float(param_2)
    xs = torch.arange(w, dtype=torch.float32)
    ys = torch.arange(h, dtype=torch.float32)
    gx = (xs / cell + phase).floor()
    gy = (ys / cell + phase).floor()
    grid = (gx[None, :] + gy[:, None]).long() % 2
    return grid.float()


def _gradient(w, h, param_1, param_2, seed):
    """Linear gradient. param_1 = angle in degrees, param_2 = contrast (0..1)."""
    angle = math.radians(float(param_1))
    contrast = min(1.0, max(0.0, float(param_2)))
    xs = torch.linspace(-1.0, 1.0, w, dtype=torch.float32)
    ys = torch.linspace(-1.0, 1.0, h, dtype=torch.float32)
    gx = xs[None, :] * math.cos(angle)
    gy = ys[:, None] * math.sin(angle)
    v = (gx + gy) * 0.5 + 0.5
    v = v.clamp(0.0, 1.0)
    return v * contrast + (1.0 - contrast) * 0.5


def _halftone(w, h, param_1, param_2, seed):
    """Halftone dots. param_1 = dot spacing (px), param_2 = max dot radius fraction (0..1)."""
    spacing = max(2.0, float(param_1))
    max_frac = min(1.0, max(0.0, float(param_2)))
    xs = torch.arange(w, dtype=torch.float32)
    ys = torch.arange(h, dtype=torch.float32)
    gx, gy = torch.meshgrid(xs, ys, indexing="xy")
    cx = (gx / spacing).round() * spacing
    cy = (gy / spacing).round() * spacing
    dist = torch.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
    ramp = (gx / w + gy / h) * 0.5
    radius = spacing * 0.5 * max_frac * (0.2 + 0.8 * ramp)
    dots = (dist <= radius).float()
    return dots


def _starburst(w, h, param_1, param_2, seed):
    """Starburst rays. param_1 = number of rays, param_2 = ray width fraction (0..1)."""
    rays = max(2, int(param_1))
    width_frac = min(1.0, max(0.02, float(param_2)))
    cx, cy = w / 2.0, h / 2.0
    xs = torch.arange(w, dtype=torch.float32)
    ys = torch.arange(h, dtype=torch.float32)
    gx, gy = torch.meshgrid(xs, ys, indexing="xy")
    dx = gx - cx
    dy = gy - cy
    ang = torch.atan2(dy, dx)
    sector = (ang + math.pi) / (2.0 * math.pi) * rays
    frac = sector - sector.floor()
    on = (frac < width_frac).float()
    dist = torch.sqrt(dx * dx + dy * dy)
    maxd = math.sqrt(cx * cx + cy * cy)
    fade = (1.0 - (dist / maxd).clamp(0.0, 1.0))
    return on * fade


def _binary(w, h, param_1, param_2, seed):
    """Deterministic binary noise. param_1 = density (0..1), param_2 = scale (px)."""
    density = min(1.0, max(0.0, float(param_1)))
    scale = max(1.0, float(param_2))
    xs = torch.arange(w, dtype=torch.float32)
    ys = torch.arange(h, dtype=torch.float32)
    gx, gy = torch.meshgrid(xs, ys, indexing="xy")
    cellx = (gx / scale).floor()
    celly = (gy / scale).floor()
    hval = torch.sin(cellx * 12.9898 + celly * 78.233 + float(seed) * 0.017) * 43758.5453
    hval = hval - hval.floor()
    return (hval < density).float()


PATTERNS = {
    "checker": _checker,
    "gradient": _gradient,
    "halftone": _halftone,
    "starburst": _starburst,
    "binary": _binary,
}


class PSN_ProcGen_Patterns:
    """Generate a procedural pattern image (checker, gradient, halftone, starburst, binary)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pattern_type": (list(PATTERNS.keys()),),
                "width": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "height": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "param_1": ("FLOAT", {"default": 32.0, "min": 0.0, "max": 10000.0}),
                "param_2": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 31 - 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "metadata")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, pattern_type, width, height, param_1, param_2, seed):
        if pattern_type not in PATTERNS:
            raise ValueError(f"unknown pattern_type: {pattern_type!r}")
        width, height = _validate_size(width, height)
        fn = PATTERNS[pattern_type]
        t = fn(width, height, param_1, param_2, seed)
        img = _to_image(t)
        meta = f"pattern={pattern_type};width={width};height={height};param_1={param_1};param_2={param_2};seed={seed}"
        return (img, meta)


def _moire(w, h, intensity):
    """Two overlapping sine grids rotated slightly -> moire fringes."""
    k = min(1.0, max(0.0, float(intensity)))
    xs = torch.arange(w, dtype=torch.float32)
    ys = torch.arange(h, dtype=torch.float32)
    gx, gy = torch.meshgrid(xs, ys, indexing="xy")
    cx, cy = w / 2.0, h / 2.0
    dx = gx - cx
    dy = gy - cy
    a = 0.03
    ca, sa = math.cos(a), math.sin(a)
    dx2 = dx * ca - dy * sa
    dy2 = dx * sa + dy * ca
    f = 0.15
    s1 = torch.sin(dx * f) * torch.sin(dy * f)
    s2 = torch.sin(dx2 * f) * torch.sin(dy2 * f)
    v = (s1 * s2) * 0.5 + 0.5
    return v * k + (1.0 - k) * 0.5


def _spiral(w, h, intensity):
    """Logarithmic spiral arms in polar coordinates."""
    k = min(1.0, max(0.0, float(intensity)))
    cx, cy = w / 2.0, h / 2.0
    xs = torch.arange(w, dtype=torch.float32)
    ys = torch.arange(h, dtype=torch.float32)
    gx, gy = torch.meshgrid(xs, ys, indexing="xy")
    dx = gx - cx
    dy = gy - cy
    r = torch.sqrt(dx * dx + dy * dy)
    theta = torch.atan2(dy, dx)
    arms = 5
    v = torch.sin(arms * theta + r * 0.15)
    v = v * 0.5 + 0.5
    maxd = math.sqrt(cx * cx + cy * cy)
    fade = (1.0 - (r / maxd).clamp(0.0, 1.0))
    v = v * fade
    return v * k + (1.0 - k) * 0.5


def _grid_distortion(w, h, intensity):
    """Grid lines warped by a sine displacement."""
    k = min(1.0, max(0.0, float(intensity)))
    xs = torch.arange(w, dtype=torch.float32)
    ys = torch.arange(h, dtype=torch.float32)
    gx, gy = torch.meshgrid(xs, ys, indexing="xy")
    cell = 24.0
    amp = 6.0 * k
    wx = gx + amp * torch.sin(gy / cell * math.pi)
    wy = gy + amp * torch.sin(wx / cell * math.pi)
    lx = (wx / cell).floor()
    ly = (wy / cell).floor()
    fx = wx / cell - lx
    fy = wy / cell - ly
    line = torch.minimum(fx, 1.0 - fx)
    line = torch.minimum(line, torch.minimum(fy, 1.0 - fy))
    v = (line < 0.08).float()
    return v


ILLUSIONS = {
    "moire": _moire,
    "spiral": _spiral,
    "grid_distortion": _grid_distortion,
}


class PSN_ProcGen_OpticalIllusion:
    """Generate an optical-illusion image (moire, spiral, grid_distortion)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "illusion_type": (list(ILLUSIONS.keys()),),
                "width": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "height": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "intensity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, illusion_type, width, height, intensity):
        if illusion_type not in ILLUSIONS:
            raise ValueError(f"unknown illusion_type: {illusion_type!r}")
        width, height = _validate_size(width, height)
        t = ILLUSIONS[illusion_type](width, height, intensity)
        img = _to_image(t)
        return (img,)


NODE_CLASS_MAPPINGS = {
    "PSN_ProcGen_Patterns": PSN_ProcGen_Patterns,
    "PSN_ProcGen_OpticalIllusion": PSN_ProcGen_OpticalIllusion,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ProcGen_Patterns": "ProcGen Patterns",
    "PSN_ProcGen_OpticalIllusion": "ProcGen Optical Illusion",
}
