"""ParametricStudio: Fast model loading via GPU residency.

Implements a process-wide LRU cache that keeps "models" (here: small CPU
tensor stand-ins, since real ComfyUI MODEL objects are opaque and we cannot
import ComfyUI internals) resident so that repeated pipeline executions do
not pay the load cost again.

Real ComfyUI types are not available in this sandbox, so the MODEL slot is
documented as a dict {"weights": torch.Tensor, "meta": dict} which is the
lightest faithful stand-in: it carries a tensor (like a real model's
parameters) plus metadata, and is never mutated in place.
"""

import time
from collections import OrderedDict

import torch

CAT = "ParametricStudio/ModelResidency"

# ---------------------------------------------------------------------------
# Global LRU cache (module-level, shared across nodes in the same process).
# Entry: OrderedDict[cache_key] = {"model": model, "expires_at": float}
# ---------------------------------------------------------------------------
_CACHE = OrderedDict()
_CACHE_MAX_ENTRIES = 8


def _now():
    return time.monotonic()


def _cache_put(cache_key, model, ttl_seconds):
    """Insert/refresh an entry, evicting LRU entries beyond the cap."""
    if cache_key in _CACHE:
        _CACHE.move_to_end(cache_key)
    _CACHE[cache_key] = {"model": model, "expires_at": _now() + max(0, ttl_seconds)}
    while len(_CACHE) > _CACHE_MAX_ENTRIES:
        _CACHE.popitem(last=False)


def _cache_get(cache_key):
    """Return (model, was_cached). Expired entries are removed."""
    entry = _CACHE.get(cache_key)
    if entry is None:
        return None, False
    if _now() >= entry["expires_at"]:
        del _CACHE[cache_key]
        return None, False
    _CACHE.move_to_end(cache_key)
    return entry["model"], True


def _cache_clear():
    _CACHE.clear()


def _cache_size():
    return len(_CACHE)


def _make_model(weights=None, meta=None):
    """Build a stand-in MODEL: dict with a CPU tensor and metadata."""
    if weights is None:
        weights = torch.zeros(2, 2)
    if meta is None:
        meta = {}
    return {"weights": weights, "meta": dict(meta)}


def _validate_model(model):
    if not isinstance(model, dict):
        raise ValueError("model must be a dict stand-in with 'weights' tensor")
    if "weights" not in model or not isinstance(model["weights"], torch.Tensor):
        raise ValueError("model['weights'] must be a torch.Tensor")


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
class PSN_Register_Resident_Model:
    """Store a model in the global LRU residency cache under cache_key."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "cache_key": ("STRING", {"default": "unet"}),
                "ttl_seconds": ("INT", {"default": 300, "min": 0, "max": 86400}),
            }
        }

    RETURN_TYPES = ("HIDDEN",)
    RETURN_NAMES = ("cache_handle",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, cache_key, ttl_seconds):
        _validate_model(model)
        if not isinstance(cache_key, str) or not cache_key.strip():
            raise ValueError("cache_key must be a non-empty string")
        # Never mutate the input: store a copy of the weights tensor and a
        # fresh meta dict so downstream edits to the cached model cannot
        # affect the caller's object.
        stored = {"weights": model["weights"].clone(), "meta": dict(model.get("meta", {}))}
        _cache_put(cache_key, stored, ttl_seconds)
        return (cache_key,)


class PSN_Get_Resident_Model:
    """Retrieve a model from the residency cache; None + was_cached=False on miss."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "cache_key": ("STRING", {"default": "unet"}),
            }
        }

    RETURN_TYPES = ("MODEL", "BOOLEAN")
    RETURN_NAMES = ("model", "was_cached")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, cache_key):
        if not isinstance(cache_key, str):
            raise ValueError("cache_key must be a string")
        model, was_cached = _cache_get(cache_key)
        return (model, was_cached)


class PSN_Resident_Cache_Info:
    """Report cache statistics (size, keys) for debugging."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("keys", "size")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self):
        keys = ",".join(_CACHE.keys())
        return (keys, _cache_size())


NODE_CLASS_MAPPINGS = {
    "PSN_Register_Resident_Model": PSN_Register_Resident_Model,
    "PSN_Get_Resident_Model": PSN_Get_Resident_Model,
    "PSN_Resident_Cache_Info": PSN_Resident_Cache_Info,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Register_Resident_Model": "Register Resident Model",
    "PSN_Get_Resident_Model": "Get Resident Model",
    "PSN_Resident_Cache_Info": "Resident Cache Info",
}
