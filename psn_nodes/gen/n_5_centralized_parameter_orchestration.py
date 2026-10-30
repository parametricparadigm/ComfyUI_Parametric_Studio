"""PSN Param Orchestrator: centralized parameter orchestration for ComfyUI.

Reads model metadata (a dict attached to the model object, or a plain dict
model) and produces a set of generation parameters (CFG, steps, sampler,
scheduler, seed policy) tuned for the requested pipeline type and quality
preset.  The model object is returned unchanged (never modified in place).

Only stdlib + torch are used; no network, no subprocess, no file IO.
"""

import json

import torch

CAT = "ParametricStudio/Orchestration"

# ---------------------------------------------------------------------------
# Parameter tables
# ---------------------------------------------------------------------------

# Base parameters per pipeline type.
_PIPELINE_BASE = {
    "image": {
        "cfg": 7.0,
        "steps": 30,
        "sampler_name": "euler_ancestral",
        "scheduler": "normal",
        "batch_size": 1,
    },
    "video": {
        "cfg": 6.0,
        "steps": 40,
        "sampler_name": "dpmpp_2m",
        "scheduler": "karras",
        "batch_size": 1,
        "frame_count": 16,
        "temporal_cfg_scale": 0.8,
    },
    "3d": {
        "cfg": 8.0,
        "steps": 50,
        "sampler_name": "heun",
        "scheduler": "normal",
        "batch_size": 1,
        "view_count": 6,
    },
}

# Quality multipliers / overrides.
_QUALITY = {
    "fast": {
        "steps_factor": 0.5,
        "cfg_delta": -1.0,
        "sampler_override": "euler",
        "scheduler_override": "simple",
    },
    "high": {
        "steps_factor": 1.5,
        "cfg_delta": 1.0,
        "sampler_override": None,
        "scheduler_override": None,
    },
}

# Model-metadata keys that can influence parameters.
_META_KEYS = ("cfg", "steps", "sampler_name", "scheduler", "pipeline_type")


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _model_metadata(model):
    """Extract a metadata dict from a model object or a plain dict.

    ComfyUI models are typically objects; we look for a ``metadata``
    attribute (dict) or a ``get_metadata`` method.  If the model is
    already a dict we use it directly.  Returns {} on failure.
    """
    if isinstance(model, dict):
        return dict(model)
    meta = getattr(model, "metadata", None)
    if isinstance(meta, dict):
        return dict(meta)
    getter = getattr(model, "get_metadata", None)
    if callable(getter):
        try:
            result = getter()
            if isinstance(result, dict):
                return dict(result)
        except Exception:
            pass
    return {}


def compute_params(pipeline_type, quality, metadata):
    """Pure function: compute the optimized parameter dict.

    Args:
        pipeline_type: one of "image", "video", "3d".
        quality: one of "fast", "high".
        metadata: dict of model metadata (may be empty).

    Returns:
        dict with keys: cfg, steps, sampler_name, scheduler, batch_size,
        pipeline_type, quality, source (str), and any pipeline-specific
        extras.  Values are clamped to sane ranges.
    """
    if pipeline_type not in _PIPELINE_BASE:
        raise ValueError("pipeline_type must be one of %s" % sorted(_PIPELINE_BASE))
    if quality not in _QUALITY:
        raise ValueError("quality must be one of %s" % sorted(_QUALITY))

    base = dict(_PIPELINE_BASE[pipeline_type])
    q = _QUALITY[quality]

    # Start from base, then let metadata override individual keys.
    params = dict(base)
    source = "default"
    for key in _META_KEYS:
        if key in metadata and metadata[key] is not None:
            params[key] = metadata[key]
            source = "model_metadata"

    # Apply quality adjustments.
    steps = int(round(params.get("steps", 30) * q["steps_factor"]))
    steps = _clamp(steps, 1, 512)
    cfg = float(params.get("cfg", 7.0)) + q["cfg_delta"]
    cfg = _clamp(cfg, 1.0, 30.0)

    sampler = q["sampler_override"] or params.get("sampler_name", "euler")
    scheduler = q["scheduler_override"] or params.get("scheduler", "normal")

    params["steps"] = steps
    params["cfg"] = cfg
    params["sampler_name"] = sampler
    params["scheduler"] = scheduler
    params["pipeline_type"] = pipeline_type
    params["quality"] = quality
    params["source"] = source

    return params


def _validate_model(model):
    """Accept a ComfyUI model object or a dict; reject None / bad types."""
    if model is None:
        raise ValueError("model must not be None")
    if isinstance(model, dict):
        return model
    # Accept any object (ComfyUI models are opaque objects).
    return model


class PSN_ParamOrchestrator:
    """Centralized parameter orchestration: adapts CFG, steps, sampler and
    scheduler based on model metadata, pipeline type and quality preset.

    Data flow: MODEL -> PSN_ParamOrchestrator -> KSampler.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "pipeline_type": ("image", "video", "3d"),
                "quality": ("fast", "high"),
            }
        }

    RETURN_TYPES = ("DICT", "MODEL")
    RETURN_NAMES = ("optimized_params", "adjusted_model")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, pipeline_type, quality):
        model = _validate_model(model)
        metadata = _model_metadata(model)
        params = compute_params(pipeline_type, quality, metadata)
        # Return the model unchanged (never modified in place).
        return (params, model)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ParamOrchestrator": PSN_ParamOrchestrator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ParamOrchestrator": "PSN Param Orchestrator",
}
