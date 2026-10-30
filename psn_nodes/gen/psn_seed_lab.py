"""PSN_Seed_Lab — pure-logic seed/noise manipulation for ancestral & SDE workflows.

This module implements ONLY the deterministic, dependency-free core of a
"seed lab": it derives a reproducible noise *descriptor* from a base seed,
a sampler mode and an offset, and it can render that descriptor into a
pure-Python pixel grid for visualization.

It does NOT import torch, numpy, comfy, or any GPU/ComfyUI internals, and it
performs no network, file, OS, subprocess, eval/exec or dunder tricks. The
"noise" output is therefore a plain dict (a descriptor: seed, mode, shape,
checksum) rather than a real tensor, and the "image" output is a plain list
of rows of ints rather than a torch tensor. Downstream GPU nodes would
consume the descriptor's seed/mode to materialize the actual tensor.

All functions and node wrappers take plain values (ints, strings) and return
plain values (ints, dicts, lists, strings).
"""

import hashlib

# --- constants -------------------------------------------------------------

# Sampler modes supported by the manipulator.
MODES = ("ancestral", "sde", "fixed")

# 64-bit mask used to keep derived seeds within a sane, non-negative range.
_MASK64 = (1 << 64) - 1

# FNV-1a 64-bit constants.
_FNV_OFFSET = 0xcbf29ce484222325
_FNV_PRIME = 0x100000001b3

# LCG (linear congruential generator) constants — Numerical Recipes.
_LCG_A = 6364136223846793005
_LCG_C = 1442695040888963407
_LCG_M = 1 << 64

# Default spatial shape for the noise descriptor / visualization grid.
_DEFAULT_SHAPE = (4, 4)


# --- pure helpers ----------------------------------------------------------

def psn_fnv1a64(text):
    """Return the 64-bit FNV-1a hash of a string as an unsigned int."""
    if not isinstance(text, str):
        raise TypeError("psn_fnv1a64 expects a str, got %r" % type(text).__name__)
    h = _FNV_OFFSET
    for ch in text:
        h ^= ord(ch)
        h = (h * _FNV_PRIME) & _MASK64
    return h


def psn_lcg_step(state):
    """Advance an LCG state by one step, returning the next state (64-bit)."""
    if not isinstance(state, int):
        raise TypeError("psn_lcg_step expects an int state")
    return (state * _LCG_A + _LCG_C) & _MASK64


def psn_derive_seed(base_seed, mode, offset):
    """Derive a deterministic 64-bit seed from base seed, mode and offset.

    The mode is folded in via FNV-1a so that the same base seed yields
    different noise for different sampler modes, and the offset is applied
    as a signed integer addition (wrapped to 64-bit) so that positive and
    negative offsets shift the seed space predictably.
    """
    if not isinstance(base_seed, int) or isinstance(base_seed, bool):
        raise TypeError("base_seed must be an int")
    if mode not in MODES:
        raise ValueError("mode must be one of %r, got %r" % (MODES, mode))
    if not isinstance(offset, int) or isinstance(offset, bool):
        raise TypeError("offset must be an int")

    # Fold the mode into the base seed deterministically.
    folded = (psn_fnv1a64("%s:%d" % (mode, base_seed))) & _MASK64
    # Apply the signed offset, wrapping into the 64-bit space.
    derived = (folded + offset) & _MASK64
    return derived


def psn_noise_descriptor(seed, mode, shape=_DEFAULT_SHAPE):
    """Build a plain-dict noise descriptor from a derived seed.

    The descriptor is deterministic: the same (seed, mode, shape) always
    yields the same dict, including a stable checksum over the first few
    LCG outputs so callers can cheaply verify reproducibility.
    """
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an int")
    if mode not in MODES:
        raise ValueError("mode must be one of %r, got %r" % (MODES, mode))
    if not isinstance(shape, (tuple, list)) or len(shape) != 2:
        raise ValueError("shape must be a 2-tuple of ints")
    if any((not isinstance(d, int) or isinstance(d, bool) or d <= 0) for d in shape):
        raise ValueError("shape dimensions must be positive ints")

    h = hashlib.sha256()
    state = seed & _MASK64
    for _ in range(8):
        state = psn_lcg_step(state)
        h.update(state.to_bytes(8, "big"))
    checksum = h.hexdigest()[:16]

    return {
        "seed": seed,
        "mode": mode,
        "shape": (int(shape[0]), int(shape[1])),
        "checksum": checksum,
    }


