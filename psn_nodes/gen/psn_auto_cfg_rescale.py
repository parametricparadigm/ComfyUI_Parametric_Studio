"""PSN_Auto_CFG_Rescale: pure-logic CFG rescaling helpers.

This module implements the *mathematical* core of an automatic CFG
rescaler. It does NOT touch torch, ComfyUI internals, or any model
objects. Instead it exposes:

- ``rescale_cfg(cfg, diff, max_cfg, mode)``: given the current CFG
  scale, the magnitude of the conditional/unconditional noise
  difference, a hard ceiling, and a rescale mode, returns the
  (possibly reduced) CFG value.
- ``PSN_Auto_CFG_Rescale``: a ComfyUI-style node wrapper that takes
  plain numeric inputs and returns the rescaled CFG plus diagnostic
  strings. The ``model`` input/output is represented as a plain
  ``STRING`` token (e.g. the model name) so the node can be wired
  into a graph without requiring a real MODEL object.

Only the Python standard library is used. No network, file, OS,
subprocess, eval/exec, or dunder tricks.
"""

from __future__ import annotations

import math

CAT = "ParametricStudio/CFG"

# Allowed rescale modes
_MODES = ("linear", "sigmoid", "none")

# Sigmoid steepness and midpoint used when mode == "sigmoid".
_SIGMOID_K = 2.0
_SIGMOID_MID = 0.5


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* into [lo, hi] without using builtins that mutate."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _sigmoid(x: float) -> float:
    """Numerically stable logistic function."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def rescale_cfg(
    cfg: float,
    diff: float,
    max_cfg: float,
    mode: str,
) -> float:
    """Compute the rescaled CFG value.

    Parameters
    ----------
    cfg:
        Current CFG scale (positive number).
    diff:
        Magnitude of the conditional/unconditional noise difference.
        Larger values indicate a stronger signal and therefore a
        higher risk of over-saturation.
    max_cfg:
        Hard ceiling for the CFG value.
    mode:
        One of ``"linear"``, ``"sigmoid"``, ``"none"``.

    Returns
    -------
    float
        The rescaled CFG value, always in ``(0, max_cfg]`` when
        ``cfg > 0`` and ``max_cfg > 0``.

    Raises
    ------
    ValueError
        If *mode* is not one of the allowed modes, or if any numeric
        input is not finite.
    """
    if mode not in _MODES:
        raise ValueError(f"Unknown rescale mode: {mode!r}")

    for name, val in (("cfg", cfg), ("diff", diff), ("max_cfg", max_cfg)):
        if not isinstance(val, (int, float)):
            raise TypeError(f"{name} must be a number, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be finite, got {val!r}")

    if cfg < 0:
        raise ValueError("cfg must be non-negative")
    if diff < 0:
        raise ValueError("diff must be non-negative")
    if max_cfg <= 0:
        raise ValueError("max_cfg must be positive")

    # Hard ceiling first.
    result = min(cfg, max_cfg)

    if mode == "none":
        return result

    # Normalise the difference into a 0..1 "risk" factor.
    # We treat diff=0 as no risk and diff>=1 as full risk.
    risk = _clamp(diff, 0.0, 1.0)

    if mode == "linear":
        # Linearly reduce CFG as risk increases.
        # At risk=0 keep full CFG; at risk=1 keep half of CFG.
        scale = 1.0 - 0.5 * risk
        result *= scale

    elif mode == "sigmoid":
        # Sigmoid-shaped reduction: gentle at low risk, steeper in
        # the middle, saturating at high risk.
        x = _SIGMOID_K * (risk - _SIGMOID_MID)
        s = _sigmoid(x)  # 0..1, 0.5 at risk=0.5
        # Map s to a scale factor in [0.5, 1.0].
        scale = 0.5 + 0.5 * (1.0 - s)
        result *= scale

    # Ensure we never go below a tiny positive floor.
    if result <= 0:
        result = 1e-6

    return result


class PSN_Auto_CFG_Rescale:
    """Rescale a CFG value based on the conditional/unconditional noise difference.

    The ``model`` input/output is a plain STRING token (e.g. the model
    name) so the node can be wired into a ComfyUI graph without
    requiring a real MODEL object. The actual rescaling logic is
    pure-Python and deterministic.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("STRING", {"default": "model"}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 1e9, "step": 0.01}),
                "diff": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.001}),
                "max_cfg": ("FLOAT", {"default": 10.0, "min": 0.001, "max": 1e9, "step": 0.01}),
                "rescale_mode": (list(_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "FLOAT", "STRING")
    RETURN_NAMES = ("model", "rescaled_cfg", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, cfg, diff, max_cfg, rescale_mode):
        """Return the model token, the rescaled CFG, and a human-readable reason."""
        try:
            rescaled = rescale_cfg(cfg, diff, max_cfg, rescale_mode)
        except (ValueError, TypeError) as exc:
            return (model, cfg, f"error: {exc}")

        if rescaled < cfg - 1e-9:
            reason = (
                f"rescaled from {cfg:.4f} to {rescaled:.4f} "
                f"(mode={rescale_mode}, diff={diff:.4f}, max_cfg={max_cfg:.4f})"
            )
        else:
            reason = f"no change (mode={rescale_mode}, diff={diff:.4f})"

        return (model, rescaled, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Auto_CFG_Rescale": PSN_Auto_CFG_Rescale,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Auto_CFG_Rescale": "PSN Auto CFG Rescale",
}
