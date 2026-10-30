"""ParametricStudio - Cinematic Camera Angle Controller.

Maps an integer angle index (0-95) to a predefined cinematic camera angle
description, combines it with distance/tilt/pan parameters, and emits both a
human-readable prompt string and a JSON parameter string for downstream text
encoding or LoRA-based control.
"""

import json

CAT = "ParametricStudio/Camera"

# 96 predefined camera angles (12 elevation bands x 8 azimuth steps).
_ELEVATIONS = [
    "extreme low angle",
    "low angle",
    "slightly low angle",
    "eye level",
    "slightly high angle",
    "high angle",
    "extreme high angle",
    "bird's eye view",
    "worm's eye view",
    "dutch angle",
    "over-the-shoulder",
    "crane shot",
]

_AZIMUTHS = [
    "front-facing",
    "front-left three-quarter",
    "left profile",
    "back-left three-quarter",
    "back-facing",
    "back-right three-quarter",
    "right profile",
    "front-right three-quarter",
]


def _build_angle_table():
    table = []
    for e in _ELEVATIONS:
        for a in _AZIMUTHS:
            table.append("{} {} shot".format(e, a))
    return table


ANGLE_TABLE = _build_angle_table()


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class PSN_Camera_Angle_Controller:
    """Look up a predefined cinematic camera angle and build a prompt + JSON params."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "angle_index": ("INT", {"default": 0, "min": 0, "max": 95}),
                "distance": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 100.0, "step": 0.1}),
                "tilt": ("FLOAT", {"default": 0.0, "min": -90.0, "max": 90.0, "step": 0.5}),
                "pan": ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": 0.5}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("camera_prompt", "camera_params")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, angle_index, distance, tilt, pan):
        idx = int(angle_index)
        if idx < 0 or idx >= len(ANGLE_TABLE):
            raise ValueError("angle_index must be in [0, {}]".format(len(ANGLE_TABLE) - 1))

        distance = float(_clamp(distance, 0.1, 100.0))
        tilt = float(_clamp(tilt, -90.0, 90.0))
        pan = float(_clamp(pan, -180.0, 180.0))

        description = ANGLE_TABLE[idx]

        prompt = (
            "cinematic camera, {desc}, distance {dist:.2f}m, tilt {tilt:.1f} deg, pan {pan:.1f} deg"
        ).format(desc=description, dist=distance, tilt=tilt, pan=pan)

        params = {
            "angle_index": idx,
            "description": description,
            "distance": round(distance, 4),
            "tilt": round(tilt, 4),
            "pan": round(pan, 4),
        }
        params_json = json.dumps(params, sort_keys=True)

        return (prompt, params_json)


NODE_CLASS_MAPPINGS = {
    "PSN_Camera_Angle_Controller": PSN_Camera_Angle_Controller,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Camera_Angle_Controller": "Cinematic Camera Angle Controller",
}
