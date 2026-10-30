"""Deterministic seed-based conditioning (pure-logic, secure-by-design).

This module implements the *logic* of a "Zero-CLIP" conditioner: it maps an
integer seed to a deterministic, reproducible conditioning payload using only
the Python standard library (``hashlib`` + ``struct``). It does NOT import
torch, ComfyUI, numpy, or any model weights, and it performs no file, network,
or OS access.

Because a real ComfyUI ``CONDITIONING`` is a list of ``[clip_embedding,
pooled_embedding]`` tensors, this node emits the *data* of that structure as
plain JSON text (``conditioning_json``) plus a human-readable ``summary``.
Downstream GPU code can deserialize the JSON and build the actual tensors.

Strategies:
  * A - Anchor-weighted: deterministic pseudo-random weights (no external
        anchor file is read; the "anchors" are derived from the seed).
  * B - Hash-based: raw SHA-256 digest bytes mapped to floats.
  * C - LCG-based: linear congruential generator seeded by the integer seed.
  * D - Mixed: combines B and C for extra diffusion.

All strategies are pure functions of (seed, strategy, model_type), so the same
inputs always yield byte-identical outputs.
"""

import hashlib
import json
import struct

CAT = "ParametricStudio/Conditioning"

_STRATEGIES = ["A", "B", "C", "D"]
_MODEL_TYPES = ["sd15", "sdxl"]

# (clip_dim, pooled_dim) per model architecture.
# SD1.5: clip 768, pooled 768. SDXL: clip 2048, pooled 1280.
_MODEL_DIMS = {
    "sd15": (768, 768),
    "sdxl": (2048, 1280),
}

# Number of "anchor" slots used by strategy A.
_ANCHOR_SLOTS = 16


def _digest_bytes(seed, strategy, salt):
    """Return 32 raw digest bytes for the given seed/strategy/salt."""
    payload = "{}|{}|{}".format(seed, strategy, salt).encode("utf-8")
    return hashlib.sha256(payload).digest()


def _bytes_to_floats(raw, count):
    """Map raw bytes to `count` floats in [-1, 1] deterministically."""
    out = []
    for i in range(count):
        # Take 4 bytes at a time (wrapping) and interpret as a signed 32-bit int.
        idx = (i * 4) % len(raw)
        chunk = raw[idx:idx + 4]
        # Pad if the tail is short (should not happen with 32-byte digests,
        # but be safe for very large counts by cycling).
        while len(chunk) < 4:
            chunk += raw[: 4 - len(chunk)]
        value = struct.unpack(">i", chunk)[0]
        # Normalize signed 32-bit int to [-1, 1].
        out.append(value / 2147483648.0)
    return out


def _lcg_floats(seed, count):
    """Generate `count` floats in [-1, 1] using a 64-bit LCG."""
    # Constants (Numerical Recipes style).
    a = 6364136223846793005
    c = 1442695040888963407
    m = 1 << 64
    state = (seed & (m - 1)) or 1  # avoid 0 state
    out = []
    for _ in range(count):
        state = (a * state + c) % m
        # Take the high 32 bits as a signed int for better distribution.
        hi = (state >> 32) & 0xFFFFFFFF
        if hi >= 0x80000000:
            hi -= 0x100000000
        out.append(hi / 2147483648.0)
    return out


def _anchor_weights(seed, slots):
    """Strategy A: derive `slots` anchor weights in [0, 1] from the seed."""
    raw = _digest_bytes(seed, "A", "anchor")
    weights = []
    for i in range(slots):
        idx = (i * 4) % len(raw)
        chunk = raw[idx:idx + 4]
        while len(chunk) < 4:
            chunk += raw[: 4 - len(chunk)]
        value = struct.unpack(">I", chunk)[0]
        weights.append(value / 4294967296.0)
    return weights


