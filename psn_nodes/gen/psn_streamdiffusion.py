"""PSN_StreamDiffusion: pure-logic state machine for StreamDiffusion-style incremental preview.

This module implements ONLY the secure, pure-Python control logic for a
StreamDiffusion-style real-time preview pipeline. It does NOT perform any
GPU/torch inference, image decoding, or ComfyUI tensor operations. Instead it
manages a JSON-serializable "stream_state" dictionary that tracks the
incremental denoising schedule, caches intermediate activation placeholders,
and validates every step.

The node wrappers take plain values (numbers, strings, JSON text) and return
plain values (numbers, strings, dicts). No sockets, no files, no network, no
subprocess, no eval/exec, no dunder tricks.

Data flow (logical):
    PSN_Stream_Init -> PSN_Stream_Step (looped) -> Preview

The "image" outputs are represented as JSON text describing the current
preview frame (e.g. step index, noise level, activation cache size) so that
downstream pure-logic nodes can consume them without torch.
"""

import json
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Allowed modes for the incremental schedule
_SCHEDULE_MODES = ("linear", "cosine", "exponential")

# Maximum number of cached activation entries to prevent unbounded memory
_MAX_CACHE_ENTRIES = 1024

# Maximum allowed steps to prevent runaway loops
_MAX_STEPS = 1024

# Minimum / maximum guidance scale
_MIN_GUIDANCE = 0.0
_MAX_GUIDANCE = 100.0

# Minimum / maximum steps
_MIN_STEPS = 1
_MAX_STEPS_ALLOWED = 1024

# ---------------------------------------------------------------------------
# Internal helpers (pure logic only)
# ---------------------------------------------------------------------------


def _validate_steps(steps):
    """Validate and clamp steps to a safe integer range."""
    if not isinstance(steps, int):
        raise ValueError("steps must be an integer")
    if steps < _MIN_STEPS or steps > _MAX_STEPS_ALLOWED:
        raise ValueError(
            "steps must be between {} and {}".format(_MIN_STEPS, _MAX_STEPS_ALLOWED)
        )
    return steps


def _validate_guidance(guidance_scale):
    """Validate guidance scale is a finite float in the allowed range."""
    if not isinstance(guidance_scale, (int, float)):
        raise ValueError("guidance_scale must be a number")
    if isinstance(guidance_scale, float) and (math.isnan(guidance_scale) or math.isinf(guidance_scale)):
        raise ValueError("guidance_scale must be a finite number")
    g = float(guidance_scale)
    if g < _MIN_GUIDANCE or g > _MAX_GUIDANCE:
        raise ValueError(
            "guidance_scale must be between {} and {}".format(_MIN_GUIDANCE, _MAX_GUIDANCE)
        )
    return g


def _validate_prompt(prompt):
    """Validate prompt is a non-empty string of reasonable length."""
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    if len(prompt) == 0:
        raise ValueError("prompt must not be empty")
    if len(prompt) > 4096:
        raise ValueError("prompt must be at most 4096 characters")
    return prompt


def _compute_noise_level(step_index, total_steps, mode):
    """Compute the noise level for a given step index using the chosen schedule.

    Returns a float in [0.0, 1.0] where 1.0 is fully noisy and 0.0 is clean.
    """
    if total_steps <= 0:
        raise ValueError("total_steps must be positive")
    if step_index < 0 or step_index >= total_steps:
        raise ValueError("step_index out of range")

    t = step_index / float(total_steps)  # 0.0 .. <1.0

    if mode == "linear":
        return 1.0 - t
    elif mode == "cosine":
        # Cosine schedule: starts high, ends low
        return 0.5 * (1.0 + math.cos(math.pi * t))
    elif mode == "exponential":
        # Exponential decay
        return math.exp(-3.0 * t)
    else:
        raise ValueError("unknown schedule mode: {}".format(mode))


def _make_state(steps, guidance_scale, schedule_mode):
    """Create a fresh stream state dictionary."""
    _validate_steps(steps)
    _validate_guidance(guidance_scale)
    if schedule_mode not in _SCHEDULE_MODES:
        raise ValueError("schedule_mode must be one of {}".format(_SCHEDULE_MODES))

    state = {
        "steps": int(steps),
        "guidance_scale": float(guidance_scale),
        "schedule_mode": schedule_mode,
        "current_step": 0,
        "completed": False,
        "activation_cache": {},
        "history": [],
    }
    return state


