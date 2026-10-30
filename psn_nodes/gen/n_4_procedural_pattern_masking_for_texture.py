"""ParametricStudio: Procedural Pattern Masking for Textures.

Two pure-torch (CPU) nodes:
  * PSN_ProceduralPatternGenerator - deterministic analytic masks (perlin / voronoi / sine / fractal)
  * PSN_BooleanMaskOperation       - element-wise boolean mask logic (and / or / xor / difference)

No AI models, no network, no third-party deps beyond torch.
"""

import math

import torch

CAT = "ParametricStudio/Procedural"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_mask(t, name="mask"):
    """Validate a ComfyUI MASK tensor: float, [B,H,W], values clamped to 0..1.

    Returns a NEW tensor (never the input object).
    """
    if not isinstance(t, torch.Tensor):
        raise ValueError(f"{name} must be a torch.Tensor, got {type(t).__name__}")
    if t.dim() != 3:
        raise ValueError(f"{name} must have shape [B,H,W], got {tuple(t.shape)}")
    if t.shape[0] < 1:
        raise ValueError(f"{name} batch must be >= 1, got {t.shape[0]}")
    if t.shape[1] < 1 or t.shape[2] < 1:
        raise ValueError(f"{name} spatial dims must be >= 1, got {tuple(t.shape)}")
    return t.detach().to(torch.float32).clamp(0.0, 1.0).contiguous()


def _check_size(width, height, name="size"):
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError(f"{name} must be ints, got {type(width).__name__}/{type(height).__name__}")
    if width < 1 or height < 1:
        raise ValueError(f"{name} must be >= 1, got {width}x{height}")
    if width > 8192 or height > 8192:
        raise ValueError(f"{name} too large (max 8192), got {width}x{height}")


# ---------------------------------------------------------------------------
# procedural pattern generation (pure math, deterministic per seed)
# ---------------------------------------------------------------------------

def _hash2i(x, y, seed):
    """Deterministic integer hash of a 2D lattice point -> [0, 1)."""
    h = (x * 374761393 + y * 668265263 + seed * 974634551) & 0x7FFFFFFF
    return (h % 100000) / 100000.0


def _perlin_value_grid(width, height, scale, seed):
    """Value-noise (perlin-style) on a [0,1] grid, batch size 1."""
    # lattice spacing in grid units
    cells = max(1, int(round(scale)))
    # build a lattice of random values, then bilinear-interpolate with smoothstep
    lat_w = cells + 1
    lat_h = cells + 1
    lat = torch.empty(lat_h, lat_w, dtype=torch.float32)
    for j in range(lat_h):
        for i in range(lat_w):
            lat[j, i] = _hash2i(i, j, seed)
    # grid coordinates in lattice space
    ys = torch.linspace(0.0, float(cells), height, dtype=torch.float32)
    xs = torch.linspace(0.0, float(cells), width, dtype=torch.float32)
    gy = ys.floor().long()
    gx = xs.floor().long()
    fy = (ys - gy).clamp(0.0, 1.0)
    fx = (xs - gx).clamp(0.0, 1.0)
    # smoothstep
    sy = fy * fy * (3.0 - 2.0 * fy)  # [H]
    sx = fx * fx * (3.0 - 2.0 * fx)  # [W]
    # gather 4 corners (clamp for safety at the right/bottom edge)
    gy2 = (gy + 1).clamp(max=lat_h - 1)
    gx2 = (gx + 1).clamp(max=lat_w - 1)
    c00 = lat[gy][:, gx]  # [H, W]
    c10 = lat[gy][:, gx2]
    c01 = lat[gy2][:, gx]
    c11 = lat[gy2][:, gx2]
    top = c00 * (1.0 - sx).unsqueeze(0) + c10 * sx.unsqueeze(0)
    bot = c01 * (1.0 - sx).unsqueeze(0) + c11 * sx.unsqueeze(0)
    out = top * (1.0 - sy).unsqueeze(1) + bot * sy.unsqueeze(1)
    return out.unsqueeze(0)  # [1, H, W]