def _build_clip_vector(seed, strategy, clip_dim):
    """Build the clip embedding vector for the given strategy."""
    if strategy == "A":
        # Anchor-weighted: blend anchor weights with hash-based values.
        anchors = _anchor_weights(seed, _ANCHOR_SLOTS)
        base = _bytes_to_floats(_digest_bytes(seed, "A", "clip"), clip_dim)
        # Weight each element by the nearest anchor weight.
        out = []
        for i, v in enumerate(base):
            w = anchors[i % _ANCHOR_SLOTS]
            out.append(v * (0.5 + 0.5 * w))
        return out
    elif strategy == "B":
        return _bytes_to_floats(_digest_bytes(seed, "B", "clip"), clip_dim)
    elif strategy == "C":
        return _lcg_floats(seed, clip_dim)
    elif strategy == "D":
        # Mixed: average of B and C.
        b = _bytes_to_floats(_digest_bytes(seed, "D", "clip"), clip_dim)
        c = _lcg_floats(seed, clip_dim)
        return [(x + y) * 0.5 for x, y in zip(b, c)]
    raise ValueError("Unknown strategy: {}".format(strategy))


def _build_pooled_vector(seed, strategy, pooled_dim):
    """Build the pooled embedding vector for the given strategy."""
    if strategy == "A":
        anchors = _anchor_weights(seed, _ANCHOR_SLOTS)
        base = _bytes_to_floats(_digest_bytes(seed, "A", "pooled"), pooled_dim)
        out = []
        for i, v in enumerate(base):
            w = anchors[i % _ANCHOR_SLOTS]
            out.append(v * (0.5 + 0.5 * w))
        return out
    elif strategy == "B":
        return _bytes_to_floats(_digest_bytes(seed, "B", "pooled"), pooled_dim)
    elif strategy == "C":
        return _lcg_floats(seed + 1, pooled_dim)  # offset seed for pooled
    elif strategy == "D":
        b = _bytes_to_floats(_digest_bytes(seed, "D", "pooled"), pooled_dim)
        c = _lcg_floats(seed + 1, pooled_dim)
        return [(x + y) * 0.5 for x, y in zip(b, c)]
    raise ValueError("Unknown strategy: {}".format(strategy))


def _round_floats(vec, decimals=6):
    """Round floats to a fixed number of decimals for stable JSON output."""
    return [round(v, decimals) for v in vec]


def generate_conditioning(seed, strategy, model_type):
    """Pure-logic core: produce the conditioning payload as a dict.

    Returns a dict with keys:
      * ``clip``: list of floats (length = clip_dim)
      * ``pooled``: list of floats (length = pooled_dim)
      * ``seed``: the input seed
      * ``strategy``: the strategy used
      * ``model_type``: the model type
      * ``clip_dim``: int
      * ``pooled_dim``: int
    """
    if strategy not in _STRATEGIES:
        raise ValueError("strategy must be one of {}".format(_STRATEGIES))
    if model_type not in _MODEL_TYPES:
        raise ValueError("model_type must be one of {}".format(_MODEL_TYPES))
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")

    clip_dim, pooled_dim = _MODEL_DIMS[model_type]
    clip = _build_clip_vector(seed, strategy, clip_dim)
    pooled = _build_pooled_vector(seed, strategy, pooled_dim)

    return {
        "clip": _round_floats(clip),
        "pooled": _round_floats(pooled),
        "seed": seed,
        "strategy": strategy,
        "model_type": model_type,
        "clip_dim": clip_dim,
        "pooled_dim": pooled_dim,
    }


class PSN_ZeroCLIPConditioner:
    """Map an integer seed to a deterministic conditioning payload.

    Outputs the conditioning data as JSON text (``conditioning_json``) and a
    short human-readable ``summary``. The JSON can be deserialized by GPU-side
    code to build the actual ComfyUI ``CONDITIONING`` tensors.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": -2**63, "max": 2**63 - 1, "step": 1}),
                "strategy": (_STRATEGIES,),
                "model_type": (_MODEL_TYPES,),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("conditioning_json", "summary")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, seed, strategy, model_type):
        payload = generate_conditioning(seed, strategy, model_type)
        conditioning_json = json.dumps(payload, separators=(",", ":"))
        summary = (
            "seed={} strategy={} model={} clip_dim={} pooled_dim={}".format(
                seed, strategy, model_type, payload["clip_dim"], payload["pooled_dim"]
            )
        )
        return (conditioning_json, summary)


NODE_CLASS_MAPPINGS = {
    "PSN_ZeroCLIPConditioner": PSN_ZeroCLIPConditioner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ZeroCLIPConditioner": "ZeroCLIP Conditioner (Seed-Based)",
}