def _step_state(state, prompt, image_json=None):
    """Perform one incremental step on the stream state.

    Returns (image_json, updated_state).
    """
    if not isinstance(state, dict):
        raise ValueError("stream_state must be a dict")

    required_keys = {"steps", "guidance_scale", "schedule_mode", "current_step", "completed", "activation_cache", "history"}
    missing = required_keys - set(state.keys())
    if missing:
        raise ValueError("stream_state missing keys: {}".format(sorted(missing)))

    if state["completed"]:
        raise ValueError("stream is already completed; call PSN_Stream_Init to reset")

    prompt = _validate_prompt(prompt)

    current = int(state["current_step"])
    total = int(state["steps"])
    mode = state["schedule_mode"]

    if current >= total:
        raise ValueError("current_step {} >= total steps {}".format(current, total))

    noise_level = _compute_noise_level(current, total, mode)

    # Simulate an activation cache entry (pure placeholder, no torch)
    cache_key = "step_{}".format(current)
    activation_entry = {
        "step": current,
        "noise_level": round(noise_level, 6),
        "prompt_hash": hash(prompt) % (10 ** 9),
        "has_image_input": image_json is not None,
    }

    # Enforce cache size limit
    cache = dict(state["activation_cache"])
    if len(cache) >= _MAX_CACHE_ENTRIES:
        # Evict oldest entry (smallest step key)
        oldest_key = min(cache.keys(), key=lambda k: int(k.split("_")[1]))
        del cache[oldest_key]
    cache[cache_key] = activation_entry

    new_step = current + 1
    completed = new_step >= total

    history = list(state["history"])
    history.append({
        "step": current,
        "noise_level": round(noise_level, 6),
        "prompt": prompt,
    })
    # Keep history bounded
    if len(history) > _MAX_CACHE_ENTRIES:
        history = history[-_MAX_CACHE_ENTRIES:]

    new_state = {
        "steps": total,
        "guidance_scale": float(state["guidance_scale"]),
        "schedule_mode": mode,
        "current_step": new_step,
        "completed": completed,
        "activation_cache": cache,
        "history": history,
    }

    # Build the preview "image" as JSON text (pure logic, no actual pixels)
    image_payload = {
        "step": current,
        "total_steps": total,
        "noise_level": round(noise_level, 6),
        "guidance_scale": float(state["guidance_scale"]),
        "schedule_mode": mode,
        "prompt": prompt,
        "cache_size": len(cache),
        "completed": completed,
    }
    image_json_out = json.dumps(image_payload, sort_keys=True)

    return image_json_out, new_state


# ---------------------------------------------------------------------------
# Node classes
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/StreamDiffusion"


class PSN_Stream_Init:
    """Initialize a StreamDiffusion-style incremental preview state.

    Pure-logic node: creates a JSON-serializable state dict that tracks the
    denoising schedule, guidance scale, and activation cache. No GPU work.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 4, "min": _MIN_STEPS, "max": _MAX_STEPS_ALLOWED, "step": 1}),
                "guidance_scale": ("FLOAT", {"default": 1.0, "min": _MIN_GUIDANCE, "max": _MAX_GUIDANCE, "step": 0.1}),
                "schedule_mode": (list(_SCHEDULE_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("stream_state",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, steps, guidance_scale, schedule_mode):
        state = _make_state(steps, guidance_scale, schedule_mode)
        return (state,)


class PSN_Stream_Step:
    """Perform one incremental denoising step on a StreamDiffusion state.

    Pure-logic node: advances the state by one step, updates the activation
    cache, and returns a JSON-text preview descriptor plus the updated state.
    No GPU work, no actual image pixels.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "stream_state": ("DICT",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "image": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "DICT")
    RETURN_NAMES = ("image", "stream_state")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, stream_state, prompt, image=None):
        image_json, new_state = _step_state(stream_state, prompt, image)
        return (image_json, new_state)


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Stream_Init": PSN_Stream_Init,
    "PSN_Stream_Step": PSN_Stream_Step,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Stream_Init": "PSN Stream Init",
    "PSN_Stream_Step": "PSN Stream Step",
}
