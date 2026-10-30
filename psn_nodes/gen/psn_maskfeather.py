"""PSN_MaskFeather: pure-logic Gaussian feathering of mask edges.

This module implements the *pure-logic, secure-by-design* part of a mask
feathering node. It does NOT import torch, cv2, comfy, or any GPU/network
library. Instead it operates on plain Python lists of numbers (a 2-D mask
represented as a list of rows, each row a list of floats in [0, 1]) and
applies a separable Gaussian blur to soften the edges.

The node wrapper (PSN_MaskFeather) accepts plain values (a JSON text string
encoding the mask, or a nested list) and returns the feathered mask as a
nested list plus a JSON text representation, so it can be wired into a
ComfyUI graph without requiring torch/cv2 at import time.

Only the Python standard library is used.
"""

import json
import math

CAT = "ParametricStudio/Mask"

# ---------------------------------------------------------------------------
# Gaussian kernel helpers
# ---------------------------------------------------------------------------

def _psn_gaussian_kernel(radius, sigma):
    """Return a 1-D Gaussian kernel of length (2*radius+1) centered at radius.

    The kernel is normalized so its elements sum to 1.0.
    """
    if radius < 0:
        raise ValueError("radius must be >= 0")
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    size = 2 * radius + 1
    kernel = []
    for i in range(size):
        x = i - radius
        kernel.append(math.exp(-(x * x) / (2.0 * sigma * sigma)))
    total = sum(kernel)
    if total == 0.0:
        # Degenerate: return a flat kernel
        flat = 1.0 / size
        return [flat] * size
    return [v / total for v in kernel]


def _psn_convolve_row(row, kernel):
    """Convolve a single row (list of floats) with a 1-D kernel, edge-clamped."""
    n = len(row)
    k = len(kernel)
    half = k // 2
    out = []
    for i in range(n):
        acc = 0.0
        for j in range(k):
            src = i + (j - half)
            if src < 0:
                src = 0
            elif src >= n:
                src = n - 1
            acc += row[src] * kernel[j]
        out.append(acc)
    return out


def _psn_convolve_column(grid, kernel):
    """Convolve each column of a 2-D grid with a 1-D kernel, edge-clamped."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    k = len(kernel)
    half = k // 2
    out = [[0.0] * cols for _ in range(rows)]
    for c in range(cols):
        col = [grid[r][c] for r in range(rows)]
        conv = _psn_convolve_row(col, kernel)
        for r in range(rows):
            out[r][c] = conv[r]
    return out


def psn_feather_mask(mask, feather_radius, sigma=None):
    """Apply a separable Gaussian blur to a 2-D mask.

    Args:
        mask: list of rows, each a list of floats in [0, 1].
        feather_radius: integer radius (>= 0) for the Gaussian kernel.
        sigma: optional sigma; defaults to feather_radius / 2.0 (or 0.5 if radius is 0).

    Returns:
        A new 2-D list of floats, values clamped to [0, 1].
    """
    if not isinstance(mask, list) or len(mask) == 0:
        raise ValueError("mask must be a non-empty list of rows")
    rows = len(mask)
    cols = len(mask[0])
    if cols == 0:
        raise ValueError("mask rows must be non-empty")
    for r in range(rows):
        if len(mask[r]) != cols:
            raise ValueError("mask rows must all have the same length")

    radius = int(feather_radius)
    if radius < 0:
        raise ValueError("feather_radius must be >= 0")

    if sigma is None:
        sigma = radius / 2.0 if radius > 0 else 0.5
    if sigma <= 0:
        sigma = 0.5

    kernel = _psn_gaussian_kernel(radius, sigma)

    # Horizontal pass
    horizontal = [_psn_convolve_row(row, kernel) for row in mask]
    # Vertical pass
    result = _psn_convolve_column(horizontal, kernel)

    # Clamp to [0, 1]
    clamped = []
    for row in result:
        clamped.append([max(0.0, min(1.0, v)) for v in row])
    return clamped


def _psn_mask_to_json(mask):
    return json.dumps(mask)


def _psn_mask_from_input(mask_input):
    """Accept a nested list or a JSON text string; return a nested list of floats."""
    if isinstance(mask_input, str):
        data = json.loads(mask_input)
    else:
        data = mask_input
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("mask must be a non-empty list of rows")
    rows = []
    for row in data:
        if not isinstance(row, list):
            raise ValueError("each mask row must be a list")
        rows.append([float(v) for v in row])
    return rows


# ---------------------------------------------------------------------------
# ComfyUI-style node wrapper
# ---------------------------------------------------------------------------

class PSN_MaskFeather:
    """Feathers mask edges with a Gaussian blur for smooth compositing.

    Pure-logic implementation: operates on plain Python lists / JSON text.
    No torch, cv2, or GPU required.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("STRING", {"default": "[]", "multiline": True}),
                "feather_radius": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 256.0, "step": 0.5}),
            },
            "optional": {
                "sigma": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 256.0, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("feathered_mask_json", "feathered_mask_preview")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mask, feather_radius, sigma=0.0):
        grid = _psn_mask_from_input(mask)
        effective_sigma = sigma if sigma > 0 else None
        feathered = psn_feather_mask(grid, feather_radius, sigma=effective_sigma)
        feathered_json = _psn_mask_to_json(feathered)
        # A small text preview: dimensions and a few sample values
        rows = len(feathered)
        cols = len(feathered[0]) if rows else 0
        preview = "mask %dx%d feathered" % (rows, cols)
        if rows > 0 and cols > 0:
            preview += " center=%.4f" % feathered[rows // 2][cols // 2]
        return (feathered_json, preview)


NODE_CLASS_MAPPINGS = {"PSN_MaskFeather": PSN_MaskFeather}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_MaskFeather": "PSN Mask Feather"}
