"""Context-aware tile refinement planning (pure-logic, secure-by-design).

This module implements the *planning* half of a context-aware tile
refinement pipeline.  The real node would split an already-upscaled image
into overlapping tiles, refine each tile with a diffusion model using
context from the overlapping regions, and composite the result.  That
requires torch / ComfyUI internals and GPU access, which are out of scope
here.

Instead we expose the pure, deterministic logic that such a node needs:

* tiling geometry (grid of tiles with a configurable overlap),
* per-tile context windows (the overlapping halo used for seamless
  blending),
* a feathered blend weight map (cosine ramp) used to composite tiles,
* seam-continuity checks (pixel continuity across tile boundaries),
* and a small allow-list / validation layer for the tile parameters.

All functions take plain values (ints, floats, strings, JSON text) and
return plain values.  No sockets, no file/OS access, no network, no
torch, no ComfyUI imports.
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/TileRefine"

# Allowed blend profiles for the feathered composite.
BLEND_MODES = ("cosine", "linear", "none")

# Hard safety bounds so a bad INT cannot produce a pathological grid.
_MIN_TILE = 8
_MAX_TILE = 4096
_MIN_OVERLAP = 0
_MAX_OVERLAP = 2048


def _clamp_int(value, lo, hi):
    """Coerce *value* to an int and clamp into [lo, hi]."""
    try:
        iv = int(value)
    except (TypeError, ValueError):
        iv = lo
    if iv < lo:
        iv = lo
    if iv > hi:
        iv = hi
    return iv


def _validate_tile_params(width, height, tile_size, overlap):
    """Validate and normalise tiling parameters.

    Returns a dict with normalised ints and a list of human-readable
    warnings.  Raises ValueError only for structurally impossible input
    (non-positive image dimensions).
    """
    warnings = []
    try:
        w = int(width)
        h = int(height)
    except (TypeError, ValueError):
        raise ValueError("width and height must be integers")
    if w <= 0 or h <= 0:
        raise ValueError("width and height must be positive")

    ts = _clamp_int(tile_size, _MIN_TILE, _MAX_TILE)
    ov = _clamp_int(overlap, _MIN_OVERLAP, _MAX_OVERLAP)

    if ov >= ts:
        warnings.append("overlap >= tile_size; clamped overlap to tile_size-1")
        ov = ts - 1
    if ov > 0 and ov % 2 != 0:
        warnings.append("odd overlap; using symmetric feathering")

    return {"width": w, "height": h, "tile_size": ts, "overlap": ov,
            "warnings": warnings}


def compute_tile_grid(width, height, tile_size, overlap):
    """Compute the grid of tile rectangles.

    Returns a list of dicts, each with keys ``x``, ``y``, ``w``, ``h``
    (the tile's position and size in the *output* image space).  Tiles are
    laid out so that consecutive tiles overlap by ``overlap`` pixels and
    the last tile in each axis is clamped so it does not extend past the
    image edge.
    """
    p = _validate_tile_params(width, height, tile_size, overlap)
    w, h, ts, ov = p["width"], p["height"], p["tile_size"], p["overlap"]
    step = ts - ov
    if step <= 0:
        step = 1

    tiles = []
    y = 0
    while y < h:
        x = 0
        while x < w:
            tw = min(ts, w - x)
            th = min(ts, h - y)
            tiles.append({"x": x, "y": y, "w": tw, "h": th})
            if x + ts >= w:
                break
            x += step
        if y + ts >= h:
            break
        y += step
    return tiles


def compute_context_window(tile, width, height, overlap):
    """Compute the context (halo) window around a tile.

    The context window extends ``overlap`` pixels beyond the tile on each
    side, clamped to the image bounds.  This is the region the model sees
    in addition to the tile itself so that edges blend seamlessly.
    """
    pad = max(0, int(overlap))
    x0 = max(0, tile["x"] - pad)
    y0 = max(0, tile["y"] - pad)
    x1 = min(width, tile["x"] + tile["w"] + pad)
    y1 = min(height, tile["y"] + tile["h"] + pad)
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def blend_weight(u, v, mode="cosine"):
    """Return the feathered blend weight in [0, 1] for local coords (u, v).

    ``u`` and ``v`` are normalised to [0, 1] within the tile.  The weight
    ramps from 0 at the edges to 1 in the centre, so overlapping tiles
    blend smoothly.  ``mode`` selects the ramp profile.
    """
    if mode not in BLEND_MODES:
        mode = "cosine"
    if mode == "none":
        return 1.0
    # Distance from the nearest edge, in [0, 0.5].
    du = min(u, 1.0 - u)
    dv = min(v, 1.0 - v)
    d = min(du, dv)
    if mode == "linear":
        return max(0.0, min(1.0, d * 2.0))
    # cosine: smoothstep-like ramp
    t = max(0.0, min(1.0, d * 2.0))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def check_seam_continuity(left_pixels, right_pixels, tolerance=1e-3):
    """Check pixel continuity across a vertical seam.

    ``left_pixels`` and ``right_pixels`` are sequences of numeric values
    (e.g. a column of pixel intensities) of equal length.  Returns a dict
    with ``continuous`` (bool), ``max_diff`` (float) and ``mean_diff``
    (float).  Mismatched lengths are treated as a discontinuity.
    """
    if len(left_pixels) != len(right_pixels):
        return {"continuous": False, "max_diff": float("inf"),
                "mean_diff": float("inf"),
                "reason": "length mismatch"}
    if not left_pixels:
        return {"continuous": True, "max_diff": 0.0, "mean_diff": 0.0,
                "reason": "empty"}
    diffs = [abs(a - b) for a, b in zip(left_pixels, right_pixels)]
    max_diff = max(diffs)
    mean_diff = sum(diffs) / len(diffs)
    return {"continuous": max_diff <= tolerance, "max_diff": max_diff,
            "mean_diff": mean_diff, "reason": "ok"}


def plan_refinement(width, height, tile_size, overlap, blend_mode="cosine"):
    """Produce a full refinement plan for an image.

    Returns a dict with the normalised parameters, the tile grid, and for
    each tile its context window.  This is the pure-logic output a real
    node would consume to drive the GPU refinement.
    """
    p = _validate_tile_params(width, height, tile_size, overlap)
    if blend_mode not in BLEND_MODES:
        p["warnings"].append("unknown blend_mode; using cosine")
        blend_mode = "cosine"
    tiles = compute_tile_grid(p["width"], p["height"], p["tile_size"],
                              p["overlap"])
    for t in tiles:
        t["context"] = compute_context_window(t, p["width"], p["height"],
                                              p["overlap"])
    return {"params": p, "blend_mode": blend_mode, "tiles": tiles,
            "tile_count": len(tiles)}


class PSN_Context_Tile_Refine:
    """Plan context-aware tile refinement for an already-upscaled image.

    Pure-logic node: it computes the tiling geometry, per-tile context
    windows and the feathered blend profile, and reports seam-continuity
    statistics.  It does NOT run a diffusion model or touch GPU tensors.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 1, "max": 8192,
                                  "step": 1}),
                "height": ("INT", {"default": 1024, "min": 1, "max": 8192,
                                   "step": 1}),
                "tile_size": ("INT", {"default": 512, "min": _MIN_TILE,
                                      "max": _MAX_TILE, "step": 1}),
                "overlap": ("INT", {"default": 64, "min": _MIN_OVERLAP,
                                    "max": _MAX_OVERLAP, "step": 1}),
                "blend_mode": (list(BLEND_MODES),),
            },
            "optional": {
                "seam_tolerance": ("FLOAT", {"default": 1e-3, "min": 0.0,
                                             "max": 1.0, "step": 1e-5}),
                "left_seam": ("STRING", {"default": "0,0,0",
                                         "multiline": False}),
                "right_seam": ("STRING", {"default": "0,0,0",
                                          "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("plan_json", "tile_count", "seam_continuous", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _parse_seam(text):
        """Parse a comma-separated string of numbers into a list of floats."""
        if not text:
            return []
        out = []
        for part in str(text).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(float(part))
            except ValueError:
                return None
        return out

    def run(self, width, height, tile_size, overlap, blend_mode,
            seam_tolerance=1e-3, left_seam="0,0,0", right_seam="0,0,0"):
        plan = plan_refinement(width, height, tile_size, overlap, blend_mode)
        plan_json = json.dumps(plan, sort_keys=True)

        left = self._parse_seam(left_seam)
        right = self._parse_seam(right_seam)
        if left is None or right is None:
            return (plan_json, plan["tile_count"], False,
                    "seam input is not valid comma-separated numbers")
        seam = check_seam_continuity(left, right, tolerance=seam_tolerance)
        reason = "; ".join(plan["params"]["warnings"]) or seam["reason"]
        return (plan_json, plan["tile_count"], seam["continuous"], reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Context_Tile_Refine": PSN_Context_Tile_Refine,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Context_Tile_Refine": "Context-Aware Tile Refinement (Plan)",
}
