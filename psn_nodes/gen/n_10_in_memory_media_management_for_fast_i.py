"""PSN In-Memory Media Management for Fast Iteration.

Provides an LRU-backed in-memory cache for media tensors so that repeated
accesses to the same media (identified by a cache key / path) do not require
re-loading from disk.  The node itself never touches the filesystem (that is
forbidden in this sandbox); instead it accepts a *media* tensor input and a
*media_path* string that acts as the logical identity of the media.  The
cache is a plain Python LRU structure built on ``collections.OrderedDict``.
"""

from __future__ import annotations

import torch
from collections import OrderedDict

CAT = "ParametricStudio/Media"


def _as_tensor(media):
    """Coerce *media* to a float32 CPU tensor (no in-place mutation)."""
    if isinstance(media, torch.Tensor):
        t = media.detach().clone().float()
    else:
        t = torch.as_tensor(media, dtype=torch.float32)
    return t


class _LRUCache:
    """Tiny LRU cache with a hard capacity limit."""

    def __init__(self, max_size: int = 8):
        self.max_size = max(1, int(max_size))
        self._data: OrderedDict = OrderedDict()

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str):
        """Return (value, hit).  On hit the key is moved to most-recent."""
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key], True
        return None, False

    def put(self, key: str, value) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)  # evict least-recently-used

    def clear(self) -> None:
        self._data.clear()


# Module-level cache shared across node instances (one per process).
_CACHE = _LRUCache(max_size=8)


def _cache_key_for(media_path: str, cache_key: str) -> str:
    """Build the effective cache key.

    If *cache_key* is non-empty it is used verbatim; otherwise the
    *media_path* string is used as the key.
    """
    if cache_key and cache_key.strip():
        return cache_key.strip()
    return media_path.strip()


class PSN_Memory_Media_Manager:
    """Cache media tensors in memory (LRU) to avoid repeated disk reads.

    Inputs
    ------
    media : IMAGE
        The media tensor [B, H, W, C] in 0..1.
    media_path : STRING
        Logical path / identifier of the media (used as cache key when
        *cache_key* is empty).
    cache_key : STRING (optional)
        Explicit cache key; overrides *media_path* when non-empty.
    max_cache_size : INT
        Maximum number of items to keep in the LRU cache.

    Outputs
    -------
    media : IMAGE
        The (cloned) media tensor.
    cache_hit : BOOLEAN
        True when the tensor was served from the in-memory cache.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "media": ("IMAGE",),
                "media_path": ("STRING", {"default": ""}),
                "max_cache_size": ("INT", {"default": 8, "min": 1, "max": 256}),
            },
            "optional": {
                "cache_key": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN")
    RETURN_NAMES = ("media", "cache_hit")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, media, media_path, max_cache_size, cache_key=""):
        # Normalise the cache capacity (the module-level cache is shared).
        _CACHE.max_size = max(1, int(max_cache_size))

        key = _cache_key_for(media_path, cache_key)
        if not key:
            raise ValueError("media_path or cache_key must be non-empty")

        value, hit = _CACHE.get(key)
        if hit:
            out = value.detach().clone().float()
        else:
            out = _as_tensor(media)
            _CACHE.put(key, out)

        return (out, hit)


class PSN_Memory_Media_Clear:
    """Clear the shared in-memory media cache."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("cleared",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self):
        _CACHE.clear()
        return (True,)


NODE_CLASS_MAPPINGS = {
    "PSN_Memory_Media_Manager": PSN_Memory_Media_Manager,
    "PSN_Memory_Media_Clear": PSN_Memory_Media_Clear,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Memory_Media_Manager": "Memory Media Manager (LRU)",
    "PSN_Memory_Media_Clear": "Memory Media Cache Clear",
}