def _voronoi_grid(width, height, scale, seed):
    """Voronoi distance-to-nearest-site mask, batch size 1.

    Sites are placed on a jittered lattice; the mask is the normalized
    distance to the nearest site (0 = on a site, 1 = farthest).
    """
    cells = max(1, int(round(scale)))
    # jittered lattice sites
    n_sites = (cells + 1) * (cells + 1)
    sites = torch.empty(n_sites, 2, dtype=torch.float32)
    k = 0
    for j in range(cells + 1):
        for i in range(cells + 1):
            jx = _hash2i(i, j, seed + 101)
            jy = _hash2i(i, j, seed + 202)
            sites[k, 0] = (i + jx) / float(cells)
            sites[k, 1] = (j + jy) / float(cells)
            k += 1
    # grid in [0,1]
    ys = torch.linspace(0.0, 1.0, height, dtype=torch.float32)
    xs = torch.linspace(0.0, 1.0, width, dtype=torch.float32)
    gy, gx = torch.meshgrid(ys, xs, indexing="ij")
    # chunked distance computation to keep memory bounded
    chunk = 256
    best = torch.full((height, width), float("inf"), dtype=torch.float32)
    for s0 in range(0, n_sites, chunk):
        s = sites[s0:s0 + chunk]  # [c, 2]
        dy = gy.unsqueeze(0) - s[:, 0:1].unsqueeze(1)  # [c, H, W]
        dx = gx.unsqueeze(0) - s[:, 1:2].unsqueeze(1)
        d2 = dx * dx + dy * dy
        best = torch.minimum(best, d2.min(dim=0).values)
    d = torch.sqrt(best)
    # normalize: typical max distance ~ 0.5/sqrt(2) for unit cell
    dmax = 0.5 / math.sqrt(2.0)
    out = (d / dmax).clamp(0.0, 1.0)
    return out.unsqueeze(0)


def _sine_grid(width, height, scale, seed):
    """Interference of two sine waves -> banding pattern, batch size 1."""
    ys = torch.linspace(0.0, 1.0, height, dtype=torch.float32)
    xs = torch.linspace(0.0, 1.0, width, dtype=torch.float32)
    gy, gx = torch.meshgrid(ys, xs, indexing="ij")
    f = max(0.1, float(scale))
    phase = (seed % 628) / 100.0
    a = torch.sin(2.0 * math.pi * f * gx + phase)
    b = torch.sin(2.0 * math.pi * f * gy + phase * 1.7)
    out = (0.5 + 0.5 * (a * b)).clamp(0.0, 1.0)
    return out.unsqueeze(0)


def _fractal_grid(width, height, scale, seed):
    """Multi-octave value noise (fBm), batch size 1."""
    out = torch.zeros(1, height, width, dtype=torch.float32)
    amp = 1.0
    total = 0.0
    octaves = 4
    for o in range(octaves):
        s = max(1.0, float(scale) * (2.0 ** o))
        out = out + amp * _perlin_value_grid(width, height, s, seed + 7 * (o + 1))
        total += amp
        amp *= 0.5
    out = (out / total).clamp(0.0, 1.0)
    return out


_PATTERNS = {
    "perlin": _perlin_value_grid,
    "voronoi": _voronoi_grid,
    "sine": _sine_grid,
    "fractal": _fractal_grid,
}


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

class PSN_ProceduralPatternGenerator:
    """Generate a deterministic procedural mask (perlin / voronoi / sine / fractal)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 256, "min": 1, "max": 8192}),
                "height": ("INT", {"default": 256, "min": 1, "max": 8192}),
                "pattern_type": (["perlin", "voronoi", "sine", "fractal"],),
                "scale": ("FLOAT", {"default": 4.0, "min": 0.1, "max": 256.0, "step": 0.1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 31 - 1}),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, width, height, pattern_type, scale, seed):
        _check_size(width, height)
        if pattern_type not in _PATTERNS:
            raise ValueError(f"unknown pattern_type {pattern_type!r}")
        if not isinstance(scale, (int, float)) or scale <= 0:
            raise ValueError(f"scale must be a positive number, got {scale!r}")
        if not isinstance(seed, int) or seed < 0:
            raise ValueError(f"seed must be a non-negative int, got {seed!r}")
        gen = _PATTERNS[pattern_type]
        mask = gen(int(width), int(height), float(scale), int(seed))
        return (mask,)


class PSN_BooleanMaskOperation:
    """Combine two masks with boolean logic (and / or / xor / difference)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask_a": ("MASK",),
                "mask_b": ("MASK",),
                "operation": (["and", "or", "xor", "difference"],),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("result_mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mask_a, mask_b, operation):
        a = _as_mask(mask_a, "mask_a")
        b = _as_mask(mask_b, "mask_b")
        if a.shape != b.shape:
            raise ValueError(f"mask shapes must match, got {tuple(a.shape)} vs {tuple(b.shape)}")
        if operation == "and":
            out = torch.minimum(a, b)
        elif operation == "or":
            out = torch.maximum(a, b)
        elif operation == "xor":
            out = torch.abs(a - b)
        elif operation == "difference":
            out = (a - b).clamp(0.0, 1.0)
        else:
            raise ValueError(f"unknown operation {operation!r}")
        return (out.contiguous(),)


NODE_CLASS_MAPPINGS = {
    "PSN_ProceduralPatternGenerator": PSN_ProceduralPatternGenerator,
    "PSN_BooleanMaskOperation": PSN_BooleanMaskOperation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ProceduralPatternGenerator": "Procedural Pattern Generator (Mask)",
    "PSN_BooleanMaskOperation": "Boolean Mask Operation",
}
