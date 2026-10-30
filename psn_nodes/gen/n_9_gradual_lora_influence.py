"""
PSN_Gradual_LoRA_Apply

Pure-logic implementation of a "gradual LoRA influence" scheduler for ComfyUI.

Because the real node requires torch and ComfyUI internals (LORA tensors,
forward-pass overrides), this module implements ONLY the secure, pure-Python
part:

  * Validation of the frame window (start_frame, end_frame).
  * Evaluation of a strength curve (linear or keyframed) at a given frame.
  * Construction of a JSON-serializable "scheduled LoRA" payload that a
    downstream torch-based node can consume to actually scale the weights.

No torch, no ComfyUI imports, no file/network I/O. All functions take plain
values (ints, floats, strings, lists, dicts) and return plain values.

The node class PSN_Gradual_LoRA_Apply exposes:
  - lora_model   : STRING (JSON text describing the LoRA; placeholder for LORA)
  - strength_curve: STRING (JSON text: either {"type":"linear",...} or
                    {"type":"keyframes","points":[[frame,strength],...]})
  - start_frame  : INT
  - end_frame    : INT

Outputs:
  - scheduled_lora : STRING (JSON text with per-frame strength schedule)
  - status         : STRING ("ok" or an error message)
"""

import json
import math

CAT = "ParametricStudio/LoRA"

# ---------------------------------------------------------------------------
# Curve evaluation helpers (pure logic)
# ---------------------------------------------------------------------------

def _clamp(value, lo, hi):
    """Clamp value into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _evaluate_linear(frame, start_frame, end_frame, start_strength, end_strength):
    """
    Linear interpolation of strength between start_frame and end_frame.
    Outside the window the strength is clamped to the nearest endpoint value.
    """
    if end_frame == start_frame:
        return start_strength
    t = (frame - start_frame) / float(end_frame - start_frame)
    t = _clamp(t, 0.0, 1.0)
    return start_strength + t * (end_strength - start_strength)


def _evaluate_keyframes(frame, points):
    """
    Piecewise-linear interpolation over keyframe points.
    points: list of [frame, strength] pairs, sorted by frame.
    Outside the range, clamp to the first/last keyframe strength.
    """
    if not points:
        return 0.0
    if len(points) == 1:
        return float(points[0][1])
    # Before first keyframe
    if frame <= points[0][0]:
        return float(points[0][1])
    # After last keyframe
    if frame >= points[-1][0]:
        return float(points[-1][1])
    # Find the segment
    for i in range(len(points) - 1):
        f0, s0 = points[i][0], points[i][1]
        f1, s1 = points[i + 1][0], points[i + 1][1]
        if f0 <= frame <= f1:
            if f1 == f0:
                return float(s0)
            t = (frame - f0) / float(f1 - f0)
            return float(s0) + t * (float(s1) - float(s0))
    # Should not reach here, but fallback
    return float(points[-1][1])


def _parse_curve(curve_json):
    """
    Parse the strength_curve JSON string.
    Returns (curve_type, params) where:
      curve_type is "linear" or "keyframes"
      params is a dict with the relevant fields.
    Raises ValueError on bad input.
    """
    if not isinstance(curve_json, str):
        raise ValueError("strength_curve must be a JSON string")
    try:
        data = json.loads(curve_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("strength_curve is not valid JSON: %s" % exc)

    if not isinstance(data, dict):
        raise ValueError("strength_curve JSON must be an object")

    ctype = data.get("type")
    if ctype == "linear":
        start_strength = data.get("start_strength", 0.0)
        end_strength = data.get("end_strength", 1.0)
        if not isinstance(start_strength, (int, float)):
            raise ValueError("start_strength must be a number")
        if not isinstance(end_strength, (int, float)):
            raise ValueError("end_strength must be a number")
        return "linear", {"start_strength": float(start_strength),
                           "end_strength": float(end_strength)}
    elif ctype == "keyframes":
        points = data.get("points")
        if not isinstance(points, list):
            raise ValueError("keyframes curve requires a 'points' list")
        cleaned = []
        for idx, pt in enumerate(points):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise ValueError("each keyframe point must be [frame, strength]")
            f, s = pt
            if not isinstance(f, (int, float)):
                raise ValueError("keyframe frame must be a number")
            if not isinstance(s, (int, float)):
                raise ValueError("keyframe strength must be a number")
            cleaned.append([float(f), float(s)])
        # Sort by frame
        cleaned.sort(key=lambda x: x[0])
        return "keyframes", {"points": cleaned}
    else:
        raise ValueError("strength_curve type must be 'linear' or 'keyframes'")


def _build_schedule(start_frame, end_frame, curve_type, curve_params):
    """
    Build a per-frame strength schedule as a list of [frame, strength] pairs.
    Only frames within [start_frame, end_frame] are included.
    """
    schedule = []
    for frame in range(int(start_frame), int(end_frame) + 1):
        if curve_type == "linear":
            strength = _evaluate_linear(
                frame, start_frame, end_frame,
                curve_params["start_strength"],
                curve_params["end_strength"]
            )
        else:
            strength = _evaluate_keyframes(frame, curve_params["points"])
        schedule.append([frame, round(strength, 6)])
    return schedule


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

class PSN_Gradual_LoRA_Apply:
    """
    Schedule LoRA strength over a frame range using a linear or keyframed curve.

    Outputs a JSON payload describing the per-frame strength schedule that a
    downstream torch-based node can use to scale LoRA weights during sampling.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lora_model": ("STRING", {"default": "", "multiline": True}),
                "strength_curve": ("STRING", {
                    "default": '{"type":"linear","start_strength":0.0,"end_strength":1.0}',
                    "multiline": True,
                }),
                "start_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "end_frame": ("INT", {"default": 99, "min": 0, "max": 100000, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("scheduled_lora", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, lora_model, strength_curve, start_frame, end_frame):
        # Validate frame window
        if start_frame < 0:
            return ("", "error: start_frame must be >= 0")
        if end_frame < 0:
            return ("", "error: end_frame must be >= 0")
        if start_frame > end_frame:
            return ("", "error: start_frame must be <= end_frame")

        # Parse curve
        try:
            curve_type, curve_params = _parse_curve(strength_curve)
        except ValueError as exc:
            return ("", "error: %s" % exc)

        # Build schedule
        schedule = _build_schedule(start_frame, end_frame, curve_type, curve_params)

        # Build output payload
        payload = {
            "lora_model": lora_model,
            "start_frame": int(start_frame),
            "end_frame": int(end_frame),
            "curve_type": curve_type,
            "schedule": schedule,
        }

        return (json.dumps(payload), "ok")


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Gradual_LoRA_Apply": PSN_Gradual_LoRA_Apply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Gradual_LoRA_Apply": "Gradual LoRA Influence",
}
