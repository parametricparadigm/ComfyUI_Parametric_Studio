"""Wave-Driven Motion Synthesis (pure-logic, secure-by-design).

This module implements the deterministic, pure-Python core of the
``PSN_Wave_Motion_Synthesizer`` node. It combines two wave functions using
additive, multiplicative, or amplitude-modulation operations and produces a
deterministic sequence of motion values.

Because the original spec depends on ``numpy`` and a ``keyframed`` library
(which are not part of the Python standard library), this implementation
replaces those with a small, self-contained wave representation and a
standard-library-only evaluator. No GPU, torch, ComfyUI internals, network,
file, or OS access is performed. All functions take plain values (numbers,
strings, JSON text) and return plain values.

A wave is represented as a JSON string with the schema::

    {"type": "sine", "amplitude": 1.0, "frequency": 1.0, "phase": 0.0}

Supported wave types are ``sine`` and ``constant``. The combined wave is
returned as a JSON string describing the operation and its operands, and the
``motion_values`` output is a JSON string containing the per-frame values.
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Wave"

_WAVE_TYPES = ("sine", "constant")
_OPERATIONS = ("add", "multiply", "modulate")


def _parse_wave(wave_text):
    """Parse and validate a wave JSON string.

    Returns a dict with keys ``type``, ``amplitude``, ``frequency``, ``phase``.
    Raises ``ValueError`` on malformed or unsupported input.
    """
    if not isinstance(wave_text, str):
        raise ValueError("wave must be a JSON string")
    try:
        data = json.loads(wave_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("wave is not valid JSON: %s" % exc)
    if not isinstance(data, dict):
        raise ValueError("wave JSON must be an object")
    wtype = data.get("type")
    if wtype not in _WAVE_TYPES:
        raise ValueError("unsupported wave type: %r" % (wtype,))
    amplitude = float(data.get("amplitude", 1.0))
    frequency = float(data.get("frequency", 1.0))
    phase = float(data.get("phase", 0.0))
    if not math.isfinite(amplitude) or not math.isfinite(frequency) or not math.isfinite(phase):
        raise ValueError("wave parameters must be finite numbers")
    return {"type": wtype, "amplitude": amplitude, "frequency": frequency, "phase": phase}


def _wave_value(wave, t):
    """Evaluate a parsed wave at normalized time ``t`` (0..1)."""
    if wave["type"] == "sine":
        return wave["amplitude"] * math.sin(2.0 * math.pi * wave["frequency"] * t + wave["phase"])
    return wave["amplitude"]


def _combine(wave_1, wave_2, operation, num_frames):
    """Combine two parsed waves over ``num_frames`` frames.

    Returns a list of per-frame motion values.
    """
    if num_frames < 1:
        raise ValueError("num_frames must be >= 1")
    values = []
    for i in range(num_frames):
        t = i / float(num_frames)
        v1 = _wave_value(wave_1, t)
        v2 = _wave_value(wave_2, t)
        if operation == "add":
            values.append(v1 + v2)
        elif operation == "multiply":
            values.append(v1 * v2)
        elif operation == "modulate":
            values.append(v1 * (1.0 + v2))
        else:
            raise ValueError("unsupported operation: %r" % (operation,))
    return values


def _combined_wave_json(wave_1, wave_2, operation):
    """Build a JSON string describing the combined wave."""
    return json.dumps({
        "operation": operation,
        "wave_1": wave_1,
        "wave_2": wave_2,
    }, sort_keys=True)


class PSN_Wave_Motion_Synthesizer:
    """Combine two wave functions to create deterministic, wave-driven motion."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wave_1": ("STRING", {"default": '{"type": "sine", "amplitude": 1.0, "frequency": 1.0, "phase": 0.0}'}),
                "wave_2": ("STRING", {"default": '{"type": "sine", "amplitude": 1.0, "frequency": 1.0, "phase": 0.0}'}),
                "operation": (list(_OPERATIONS),),
                "num_frames": ("INT", {"default": 100, "min": 1, "max": 100000, "step": 1}),
            },
            "optional": {
                "current_frame": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT", "STRING")
    RETURN_NAMES = ("combined_wave", "motion_value", "motion_values")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, wave_1, wave_2, operation, num_frames, current_frame=0):
        parsed_1 = _parse_wave(wave_1)
        parsed_2 = _parse_wave(wave_2)
        if operation not in _OPERATIONS:
            raise ValueError("unsupported operation: %r" % (operation,))
        values = _combine(parsed_1, parsed_2, operation, num_frames)
        combined = _combined_wave_json(parsed_1, parsed_2, operation)
        if current_frame < 0 or current_frame >= num_frames:
            current_frame = 0
        motion_value = values[current_frame]
        motion_values_json = json.dumps(values)
        return (combined, motion_value, motion_values_json)


NODE_CLASS_MAPPINGS = {
    "PSN_Wave_Motion_Synthesizer": PSN_Wave_Motion_Synthesizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Wave_Motion_Synthesizer": "Wave Motion Synthesizer",
}
