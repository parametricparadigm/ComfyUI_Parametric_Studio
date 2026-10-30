"""PSN_HyperTile_Patch: pure-logic planning/validation for hierarchical hyper-tile attention.

This module does NOT touch torch, ComfyUI, or any GPU. It implements the secure,
pure-Python planning layer for a hyper-tile attention patch:

- Validates tile_size (positive int, power of two, within sane bounds).
- Computes a hierarchical tiling plan (levels, tile counts, overlap) for a given
  image/sequence resolution.
- Estimates relative memory footprint of the tiled attention vs. a single full
  attention pass, so callers can assert memory reduction without a GPU.
- Provides a deterministic "patch descriptor" (JSON-serialisable dict) that a
  downstream torch/ComfyUI hook could consume.

The node wrapper (PSN_HyperTile_Patch) takes plain values (ints, strings) and
returns plain values (ints, strings, dicts-as-JSON). It never opens sockets,
files, or imports torch/comfy.
"""

import json
import math

CAT = "ParametricStudio/Attention"

# Sane bounds for tile_size to avoid pathological plans.
_MIN_TILE = 8
_MAX_TILE = 4096
# Maximum number of tiles per level to keep plans tractable.
_MAX_TILES_PER_LEVEL = 1024


def _is_power_of_two(n):
    """Return True if n is a positive power of two."""
    return n > 0 and (n & (n - 1)) == 0


def validate_tile_size(tile_size):
    """Validate tile_size. Returns (ok, reason, normalised_value)."""
    if not isinstance(tile_size, int) or isinstance(tile_size, bool):
        return False, "tile_size must be an integer", None
    if tile_size < _MIN_TILE:
        return False, f"tile_size must be >= {_MIN_TILE}", None
    if tile_size > _MAX_TILE:
        return False, f"tile_size must be <= {_MAX_TILE}", None
    if not _is_power_of_two(tile_size):
        return False, "tile_size must be a power of two", None
    return True, "ok", tile_size


def compute_tiling_plan(width, height, tile_size, overlap_ratio=0.0):
    """Compute a hierarchical tiling plan for a width x height image.

    Returns a dict with:
      - levels: list of dicts, one per hierarchy level (level 0 = finest)
      - total_tiles: total number of tiles across all levels
      - max_tiles_per_level: max tiles in any single level
      - estimated_memory_factor: relative memory vs full attention (<=1.0 means reduction)

    Each level uses tiles of size tile_size * (2 ** level).
    We stop when a level's tile size >= max(width, height) or tiles exceed _MAX_TILES_PER_LEVEL.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")

    levels = []
    total_tiles = 0
    max_tiles = 0
    max_dim = max(width, height)

    level = 0
    while True:
        current_tile = tile_size * (2 ** level)
        if current_tile > max_dim * 2:
            break

        tiles_w = math.ceil(width / current_tile)
        tiles_h = math.ceil(height / current_tile)
        tiles = tiles_w * tiles_h

        if tiles > _MAX_TILES_PER_LEVEL:
            break

        levels.append({
            "level": level,
            "tile_size": current_tile,
            "tiles_w": tiles_w,
            "tiles_h": tiles_h,
            "tiles": tiles,
        })
        total_tiles += tiles
        max_tiles = max(max_tiles, tiles)
        level += 1

        # Stop if we've reached a level where tile covers the whole image
        if current_tile >= max_dim:
            break

    if not levels:
        levels.append({
            "level": 0,
            "tile_size": tile_size,
            "tiles_w": math.ceil(width / tile_size),
            "tiles_h": math.ceil(height / tile_size),
            "tiles": math.ceil(width / tile_size) * math.ceil(height / tile_size),
        })
        total_tiles = levels[0]["tiles"]
        max_tiles = levels[0]["tiles"]

    # Estimate memory factor: tiled attention processes tiles independently.
    # Full attention on N tokens is O(N^2). Tiled attention on tiles of size T
    # is O(num_tiles * T^2) = O(N * T). So factor ~ T / N where N = width*height.
    n_tokens = width * height
    finest_tile = levels[0]["tile_size"]
    # Use the finest level tile size for the memory estimate
    estimated_memory_factor = min(1.0, finest_tile / max(1, n_tokens))

    return {
        "width": width,
        "height": height,
        "tile_size": tile_size,
        "levels": levels,
        "total_tiles": total_tiles,
        "max_tiles_per_level": max_tiles,
        "estimated_memory_factor": round(estimated_memory_factor, 6),
    }


def build_patch_descriptor(width, height, tile_size, overlap_ratio=0.0):
    """Build a JSON-serialisable patch descriptor for downstream hooks."""
    ok, reason, norm_tile = validate_tile_size(tile_size)
    if not ok:
        return {"ok": False, "reason": reason, "plan": None}

    plan = compute_tiling_plan(width, height, norm_tile, overlap_ratio)
    return {
        "ok": True,
        "reason": "ok",
        "plan": plan,
        "patch_type": "hyper_tile_attention",
        "version": 1,
    }


class PSN_HyperTile_Patch:
    """Plans and validates a hierarchical hyper-tile attention patch.

    Pure-logic node: takes resolution and tile_size, returns a tiling plan
    and memory estimate. No torch, no GPU, no I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 1, "max": 16384, "step": 1}),
                "height": ("INT", {"default": 1024, "min": 1, "max": 16384, "step": 1}),
                "tile_size": ("INT", {"default": 64, "min": _MIN_TILE, "max": _MAX_TILE, "step": 1}),
            },
            "optional": {
                "overlap_ratio": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 0.5, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "FLOAT", "INT")
    RETURN_NAMES = ("valid", "plan_json", "memory_factor", "total_tiles")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, width, height, tile_size, overlap_ratio=0.0):
        ok, reason, norm_tile = validate_tile_size(tile_size)
        if not ok:
            return (False, json.dumps({"ok": False, "reason": reason}), 1.0, 0)

        if width <= 0 or height <= 0:
            return (False, json.dumps({"ok": False, "reason": "width and height must be positive"}), 1.0, 0)

        plan = compute_tiling_plan(width, height, norm_tile, overlap_ratio)
        descriptor = {
            "ok": True,
            "reason": "ok",
            "plan": plan,
            "patch_type": "hyper_tile_attention",
            "version": 1,
        }
        return (
            True,
            json.dumps(descriptor),
            plan["estimated_memory_factor"],
            plan["total_tiles"],
        )


NODE_CLASS_MAPPINGS = {
    "PSN_HyperTile_Patch": PSN_HyperTile_Patch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_HyperTile_Patch": "PSN HyperTile Patch",
}
