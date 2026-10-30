"""PSN_RESFastSampler — pure-logic core for a RES-style fast sampler.

The real RES sampler needs torch/GPU (denoising a latent over N steps), which is
out of scope here. This module implements ONLY the secure, deterministic,
pure-logic parts that a RES fast-sampler needs, as plain-value functions and a
node wrapper that takes numbers/strings (no tensors, no torch, no ComfyUI
internals, no I/O):

  * plan_res_steps(steps)   -> the RES step schedule (a list of sigma values).
  * res_quality_risk(steps) -> a quality-risk report for low step counts.
  * derive_latent_seed(...) -> a deterministic seed for the latent.
  * build_res_payload(...)  -> a JSON-serializable description of a RES run.

The node returns the planned schedule, the risk report, and a derived seed so a
downstream (GPU) node can perform the actual sampling.
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Sampling"

# RES is tuned for low step counts; below this the quality risk is high.
RES_MIN_STEPS = 10
RES_MAX_STEPS = 200
RES_DEFAULT_STEPS = 20


def _clamp_int(value, lo, hi):
    """Coerce a plain value to an int clamped into [lo, hi]."""
    try:
        iv = int(value)
    except (TypeError, ValueError):
        iv = lo
    if iv < lo:
        iv = lo
    elif iv > hi:
        iv = hi
    return iv


def plan_res_steps(steps):
    """Build the RES step schedule for a given step count.

    Returns a dict with:
      steps: the (clamped) integer step count actually used
      sigmas: a list of descending sigma values, one per step (last is 0.0)
      schedule: "res"
    """
    n = _clamp_int(steps, RES_MIN_STEPS, RES_MAX_STEPS)
    # RES uses a linear sigma ramp from 1.0 down to 0.0 across n steps.
    sigmas = [round(1.0 - i / n, 6) for i in range(n)]
    sigmas[-1] = 0.0
    return {"steps": n, "sigmas": sigmas, "schedule": "res"}


def res_quality_risk(steps):
    """Report the quality risk for a given step count.

    Returns (ok, reason) where ok is False when steps is below RES_MIN_STEPS.
    """
    n = _clamp_int(steps, 1, RES_MAX_STEPS)
    if n < RES_MIN_STEPS:
        return (False, "steps below RES minimum (%d); expect quality drop" % RES_MIN_STEPS)
    if n <= RES_DEFAULT_STEPS:
        return (True, "fast-preview range; acceptable quality")
    return (True, "standard range; full quality")


def derive_latent_seed(seed, steps, cfg):
    """Derive a deterministic latent seed from the run parameters.

    Uses a simple, stable FNV-1a hash over the parameter string so the same
    inputs always yield the same seed (no randomness, no I/O).
    """
    key = "res|%d|%s" % (_clamp_int(steps, RES_MIN_STEPS, RES_MAX_STEPS),
                         repr(float(cfg)))
    h = 0xcbf29ce484222325
    for ch in key:
        h ^= ord(ch)
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    base = _clamp_int(seed, 0, 2**32 - 1)
    return (base + h) % (2**32)


def build_res_payload(steps, cfg, seed):
    """Assemble a JSON-serializable description of a RES run (no tensors)."""
    plan = plan_res_steps(steps)
    ok, reason = res_quality_risk(steps)
    return {
        "schedule": "res",
        "steps": plan["steps"],
        "sigmas": plan["sigmas"],
        "cfg": float(cfg),
        "seed": derive_latent_seed(seed, steps, cfg),
        "quality_ok": ok,
        "quality_reason": reason,
    }


class PSN_RESFastSampler:
    """Plan a RES fast-sampling run (pure logic; no GPU/torch)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": RES_DEFAULT_STEPS, "min": 1, "max": RES_MAX_STEPS, "step": 1}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0, "step": 0.1}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "BOOLEAN")
    RETURN_NAMES = ("payload", "schedule_json", "latent_seed", "quality_ok")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, steps, cfg, seed=0):
        payload = build_res_payload(steps, cfg, seed)
        schedule_json = json.dumps(payload["sigmas"])
        return (json.dumps(payload), schedule_json, payload["seed"], payload["quality_ok"])


NODE_CLASS_MAPPINGS = {"PSN_RESFastSampler": PSN_RESFastSampler}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_RESFastSampler": "RES Fast Sampler (logic)"}
