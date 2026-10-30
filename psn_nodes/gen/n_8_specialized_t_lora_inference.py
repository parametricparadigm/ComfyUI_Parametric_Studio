"""
PSN Specialized T-LoRA Inference (pure-logic core).

This module implements the *pure-logic, secure-by-design* portion of the
"Specialized T-LoRA Inference" spec. It does NOT touch torch, ComfyUI
internals, GPU, sockets, files, or the network. Instead it provides:

  * PSN_TLora_Timestep_Mask  -- computes the per-step activation strength
    (0.0 .. 1.0) for a T-LoRA adapter given a timestep window and a mask
    type ("linear", "step", "custom"). It also validates the window
    parameters and returns a human-readable reason when the mask is
    degenerate (e.g. start > end, or window outside [0, total_steps]).

The returned per-step strength vector is the exact payload that a real
ComfyUI wrapper would use to scale the adapter weights inside the
denoising loop. The wrapper itself (which would need torch/comfy) is
intentionally out of scope here.

Inputs are plain Python values (ints, floats, strings, lists). No
file, network, subprocess, eval/exec, or dunder tricks are used.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MASK_TYPES: List[str] = ["linear", "step", "custom"]

_CAT: str = "ParametricStudio/TLora"

# Sentinel used to indicate "no custom mask supplied".
_NO_CUSTOM: str = ""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value into [lo, hi] without importing math."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _validate_window(
    start_step: int,
    end_step: int,
    total_steps: int,
) -> Tuple[bool, str]:
    """
    Validate the timestep window.

    Returns (ok, reason). ok is True when the window is usable.
    """
    if total_steps <= 0:
        return False, "total_steps must be a positive integer"
    if start_step < 0:
        return False, "start_step must be >= 0"
    if end_step < 0:
        return False, "end_step must be >= 0"
    if start_step >= total_steps:
        return False, "start_step is beyond total_steps (adapter never active)"
    if end_step >= total_steps:
        return False, "end_step is beyond total_steps (adapter never active)"
    if start_step > end_step:
        return False, "start_step must be <= end_step"
    return True, "ok"


def _linear_strength(
    step: int,
    start_step: int,
    end_step: int,
) -> float:
    """
    Linear ramp: 0.0 before start, ramps 0->1 across [start, end],
    0.0 after end. The ramp is inclusive of both endpoints.
    """
    if step < start_step:
        return 0.0
    if step > end_step:
        return 0.0
    span = end_step - start_step
    if span <= 0:
        # Single-step window: fully active at that step.
        return 1.0
    t = (step - start_step) / float(span)
    return _clamp(t, 0.0, 1.0)


def _step_strength(
    step: int,
    start_step: int,
    end_step: int,
) -> float:
    """Hard step: 1.0 inside [start, end], 0.0 otherwise."""
    if start_step <= step <= end_step:
        return 1.0
    return 0.0


def _custom_strength(
    step: int,
    custom_mask: List[float],
    total_steps: int,
) -> float:
    """
    Use the user-supplied per-step mask. If the mask is shorter than
    total_steps, missing entries default to 0.0. Values are clamped
    to [0, 1].
    """
    if not custom_mask:
        return 0.0
    if step < 0 or step >= len(custom_mask):
        return 0.0
    return _clamp(float(custom_mask[step]), 0.0, 1.0)


def compute_strength_vector(
    start_step: int,
    end_step: int,
    total_steps: int,
    mask_type: str,
    custom_mask: List[float] | None = None,
) -> Tuple[List[float], bool, str]:
    """
    Compute the per-step activation strength for every step in
    [0, total_steps).

    Returns (strengths, ok, reason).
    strengths is a list of length total_steps (or empty if not ok).
    """
    # For "custom" mask type, the start/end window is not used for strength
    # calculation, so we relax the window validation to only check total_steps.
    if mask_type == "custom":
        if total_steps <= 0:
            return [], False, "total_steps must be a positive integer"
        if not custom_mask:
            return [], False, "custom mask type requires a non-empty custom_mask list"
    else:
        ok, reason = _validate_window(start_step, end_step, total_steps)
        if not ok:
            return [], False, reason

    strengths: List[float] = []
    for step in range(total_steps):
        if mask_type == "linear":
            s = _linear_strength(step, start_step, end_step)
        elif mask_type == "step":
            s = _step_strength(step, start_step, end_step)
        elif mask_type == "custom":
            s = _custom_strength(step, custom_mask or [], total_steps)
        else:
            return [], False, f"unknown mask_type: {mask_type!r}"
        strengths.append(s)

    return strengths, True, "ok"


# ---------------------------------------------------------------------------
# ComfyUI-style node
# ---------------------------------------------------------------------------

class PSN_TLora_Timestep_Mask:
    """
    Compute the per-step activation strength for a T-LoRA adapter.

    This is the pure-logic core of the T-LoRA timestep mask. It does NOT
    modify a MODEL or TLORA object (those require torch/comfy). Instead it
    produces the strength vector that a real wrapper would use to scale the
    adapter weights during denoising.

    Inputs:
        start_step   -- first step (inclusive) where the adapter becomes active
        end_step     -- last step (inclusive) where the adapter is active
        total_steps  -- total number of denoising steps
        mask_type    -- "linear", "step", or "custom"
        custom_mask  -- optional list of per-step strengths (for "custom")

    Outputs:
        strengths    -- list of floats, one per step, in [0, 1]
        ok           -- True if the mask is valid and usable
        reason       -- human-readable explanation
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "start_step": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "end_step": ("INT", {"default": 5, "min": 0, "max": 10000, "step": 1}),
                "total_steps": ("INT", {"default": 10, "min": 1, "max": 10000, "step": 1}),
                "mask_type": (_MASK_TYPES,),
            },
            "optional": {
                "custom_mask": ("STRING", {"default": _NO_CUSTOM, "multiline": True}),
            },
        }

    RETURN_TYPES = ("FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("strengths", "ok", "reason")
    FUNCTION = "run"
    CATEGORY = _CAT

    def run(
        self,
        start_step: int,
        end_step: int,
        total_steps: int,
        mask_type: str,
        custom_mask: str = _NO_CUSTOM,
    ) -> Tuple[List[float], bool, str]:
        """
        Compute the per-step strength vector.

        custom_mask is accepted as a JSON-like string of floats
        (e.g. "[0.0, 0.5, 1.0, 1.0, 0.5, 0.0]") to keep the node
        interface simple and avoid passing list types through the
        ComfyUI graph. An empty string means "not supplied".
        """
        parsed_mask: List[float] | None = None
        if mask_type == "custom":
            if not custom_mask or custom_mask.strip() == _NO_CUSTOM:
                return [], False, "custom mask type requires a non-empty custom_mask list"
            try:
                # Parse a simple list of numbers. We avoid json.loads to
                # keep dependencies minimal and to reject anything that is
                # not a flat list of numbers.
                text = custom_mask.strip()
                if not (text.startswith("[") and text.endswith("]")):
                    return [], False, "custom_mask must be a list of numbers, e.g. [0.0, 1.0]"
                inner = text[1:-1].strip()
                if not inner:
                    return [], False, "custom_mask list is empty"
                parts = [p.strip() for p in inner.split(",")]
                parsed_mask = []
                for p in parts:
                    if not p:
                        continue
                    parsed_mask.append(float(p))
                if not parsed_mask:
                    return [], False, "custom_mask list is empty"
            except (ValueError, TypeError):
                return [], False, "custom_mask could not be parsed as a list of numbers"

        strengths, ok, reason = compute_strength_vector(
            start_step=start_step,
            end_step=end_step,
            total_steps=total_steps,
            mask_type=mask_type,
            custom_mask=parsed_mask,
        )
        return strengths, ok, reason


# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS: Dict[str, type] = {
    "PSN_TLora_Timestep_Mask": PSN_TLora_Timestep_Mask,
}

NODE_DISPLAY_NAME_MAPPINGS: Dict[str, str] = {
    "PSN_TLora_Timestep_Mask": "PSN T-LoRA Timestep Mask",
}
