"""
PSN_ScheduledCFG: Pure-logic implementation of a scheduled CFG (Classifier-Free Guidance)
interpolation engine for complex prompts.

This module implements ONLY the pure-logic, secure-by-design part of the spec:
- Parsing and validating a JSON schedule of [step_percent, cfg_value] pairs.
- Interpolating the CFG value at a given step percentage using Linear, Smoothstep,
  or Cosine interpolation.
- No torch, no ComfyUI imports, no network, no file I/O, no GPU access.

The node class PSN_ScheduledCFG takes plain values (strings, floats) and returns
the interpolated CFG value, the parsed schedule, and a status message. In a real
ComfyUI environment, this logic would be wrapped to patch a MODEL object, but here
we expose the core interpolation logic as a standalone node.
"""

import json
import math

# Allowed interpolation modes
_INTERP_MODES = ["Linear", "Smoothstep", "Cosine"]

# Minimum and maximum allowed CFG values
_CFG_MIN = 0.0
_CFG_MAX = 100.0

# Minimum and maximum allowed step percentages
_STEP_MIN = 0.0
_STEP_MAX = 1.0


def _validate_schedule(schedule_json: str):
    """
    Parse and validate a JSON schedule string.
    Returns (schedule_list, error_message).
    schedule_list is a list of (step_percent, cfg_value) tuples, sorted by step_percent.
    error_message is None if valid, otherwise a string describing the error.
    """
    if not isinstance(schedule_json, str):
        return None, "Schedule must be a JSON string."

    try:
        data = json.loads(schedule_json)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"

    if not isinstance(data, list):
        return None, "Schedule must be a JSON array."

    if len(data) < 2:
        return None, "Schedule must contain at least 2 points."

    schedule = []
    for i, point in enumerate(data):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None, f"Point {i} must be a [step_percent, cfg_value] pair."

        step_pct, cfg_val = point

        if not isinstance(step_pct, (int, float)) or isinstance(step_pct, bool):
            return None, f"Point {i}: step_percent must be a number."
        if not isinstance(cfg_val, (int, float)) or isinstance(cfg_val, bool):
            return None, f"Point {i}: cfg_value must be a number."

        step_pct = float(step_pct)
        cfg_val = float(cfg_val)

        if step_pct < _STEP_MIN or step_pct > _STEP_MAX:
            return None, f"Point {i}: step_percent must be between {_STEP_MIN} and {_STEP_MAX}."
        if cfg_val < _CFG_MIN or cfg_val > _CFG_MAX:
            return None, f"Point {i}: cfg_value must be between {_CFG_MIN} and {_CFG_MAX}."

        schedule.append((step_pct, cfg_val))

    # Sort by step_percent
    schedule.sort(key=lambda x: x[0])

    # Check for duplicate step percentages
    for i in range(1, len(schedule)):
        if schedule[i][0] == schedule[i - 1][0]:
            return None, f"Duplicate step_percent at index {i}: {schedule[i][0]}."

    return schedule, None


def _interpolate_linear(t: float) -> float:
    """Linear interpolation: t in [0, 1] -> t."""
    return t


def _interpolate_smoothstep(t: float) -> float:
    """Smoothstep interpolation: t in [0, 1] -> 3t^2 - 2t^3."""
    return 3.0 * t * t - 2.0 * t * t * t


def _interpolate_cosine(t: float) -> float:
    """Cosine interpolation: t in [0, 1] -> (1 - cos(pi * t)) / 2."""
    return (1.0 - math.cos(math.pi * t)) / 2.0


def _get_interpolation_func(mode: str):
    """Return the interpolation function for the given mode."""
    if mode == "Linear":
        return _interpolate_linear
    elif mode == "Smoothstep":
        return _interpolate_smoothstep
    elif mode == "Cosine":
        return _interpolate_cosine
    else:
        raise ValueError(f"Unknown interpolation mode: {mode}")


