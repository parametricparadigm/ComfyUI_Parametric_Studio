"""
PSN_Repro_Layer: Pure-logic reproducibility helpers for contest judging.

This module implements the *pure-logic, secure-by-design* portion of the
PSN_Repro_Layer spec. Because the spec requires GPU/torch/ComfyUI internals
(torch.backends.cudnn.deterministic, torch.use_deterministic_algorithms,
comfy.sample, CUDA device pinning), those parts are NOT implemented here.
Instead, this module provides:

  * PSN_Fixed_Seed_Generator: deterministic seed derivation from a base seed
    and batch index, with "deterministic" and "offset" modes.
  * PSN_Batch_Invariant_Sampler: a pure-logic *plan* builder that validates
    sampler parameters and produces a canonical, hashable inference plan
    (seed, steps, cfg, sampler_name, scheduler, device pin, determinism flags)
    that a downstream torch/ComfyUI wrapper could consume. It does NOT touch
    torch, CUDA, or any model/latent tensors.

All functions take plain values (ints, floats, strings) and return plain
values (ints, dicts, strings). No network, no file I/O, no subprocess, no
eval/exec, no torch, no comfy imports.
"""

import hashlib
import json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEED_MODULUS = 2**32  # 32-bit unsigned seed space

_VALID_MODES = ("deterministic", "offset")
_VALID_SAMPLERS = (
    "euler",
    "euler_ancestral",
    "heun",
    "heunpp2",
    "dpm_2",
    "dpm_2_ancestral",
    "lms",
    "dpm_fast",
    "dpm_adaptive",
    "ddim",
    "uni_pc",
    "uni_pc_bh2",
)
_VALID_SCHEDULERS = (
    "normal",
    "karras",
    "exponential",
    "sgm_uniform",
    "simple",
    "ddim_uniform",
)
_VALID_DEVICES = ("cuda:0", "cuda:1", "cpu")


# ---------------------------------------------------------------------------
# Pure-logic helpers
# ---------------------------------------------------------------------------

def _clamp_seed(value):
    """Clamp an integer into the 32-bit unsigned seed space [0, 2**32)."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("seed value must be an int, got %r" % type(value).__name__)
    return value % _SEED_MODULUS


def _validate_positive_int(name, value, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("%s must be an int, got %r" % (name, type(value).__name__))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (name, minimum, value))
    return value


def _validate_float(name, value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be a number, got %r" % (name, type(value).__name__))
    value = float(value)
    if value < minimum or value > maximum:
        raise ValueError("%s must be in [%g, %g], got %g" % (name, minimum, maximum, value))
    return value


def _validate_choice(name, value, allowed):
    if not isinstance(value, str):
        raise TypeError("%s must be a string, got %r" % (name, type(value).__name__))
    if value not in allowed:
        raise ValueError("%s must be one of %s, got %r" % (name, list(allowed), value))
    return value


def _canonical_hash(payload):
    """Produce a stable 16-hex-char fingerprint of a JSON-serialisable payload."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Node 1: PSN_Fixed_Seed_Generator
# ---------------------------------------------------------------------------

class PSN_Fixed_Seed_Generator:
    """
    Generates a deterministic seed from a base seed and batch index.

    Modes:
      * "deterministic": the batch index is ignored; every item in the batch
        receives the same seed (base_seed mod 2**32).
      * "offset": the batch index is added to the base seed (mod 2**32),
        giving each batch item a distinct but reproducible seed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1}),
                "batch_index": ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
                "mode": (list(_VALID_MODES),),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("seed",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Repro"

    def run(self, base_seed, batch_index, mode):
        _validate_choice("mode", mode, _VALID_MODES)
        base = _clamp_seed(base_seed)
        idx = _validate_positive_int("batch_index", batch_index, minimum=0)

        if mode == "deterministic":
            seed = base
        else:  # offset
            seed = (base + idx) % _SEED_MODULUS

        return (seed,)


# ---------------------------------------------------------------------------
# Node 2: PSN_Batch_Invariant_Sampler
# ---------------------------------------------------------------------------

class PSN_Batch_Invariant_Sampler:
    """
    Pure-logic inference-plan builder for batch-invariant, deterministic
    sampling.

    This node does NOT execute sampling. It validates all sampler parameters
    and emits a canonical, hashable *plan* dict that a downstream
    torch/ComfyUI wrapper would use to configure:
      * torch.backends.cudnn.deterministic = True
      * torch.use_deterministic_algorithms(True)
      * CUDA device pinning
      * fixed seed, steps, cfg, sampler, scheduler

    The plan includes a 16-hex fingerprint so callers can verify that two
    invocations with identical inputs produce identical plans.

    Inputs (plain values only; model/conditioning/latent are represented by
    their string identifiers in this pure-logic layer):
      model_id, positive_id, negative_id, latent_id, seed, steps, cfg,
      sampler_name, scheduler, device

    Outputs:
      plan (STRING): JSON-encoded inference plan
      fingerprint (STRING): 16-hex-char stable hash of the plan
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_id": ("STRING", {"default": "model_0", "multiline": False}),
                "positive_id": ("STRING", {"default": "pos_0", "multiline": False}),
                "negative_id": ("STRING", {"default": "neg_0", "multiline": False}),
                "latent_id": ("STRING", {"default": "lat_0", "multiline": False}),
                "seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 1000}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "sampler_name": (list(_VALID_SAMPLERS),),
                "scheduler": (list(_VALID_SCHEDULERS),),
                "device": (list(_VALID_DEVICES),),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("plan", "fingerprint")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Repro"

    def run(self, model_id, positive_id, negative_id, latent_id,
            seed, steps, cfg, sampler_name, scheduler, device):
        # Validate / normalise every field
        for name, val in (
            ("model_id", model_id),
            ("positive_id", positive_id),
            ("negative_id", negative_id),
            ("latent_id", latent_id),
        ):
            if not isinstance(val, str) or not val.strip():
                raise ValueError("%s must be a non-empty string" % name)

        seed_val = _clamp_seed(seed)
        steps_val = _validate_positive_int("steps", steps, minimum=1)
        cfg_val = _validate_float("cfg", cfg, 0.0, 100.0)
        sampler_val = _validate_choice("sampler_name", sampler_name, _VALID_SAMPLERS)
        sched_val = _validate_choice("scheduler", scheduler, _VALID_SCHEDULERS)
        dev_val = _validate_choice("device", device, _VALID_DEVICES)

        plan = {
            "model_id": model_id.strip(),
            "positive_id": positive_id.strip(),
            "negative_id": negative_id.strip(),
            "latent_id": latent_id.strip(),
            "seed": seed_val,
            "steps": steps_val,
            "cfg": cfg_val,
            "sampler_name": sampler_val,
            "scheduler": sched_val,
            "device": dev_val,
            "determinism": {
                "cudnn_deterministic": True,
                "use_deterministic_algorithms": True,
                "batch_invariant": True,
            },
        }

        fp = _canonical_hash(plan)
        plan_json = json.dumps(plan, sort_keys=True, separators=(",", ":"))
        return (plan_json, fp)


# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Fixed_Seed_Generator": PSN_Fixed_Seed_Generator,
    "PSN_Batch_Invariant_Sampler": PSN_Batch_Invariant_Sampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Fixed_Seed_Generator": "PSN Fixed Seed Generator",
    "PSN_Batch_Invariant_Sampler": "PSN Batch Invariant Sampler",
}
