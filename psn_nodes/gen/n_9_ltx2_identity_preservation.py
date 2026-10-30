"""Pure-logic LTX2 identity preservation helpers.

This module implements the *logic* of the LTX2 identity-preservation nodes
(PSN_LTX2_Identity_Lock and PSN_LTX2_Stabilize) without any GPU/torch/ComfyUI
internals.  Because the real nodes operate on ``LATENT`` tensors, this
implementation works on plain Python lists of floats that stand in for a
flattened latent.  All functions take and return plain values (lists of
floats, numbers, strings) so they can be unit-tested with the standard
library only.

The two operations:

* **Identity lock** -- blends the current latent with a reference latent so
  that identity features are preserved.  ``locked = (1 - strength) * current
  + strength * reference``.

* **Stabilize** -- applies a simple low-pass (moving-average) filter in the
  spatial domain to reduce high-frequency noise that disrupts identity.  A
  moving average is a low-pass filter; the ``stability_factor`` controls how
  much of the smoothed signal is mixed back in.

No network, file, OS, subprocess, eval/exec, or dunder tricks are used.
"""

import math

CAT = "ParametricStudio/LTX2"


def _as_float_list(value, name):
    """Coerce *value* into a flat list of floats.

    Accepts a list/tuple of numbers.  Raises ``ValueError`` for anything that
    is not a sequence of real numbers.
    """
    if value is None:
        raise ValueError("%s must be a list of numbers" % name)
    if isinstance(value, (int, float)):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list of numbers" % name)
    out = []
    for i, item in enumerate(value):
        if isinstance(item, bool):
            raise ValueError("%s[%d] is not a number" % (name, i))
        if not isinstance(item, (int, float)):
            raise ValueError("%s[%d] is not a number" % (name, i))
        f = float(item)
        if math.isnan(f) or math.isinf(f):
            raise ValueError("%s[%d] is not finite" % (name, i))
        out.append(f)
    return out


def _clamp01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def identity_lock(current, reference, lock_strength):
    """Blend *current* toward *reference* by *lock_strength*.

    Returns a new list.  ``lock_strength`` is clamped to [0, 1].  The two
    inputs must have the same length.
    """
    cur = _as_float_list(current, "current")
    ref = _as_float_list(reference, "reference")
    if len(cur) != len(ref):
        raise ValueError(
            "current and reference must have the same length (%d vs %d)"
            % (len(cur), len(ref))
        )
    s = _clamp01(float(lock_strength))
    return [(1.0 - s) * c + s * r for c, r in zip(cur, ref)]


def _moving_average(values, window):
    """Simple centered moving average with edge clamping."""
    n = len(values)
    if n == 0:
        return []
    half = window // 2
    out = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        seg = values[lo:hi]
        out.append(sum(seg) / float(len(seg)))
    return out


def stabilize(latent, stability_factor):
    """Low-pass filter *latent* and blend with the original.

    A moving-average window of 3 is applied (a basic low-pass), then the
    result is mixed with the original by *stability_factor* (clamped to
    [0, 1]).  ``stability_factor`` of 0 returns the original; 1 returns the
    fully smoothed signal.
    """
    vals = _as_float_list(latent, "latent")
    f = _clamp01(float(stability_factor))
    if len(vals) == 0:
        return []
    smoothed = _moving_average(vals, 3)
    return [(1.0 - f) * v + f * s for v, s in zip(vals, smoothed)]


def _similarity(a, b):
    """Cosine similarity between two equal-length float lists."""
    if len(a) != len(b):
        raise ValueError("length mismatch")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _high_freq_energy(values):
    """Sum of squared first-differences (a proxy for high-frequency content)."""
    if len(values) < 2:
        return 0.0
    return sum((b - a) ** 2 for a, b in zip(values, values[1:]))


class PSN_LTX2_Identity_Lock:
    """Blend the current latent with a reference latent to preserve identity."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "current_latent": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "reference_latent": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "lock_strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("locked_latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, current_latent, reference_latent, lock_strength):
        return (identity_lock(current_latent, reference_latent, lock_strength),)


class PSN_LTX2_Stabilize:
    """Low-pass filter a latent to reduce high-frequency identity noise."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "stability_factor": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("stabilized_latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, stability_factor):
        return (stabilize(latent, stability_factor),)


NODE_CLASS_MAPPINGS = {
    "PSN_LTX2_Identity_Lock": PSN_LTX2_Identity_Lock,
    "PSN_LTX2_Stabilize": PSN_LTX2_Stabilize,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LTX2_Identity_Lock": "LTX2 Identity Lock",
    "PSN_LTX2_Stabilize": "LTX2 Stabilize",
}
