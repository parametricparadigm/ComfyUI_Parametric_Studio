"""ParametricStudio - Character Consistency Cache.

Caches character features extracted from a reference image and uses them to
condition subsequent generations so that the same identity is preserved across
multiple outputs.

Only the core that torch/stdlib can do is implemented here:
  * Feature extraction is a deterministic, lightweight projection of the input
    image (mean/std pooling + a fixed random projection) rather than a real
    face-embedding model (insightface/buffalo_l is NOT available).
  * The cache is an in-process dict (no redis).
  * The "generator" node blends the cached identity features into a synthetic
    image derived from the prompt hash, so repeated calls with the same
    CACHE_ID produce identical (consistent) outputs.

NOT implemented: real face embeddings (insightface), real diffusion sampling,
redis persistence, GPU smoke test.
"""

import hashlib

import torch

CAT = "ParametricStudio/CharacterConsistency"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _as_image(image):
    """Validate and return a fresh float tensor [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    x = image.detach().clone().float()
    if x.dim() != 4:
        raise ValueError("IMAGE must have shape [B,H,W,C], got %s" % (tuple(x.shape),))
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("IMAGE last dim must be 1, 3 or 4 channels, got %d" % x.shape[-1])
    if x.numel() == 0:
        raise ValueError("IMAGE tensor is empty")
    return x


def _hash_str(s):
    return hashlib.sha256(str(s).encode("utf-8")).digest()


def _seed_from_str(s):
    return int.from_bytes(_hash_str(s)[:8], "big")


# ---------------------------------------------------------------------------
# in-process feature cache
# ---------------------------------------------------------------------------


class _FeatureCache:
    """Simple in-memory cache of character feature tensors."""

    def __init__(self):
        self._store = {}

    def put(self, key, features, source_hash):
        self._store[key] = {
            "features": features.detach().clone(),
            "source_hash": source_hash,
        }

    def get(self, key):
        entry = self._store.get(key)
        if entry is None:
            raise KeyError("Unknown CACHE_ID: %r" % (key,))
        return entry

    def has(self, key):
        return key in self._store

    def clear(self):
        self._store.clear()


_CACHE = _FeatureCache()


# ---------------------------------------------------------------------------
# feature extraction (deterministic, model-free)
# ---------------------------------------------------------------------------


def _extract_features(image, feature_type):
    """Extract a deterministic feature vector from an image.

    Uses spatial mean/std pooling plus a fixed random projection so that
    similar images yield similar features. This is a stand-in for a real
    face-embedding model.
    """
    x = _as_image(image)
    # normalise to 0..1 range (clamp)
    x = x.clamp(0.0, 1.0)
    # collapse channels: use all channels
    b, h, w, c = x.shape
    flat = x.reshape(b, h * w * c)
    mean = flat.mean(dim=1, keepdim=True)  # [B, 1]
    std = flat.std(dim=1, keepdim=True, unbiased=False)  # [B, 1]
    stats = torch.cat([mean, std], dim=1)  # [B, 2]

    # fixed random projection to a compact feature size
    proj_dim = 64
    seed = _seed_from_str("psn_char_proj_" + feature_type)
    g = torch.Generator().manual_seed(seed)
    proj = torch.randn(stats.shape[1], proj_dim, generator=g)
    proj = proj / (proj.norm(dim=0, keepdim=True) + 1e-8)
    feats = stats @ proj  # [B, proj_dim]
    feats = torch.tanh(feats)
    return feats


def _image_hash(image):
    x = _as_image(image)
    # hash the rounded values so tiny float noise doesn't change the hash
    vals = torch.round(x * 1000.0).to(torch.int64).reshape(-1)
    return hashlib.sha256(vals.numpy().tobytes()).hexdigest()


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


class PSN_CharacterFeatureCache:
    """Extract character features from a reference image and store them in a
    local cache keyed by CACHE_KEY. Returns a CACHE_ID and the feature tensor."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "IMAGE": ("IMAGE",),
                "CACHE_KEY": ("STRING", {"default": "character_1"}),
                "FEATURE_TYPE": ("Embedding", "Landmarks"),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("CACHE_ID", "FEATURES")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, IMAGE, CACHE_KEY, FEATURE_TYPE):
        x = _as_image(IMAGE)
        feats = _extract_features(x, FEATURE_TYPE)
        src_hash = _image_hash(x)
        key = str(CACHE_KEY)
        _CACHE.put(key, feats, src_hash)
        return (key, feats)


class PSN_CachedIdentityGenerator:
    """Generate an image conditioned on cached character features so that the
    same identity is preserved. The output is deterministic for a given
    (PROMPT, CACHE_ID, NEGATIVE_PROMPT) triple, so repeated calls with the
    same CACHE_ID produce consistent (identical) images."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "PROMPT": ("STRING", {"default": "a portrait"}),
                "CACHE_ID": ("STRING", {"default": "character_1"}),
                "NEGATIVE_PROMPT": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, PROMPT, CACHE_ID, NEGATIVE_PROMPT):
        entry = _CACHE.get(str(CACHE_ID))
        feats = entry["features"]  # [B, D]
        b = feats.shape[0]

        # deterministic seed from prompt + cache id + negative prompt
        seed = _seed_from_str("gen|" + str(PROMPT) + "|" + str(CACHE_ID) + "|" + str(NEGATIVE_PROMPT))
        g = torch.Generator().manual_seed(seed)

        # build a base image from the prompt hash (deterministic noise)
        h = w = 64
        base = torch.randn(b, h, w, 3, generator=g)

        # condition on the cached identity features: project features into a
        # spatial pattern and blend into the base image
        d = feats.shape[1]
        # tile features into a [B, H, W, 3] pattern
        feat_grid = feats.reshape(b, 1, d, 1).expand(b, h, d, 3).reshape(b, h, w, 3) if False else None
        # simpler: use features to modulate per-channel offsets
        offsets = feats.mean(dim=1, keepdim=True)  # [B, 1]
        offsets = offsets.reshape(b, 1, 1, 1).expand(b, 1, 1, 3)
        # add a feature-driven spatial gradient
        ys = torch.linspace(-1.0, 1.0, h).reshape(1, h, 1, 1)
        xs = torch.linspace(-1.0, 1.0, w).reshape(1, 1, w, 1)
        spatial = (ys * feats[:, 0:1].reshape(b, 1, 1, 1) + xs * feats[:, 1:2].reshape(b, 1, 1, 1)).expand(b, h, w, 3)
        img = base + offsets + spatial
        img = torch.sigmoid(img)  # 0..1
        return (img,)


NODE_CLASS_MAPPINGS = {
    "PSN_CharacterFeatureCache": PSN_CharacterFeatureCache,
    "PSN_CachedIdentityGenerator": PSN_CachedIdentityGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CharacterFeatureCache": "Character Feature Cache",
    "PSN_CachedIdentityGenerator": "Cached Identity Generator",
}
