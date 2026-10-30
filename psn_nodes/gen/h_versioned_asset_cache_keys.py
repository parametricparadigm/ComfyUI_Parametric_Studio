"""Versioned asset cache keys for ComfyUI.

Builds deterministic, versioned cache keys from model, prompt, style and
optional numeric parameters.  A key changes whenever any input changes, so
downstream caches (e.g. generated sprites or backgrounds) are invalidated
exactly when they should be, while unchanged inputs keep their cached assets.

The module is pure Python + stdlib (hashlib, json, re).  No network, no file
I/O, no subprocess.
"""

import hashlib
import json
import re

CAT = "ParametricStudio/Cache"

# Bump this when the key algorithm itself changes so old caches are
# automatically invalidated.
ALGO_VERSION = 1


def _normalize_text(value):
    """Collapse whitespace and strip so trivial edits do not change keys."""
    if not isinstance(value, str):
        raise TypeError("expected str, got %r" % type(value).__name__)
    return re.sub(r"\s+", " ", value).strip()


def _normalize_number(value):
    """Accept int/float, reject bool/str, round to 6 decimals for stability."""
    if isinstance(value, bool):
        raise TypeError("bool is not a valid numeric parameter")
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    raise TypeError("expected int or float, got %r" % type(value).__name__)


def build_cache_key(model, prompt, style, seed=None, steps=None, cfg=None):
    """Build a deterministic versioned cache key.

    Args:
        model:  str, model identifier (e.g. "sd_xl_base_1.0").
        prompt: str, the generation prompt.
        style:  str, style preset name (e.g. "anime", "realistic").
        seed:   optional int, random seed.
        steps:  optional int, sampler steps.
        cfg:    optional float, CFG scale.

    Returns:
        str:  a stable hex digest prefixed with the algorithm version.

    Raises:
        TypeError:  if any argument has the wrong type.
        ValueError: if a required string is empty after normalization.
    """
    model_n = _normalize_text(model)
    prompt_n = _normalize_text(prompt)
    style_n = _normalize_text(style)

    if not model_n:
        raise ValueError("model must not be empty")
    if not prompt_n:
        raise ValueError("prompt must not be empty")
    if not style_n:
        raise ValueError("style must not be empty")

    seed_n = None if seed is None else _normalize_number(seed)
    steps_n = None if steps is None else _normalize_number(steps)
    cfg_n = None if cfg is None else _normalize_number(cfg)

    payload = {
        "v": ALGO_VERSION,
        "model": model_n,
        "prompt": prompt_n,
        "style": style_n,
        "seed": seed_n,
        "steps": steps_n,
        "cfg": cfg_n,
    }
    # sort_keys ensures a stable serialization regardless of dict order.
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return "v%d-%s" % (ALGO_VERSION, digest)


def keys_equal(key_a, key_b):
    """Return True if two cache keys refer to the same asset version."""
    if not isinstance(key_a, str) or not isinstance(key_b, str):
        raise TypeError("cache keys must be strings")
    return key_a == key_b


def is_valid_key(key):
    """Check that a string looks like a key produced by build_cache_key."""
    if not isinstance(key, str):
        return False
    m = re.fullmatch(r"v(\d+)-[0-9a-f]{64}", key)
    return m is not None


class PSN_VersionedAssetCacheKey:
    """Build a versioned cache key from model, prompt, style and optional params."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("STRING", {"default": "", "multiline": False}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "style": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 32 - 1}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 30.0}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("cache_key",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, prompt, style, seed=0, steps=20, cfg=7.0):
        key = build_cache_key(model, prompt, style, seed=seed, steps=steps, cfg=cfg)
        return (key,)


class PSN_CacheKeyCompare:
    """Compare two cache keys and report whether they match."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key_a": ("STRING", {"default": ""}),
                "key_b": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("match", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, key_a, key_b):
        if not is_valid_key(key_a) or not is_valid_key(key_b):
            return (False, "invalid_key")
        match = keys_equal(key_a, key_b)
        status = "hit" if match else "miss"
        return (match, status)


NODE_CLASS_MAPPINGS = {
    "PSN_VersionedAssetCacheKey": PSN_VersionedAssetCacheKey,
    "PSN_CacheKeyCompare": PSN_CacheKeyCompare,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VersionedAssetCacheKey": "Versioned Asset Cache Key",
    "PSN_CacheKeyCompare": "Cache Key Compare",
}
