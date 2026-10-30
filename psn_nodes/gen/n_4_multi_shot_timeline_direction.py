"""
PSN Multi-Shot Timeline Direction nodes.

This module implements the pure-logic, secure-by-design parts of the
"Multi-Shot Timeline Direction" spec. It does NOT touch GPU/torch/ComfyUI
internals, and it performs no network, file, OS, subprocess, or eval/exec
operations. It only manipulates plain Python values (strings, numbers,
lists, dicts) and JSON text.

- PSN_TimelineDirector: parses a JSON scene list, validates it, merges
  per-scene camera/energy curves into a unified per-frame schedule, and
  reports scene boundaries.
- PSN_SceneTransition: computes the per-frame blend weights for a
  transition (cut / fade / dissolve) between two scenes. The actual image
  interpolation is left to a downstream GPU node; this node only produces
  the numeric weights and a description of the transition.

All public functions take plain values and return plain values.
"""

import json
import math

CAT = "ParametricStudio/Timeline"

# Allowed transition types for the transition node.
_TRANSITION_TYPES = ("cut", "fade", "dissolve")

# Allowed curve shapes for camera_curve / energy_curve.
_CURVE_SHAPES = ("linear", "ease_in", "ease_out", "ease_in_out", "hold")


def _clamp(value, lo, hi):
    """Clamp a number into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _curve_value(shape, t):
    """
    Evaluate a normalized curve shape at t in [0, 1].

    Returns a float in [0, 1].
    """
    t = _clamp(t, 0.0, 1.0)
    if shape == "linear":
        return t
    if shape == "ease_in":
        return t * t
    if shape == "ease_out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if shape == "ease_in_out":
        # Smoothstep.
        return t * t * (3.0 - 2.0 * t)
    if shape == "hold":
        # Hold at 0 until the very end, then jump to 1.
        return 0.0 if t < 1.0 else 1.0
    raise ValueError("Unknown curve shape: %r" % (shape,))


def _parse_scene(scene, index):
    """
    Validate and normalize a single scene dict.

    Returns a dict with keys:
      start_frame (int), end_frame (int), camera_curve (str), energy_curve (str)
    """
    if not isinstance(scene, dict):
        raise ValueError("Scene %d must be an object" % index)

    if "start_frame" not in scene or "end_frame" not in scene:
        raise ValueError("Scene %d missing start_frame or end_frame" % index)

    start = scene["start_frame"]
    end = scene["end_frame"]

    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError("Scene %d start_frame must be an int" % index)
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError("Scene %d end_frame must be an int" % index)
    if start < 0:
        raise ValueError("Scene %d start_frame must be >= 0" % index)
    if end <= start:
        raise ValueError("Scene %d end_frame must be > start_frame" % index)

    camera_curve = scene.get("camera_curve", "linear")
    energy_curve = scene.get("energy_curve", "linear")

    if not isinstance(camera_curve, str) or camera_curve not in _CURVE_SHAPES:
        raise ValueError(
            "Scene %d camera_curve must be one of %s" % (index, list(_CURVE_SHAPES))
        )
    if not isinstance(energy_curve, str) or energy_curve not in _CURVE_SHAPES:
        raise ValueError(
            "Scene %d energy_curve must be one of %s" % (index, list(_CURVE_SHAPES))
        )

    return {
        "start_frame": start,
        "end_frame": end,
        "camera_curve": camera_curve,
        "energy_curve": energy_curve,
    }


def _build_schedule(scenes, total_frames):
    """
    Build a per-frame schedule from validated scenes.

    Returns:
      schedule: list of dicts, one per frame in [0, total_frames), each with
                keys 'camera' and 'energy' (floats in [0, 1]) and 'scene_index'.
      boundaries: sorted list of frame indices where a scene starts
                  (excluding frame 0 if it is the first scene start).
    """
    schedule = []
    boundaries = []

    for scene_index, scene in enumerate(scenes):
        start = scene["start_frame"]
        end = scene["end_frame"]
        if scene_index > 0:
            boundaries.append(start)

        span = end - start
        for frame in range(start, min(end, total_frames)):
            if span <= 1:
                t = 1.0
            else:
                t = (frame - start) / float(span - 1)
            camera = _curve_value(scene["camera_curve"], t)
            energy = _curve_value(scene["energy_curve"], t)
            schedule.append(
                {
                    "frame": frame,
                    "camera": camera,
                    "energy": energy,
                    "scene_index": scene_index,
                }
            )

    # Fill any gaps up to total_frames with the last scene's end values.
    if scenes:
        last_scene = scenes[-1]
        last_camera = _curve_value(last_scene["camera_curve"], 1.0)
        last_energy = _curve_value(last_scene["energy_curve"], 1.0)
        last_index = len(scenes) - 1
        while len(schedule) < total_frames:
            frame = len(schedule)
            schedule.append(
                {
                    "frame": frame,
                    "camera": last_camera,
                    "energy": last_energy,
                    "scene_index": last_index,
                }
            )

    boundaries = sorted(set(boundaries))
    return schedule, boundaries


def _transition_weights(transition_type, duration):
    """
    Compute per-frame blend weights for a transition.

    Returns a list of length `duration` where each element is a float in
    [0, 1] representing the weight of scene_b (the incoming scene). The
    weight of scene_a is 1 - w.

    - cut: instant switch; all frames are scene_b (weight 1.0).
    - fade: linear ramp from 0 to 1.
    - dissolve: smoothstep ramp from 0 to 1.
    """
    if transition_type not in _TRANSITION_TYPES:
        raise ValueError("Unknown transition type: %r" % (transition_type,))
    if duration <= 0:
        raise ValueError("duration must be a positive integer")

    weights = []
    for i in range(duration):
        if duration == 1:
            t = 1.0
        else:
            t = i / float(duration - 1)
        if transition_type == "cut":
            w = 1.0
        elif transition_type == "fade":
            w = t
        else:  # dissolve
            w = t * t * (3.0 - 2.0 * t)
        weights.append(_clamp(w, 0.0, 1.0))
    return weights


class PSN_TimelineDirector:
    """
    Parse a JSON scene list and merge per-scene camera/energy curves into a
    unified per-frame timeline schedule. Reports scene boundaries.

    Pure-logic node: no GPU, no file I/O, no network.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scenes": ("STRING", {"default": "[]", "multiline": True}),
                "total_frames": ("INT", {"default": 100, "min": 1, "max": 100000, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("timeline_schedule", "scene_boundaries")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, scenes, total_frames):
        """
        Returns:
          timeline_schedule: JSON string of the per-frame schedule.
          scene_boundaries:  JSON string of the list of boundary frame indices.
        """
        if not isinstance(scenes, str):
            raise ValueError("scenes must be a JSON string")
        if not isinstance(total_frames, int) or isinstance(total_frames, bool):
            raise ValueError("total_frames must be an int")
        if total_frames <= 0:
            raise ValueError("total_frames must be > 0")

        try:
            raw = json.loads(scenes)
        except json.JSONDecodeError as exc:
            raise ValueError("scenes is not valid JSON: %s" % exc)

        if not isinstance(raw, list):
            raise ValueError("scenes JSON must be a list of scene objects")

        parsed = [_parse_scene(s, i) for i, s in enumerate(raw)]

        # Sort by start_frame for deterministic ordering.
        parsed.sort(key=lambda s: s["start_frame"])

        # Validate no overlaps.
        for i in range(1, len(parsed)):
            if parsed[i]["start_frame"] < parsed[i - 1]["end_frame"]:
                raise ValueError(
                    "Scene %d overlaps with scene %d" % (i, i - 1)
                )

        schedule, boundaries = _build_schedule(parsed, total_frames)

        schedule_json = json.dumps(schedule)
        boundaries_json = json.dumps(boundaries)
        return (schedule_json, boundaries_json)


class PSN_SceneTransition:
    """
    Compute per-frame blend weights for a transition between two scenes.

    Pure-logic node: produces numeric weights and a description; the actual
    image interpolation is left to a downstream GPU node.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "transition_type": (list(_TRANSITION_TYPES),),
                "duration": ("INT", {"default": 10, "min": 1, "max": 10000, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("transition_weights", "transition_description")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, transition_type, duration):
        """
        Returns:
          transition_weights: JSON string of a list of floats (weight of
                              scene_b per frame).
          transition_description: human-readable description.
        """
        if not isinstance(transition_type, str) or transition_type not in _TRANSITION_TYPES:
            raise ValueError("transition_type must be one of %s" % (list(_TRANSITION_TYPES),))
        if not isinstance(duration, int) or isinstance(duration, bool):
            raise ValueError("duration must be an int")
        if duration <= 0:
            raise ValueError("duration must be > 0")

        weights = _transition_weights(transition_type, duration)
        weights_json = json.dumps(weights)
        description = (
            "Transition '%s' over %d frames; weight of scene_b per frame: %s"
            % (transition_type, duration, weights_json)
        )
        return (weights_json, description)


NODE_CLASS_MAPPINGS = {
    "PSN_TimelineDirector": PSN_TimelineDirector,
    "PSN_SceneTransition": PSN_SceneTransition,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TimelineDirector": "PSN Timeline Director",
    "PSN_SceneTransition": "PSN Scene Transition",
}