def compute_cfg_at_step(schedule: list, step_percent: float, mode: str) -> float:
    """
    Compute the CFG value at a given step percentage using the specified interpolation.

    Args:
        schedule: List of (step_percent, cfg_value) tuples, sorted by step_percent.
        step_percent: The current step percentage (0.0 to 1.0).
        mode: Interpolation mode ("Linear", "Smoothstep", "Cosine").

    Returns:
        The interpolated CFG value.
    """
    if not schedule:
        raise ValueError("Schedule must not be empty.")

    # Clamp step_percent to [0, 1]
    step_percent = max(_STEP_MIN, min(_STEP_MAX, step_percent))

    interp_func = _get_interpolation_func(mode)

    # If step_percent is before the first point, return the first cfg value
    if step_percent <= schedule[0][0]:
        return schedule[0][1]

    # If step_percent is after the last point, return the last cfg value
    if step_percent >= schedule[-1][0]:
        return schedule[-1][1]

    # Find the two surrounding points
    for i in range(len(schedule) - 1):
        s0, c0 = schedule[i]
        s1, c1 = schedule[i + 1]
        if s0 <= step_percent <= s1:
            # Compute local t in [0, 1]
            if s1 == s0:
                t = 0.0
            else:
                t = (step_percent - s0) / (s1 - s0)
            t = max(0.0, min(1.0, t))
            # Apply interpolation
            t_interp = interp_func(t)
            # Linearly interpolate between c0 and c1 using t_interp
            return c0 + (c1 - c0) * t_interp

    # Should not reach here, but return last value as fallback
    return schedule[-1][1]


class PSN_ScheduledCFG:
    """
    Applies a custom CFG schedule that varies guidance strength across the sampling process.

    This node takes a JSON schedule of [step_percent, cfg_value] pairs and an interpolation
    mode, and outputs the interpolated CFG value at a given step percentage.

    In a full ComfyUI implementation, this would patch a MODEL object. Here, we expose
    the pure-logic interpolation as a standalone node that takes plain values.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "schedule": ("STRING", {
                    "default": "[[0.0, 7.5], [0.5, 5.0], [1.0, 2.5]]",
                    "multiline": True,
                    "tooltip": "JSON array of [step_percent, cfg_value] pairs, e.g. [[0.0, 7.5], [0.5, 5.0], [1.0, 2.5]]"
                }),
                "interpolation": (_INTERP_MODES,),
                "step_percent": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.001,
                    "tooltip": "Current step percentage (0.0 to 1.0)"
                }),
            },
            "optional": {},
        }

    RETURN_TYPES = ("FLOAT", "STRING", "STRING")
    RETURN_NAMES = ("cfg_value", "parsed_schedule", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/ScheduledCFG"

    def run(self, schedule: str, interpolation: str, step_percent: float):
        """
        Compute the CFG value at the given step percentage.

        Args:
            schedule: JSON string of [step_percent, cfg_value] pairs.
            interpolation: Interpolation mode ("Linear", "Smoothstep", "Cosine").
            step_percent: Current step percentage (0.0 to 1.0).

        Returns:
            Tuple of (cfg_value, parsed_schedule_json, status_message).
        """
        # Validate interpolation mode
        if interpolation not in _INTERP_MODES:
            return (0.0, "[]", f"Error: Unknown interpolation mode '{interpolation}'.")

        # Parse and validate schedule
        parsed_schedule, error = _validate_schedule(schedule)
        if error:
            return (0.0, "[]", f"Error: {error}")

        # Compute CFG value
        try:
            cfg_value = compute_cfg_at_step(parsed_schedule, step_percent, interpolation)
        except Exception as e:
            return (0.0, json.dumps(parsed_schedule), f"Error: {e}")

        # Format parsed schedule as JSON string
        parsed_schedule_json = json.dumps([[s, c] for s, c in parsed_schedule])

        status = f"CFG={cfg_value:.4f} at step={step_percent:.3f} using {interpolation} interpolation."

        return (cfg_value, parsed_schedule_json, status)


NODE_CLASS_MAPPINGS = {
    "PSN_ScheduledCFG": PSN_ScheduledCFG,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ScheduledCFG": "PSN Scheduled CFG",
}
