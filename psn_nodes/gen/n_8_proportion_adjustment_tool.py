"""PSN Proportion Adjustment Tool (pure-logic core).

This module implements the *pure, secure-by-design* part of the
"Proportion Adjustment Tool" spec.  The original spec depends on
``onnxruntime`` / ``numpy`` and GPU pose tensors, which are NOT used here.
Instead, pose data is represented as plain JSON text (a list of
``{"name": str, "x": float, "y": float}`` keypoints) and all proportion
math is done with the Python standard library only.

No network, file, OS, subprocess, eval/exec, torch or ComfyUI imports are
performed.  The node takes plain values (strings, floats) and returns
plain values (JSON string, float).
"""

import json
import math

CAT = "ParametricStudio/Proportion"

# ---------------------------------------------------------------------------
# Body-type proportion tables.
#
# Each body type maps a *segment* (a pair of named keypoints) to a target
# scale factor relative to the "neutral" body.  A factor > 1 lengthens the
# segment, < 1 shortens it.  The neutral body uses all factors of 1.0.
# ---------------------------------------------------------------------------
_NEUTRAL = {
    "neck": 1.0,
    "left_arm": 1.0,
    "right_arm": 1.0,
    "left_leg": 1.0,
    "right_leg": 1.0,
    "torso": 1.0,
}

_BODY_TYPES = {
    "neutral": dict(_NEUTRAL),
    "slim": {
        "neck": 1.0,
        "left_arm": 0.95,
        "right_arm": 0.95,
        "left_leg": 1.05,
        "right_leg": 1.05,
        "torso": 0.95,
    },
    "muscular": {
        "neck": 1.1,
        "left_arm": 1.15,
        "right_arm": 1.15,
        "left_leg": 1.0,
        "right_leg": 1.0,
        "torso": 1.1,
    },
    "tall": {
        "neck": 1.05,
        "left_arm": 1.05,
        "right_arm": 1.05,
        "left_leg": 1.2,
        "right_leg": 1.2,
        "torso": 1.1,
    },
}

# Map each segment to the (start_keypoint, end_keypoint) names.
_SEGMENTS = {
    "neck": ("neck", "head"),
    "left_arm": ("left_shoulder", "left_hand"),
    "right_arm": ("right_shoulder", "right_hand"),
    "left_leg": ("left_hip", "left_ankle"),
    "right_leg": ("right_hip", "right_ankle"),
    "torso": ("left_shoulder", "left_hip"),
}

# The set of keypoint names we know how to place.
_KNOWN_KEYS = set()
for _a, _b in _SEGMENTS.values():
    _KNOWN_KEYS.add(_a)
    _KNOWN_KEYS.add(_b)


def _dist(ax, ay, bx, by):
    return math.hypot(bx - ax, by - ay)


def _parse_pose(text):
    """Parse pose JSON text into a list of dicts.  Raises ValueError on bad input."""
    if not isinstance(text, str):
        raise ValueError("pose_keypoint must be a JSON string")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("pose_keypoint is not valid JSON: %s" % exc)
    if not isinstance(data, list):
        raise ValueError("pose_keypoint must be a JSON list of keypoints")
    for i, kp in enumerate(data):
        if not isinstance(kp, dict):
            raise ValueError("keypoint %d is not an object" % i)
        if "name" not in kp or not isinstance(kp["name"], str):
            raise ValueError("keypoint %d missing string 'name'" % i)
        for axis in ("x", "y"):
            if axis not in kp:
                raise ValueError("keypoint %d missing '%s'" % (i, axis))
            val = kp[axis]
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError("keypoint %d '%s' is not a number" % (i, axis))
            if not math.isfinite(float(val)):
                raise ValueError("keypoint %d '%s' is not finite" % (i, axis))
    return data


def _index_by_name(keypoints):
    idx = {}
    for kp in keypoints:
        idx[kp["name"]] = kp
    return idx


def _adjust(keypoints, body_type, strength):
    """Return (adjusted_keypoints, metrics) for the given pose and body type."""
    factors = _BODY_TYPES[body_type]
    idx = _index_by_name(keypoints)
    adjusted = [dict(kp) for kp in keypoints]
    adj_idx = {kp["name"]: kp for kp in adjusted}

    total_change = 0.0
    segments_touched = 0

    for seg, (start_name, end_name) in _SEGMENTS.items():
        if start_name not in idx or end_name not in idx:
            continue
        start = idx[start_name]
        end = idx[end_name]
        target = adj_idx[start_name]
        target_end = adj_idx[end_name]

        # The "anchor" is the start point; we move the end point along the
        # direction from start to end to achieve the desired length.
        dx = end["x"] - start["x"]
        dy = end["y"] - start["y"]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue

        factor = factors.get(seg, 1.0)
        # Blend: effective factor = 1 + (factor - 1) * strength
        eff = 1.0 + (factor - 1.0) * strength
        new_length = length * eff

        # Unit direction
        ux = dx / length
        uy = dy / length

        # Move the end point (the second keypoint of the segment)
        target_end["x"] = start["x"] + ux * new_length
        target_end["y"] = start["y"] + uy * new_length

        delta = abs(new_length - length)
        total_change += delta
        segments_touched += 1

    # Metric: average relative change across touched segments, or 0 if none.
    if segments_touched > 0:
        metrics = total_change / segments_touched
    else:
        metrics = 0.0

    return adjusted, metrics


class PSN_ProportionAdjust_Modify:
    """Adjust pose keypoint proportions toward a target body type.

    Pure-logic implementation: pose is plain JSON text, no GPU/torch.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pose_keypoint": ("STRING", {"multiline": True, "default": "[]"}),
                "body_type": (list(_BODY_TYPES.keys()),),
                "adjustment_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("adjusted_pose", "proportion_metrics")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, pose_keypoint, body_type, adjustment_strength):
        keypoints = _parse_pose(pose_keypoint)
        if body_type not in _BODY_TYPES:
            raise ValueError("unknown body_type: %r" % (body_type,))
        if not isinstance(adjustment_strength, (int, float)) or isinstance(adjustment_strength, bool):
            raise ValueError("adjustment_strength must be a number")
        if not math.isfinite(float(adjustment_strength)):
            raise ValueError("adjustment_strength must be finite")
        strength = float(adjustment_strength)
        if strength < 0.0:
            strength = 0.0
        if strength > 2.0:
            strength = 2.0

        adjusted, metrics = _adjust(keypoints, body_type, strength)
        return (json.dumps(adjusted), float(metrics))


NODE_CLASS_MAPPINGS = {
    "PSN_ProportionAdjust_Modify": PSN_ProportionAdjust_Modify,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ProportionAdjust_Modify": "Proportion Adjustment Tool",
}