def psn_noise_to_grid(descriptor, width=4, height=4):
    """Render a noise descriptor into a pure-Python pixel grid.

    Returns a list of `height` rows, each a list of `width` ints in [0, 255].
    The grid is deterministic for a given descriptor: it is driven by an LCG
    seeded from the descriptor's seed, so identical descriptors produce
    identical grids.
    """
    if not isinstance(descriptor, dict):
        raise TypeError("descriptor must be a dict")
    for key in ("seed", "mode", "shape", "checksum"):
        if key not in descriptor:
            raise ValueError("descriptor missing key %r" % key)
    if descriptor["mode"] not in MODES:
        raise ValueError("descriptor mode invalid")
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise ValueError("width must be a positive int")
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        raise ValueError("height must be a positive int")

    state = descriptor["seed"] & _MASK64
    grid = []
    for _ in range(height):
        row = []
        for _ in range(width):
            state = psn_lcg_step(state)
            # Map the 64-bit LCG output into a 0..255 byte.
            row.append((state >> 56) & 0xFF)
        grid.append(row)
    return grid


# --- node wrappers ---------------------------------------------------------

class PSN_Seed_Manipulator:
    """Derive a deterministic noise descriptor from a base seed, mode and offset.

    Pure-logic only: no torch/numpy. The `noise` output is a plain dict
    descriptor (seed, mode, shape, checksum), not a tensor.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_seed": ("INT", {"default": 0, "min": -1e9, "max": 1e9, "step": 1}),
                "mode": (list(MODES),),
                "offset": ("INT", {"default": 0, "min": -1e9, "max": 1e9, "step": 1}),
            },
            "optional": {
                "shape": ("STRING", {"default": "4,4"}),
            },
        }

    RETURN_TYPES = ("INT", "DICT")
    RETURN_NAMES = ("seed", "noise")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/SeedLab"

    def run(self, base_seed, mode, offset, shape="4,4"):
        # Parse the optional "h,w" shape string defensively.
        try:
            parts = [p.strip() for p in str(shape).split(",")]
            if len(parts) != 2:
                raise ValueError
            h, w = int(parts[0]), int(parts[1])
            if h <= 0 or w <= 0:
                raise ValueError
            shape_tuple = (h, w)
        except (ValueError, TypeError):
            shape_tuple = _DEFAULT_SHAPE

        derived = psn_derive_seed(base_seed, mode, offset)
        descriptor = psn_noise_descriptor(derived, mode, shape_tuple)
        return (derived, descriptor)


class PSN_Seed_Visualizer:
    """Convert a noise descriptor into a pure-Python pixel grid for visualization.

    Pure-logic only: no torch/numpy. The `noise_image` output is a list of
    rows of ints (0..255), not a torch IMAGE tensor.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "noise": ("DICT",),
            },
            "optional": {
                "width": ("INT", {"default": 4, "min": 1, "max": 512, "step": 1}),
                "height": ("INT", {"default": 4, "min": 1, "max": 512, "step": 1}),
            },
        }

    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("noise_image",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/SeedLab"

    def run(self, noise, width=4, height=4):
        grid = psn_noise_to_grid(noise, width=width, height=height)
        return (grid,)


# --- mappings --------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Seed_Manipulator": PSN_Seed_Manipulator,
    "PSN_Seed_Visualizer": PSN_Seed_Visualizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Seed_Manipulator": "PSN Seed Manipulator",
    "PSN_Seed_Visualizer": "PSN Seed Visualizer",
}
