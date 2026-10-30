"""
PSN_Iterative_Morphing_Engine

Pure-logic implementation of a Deforum-style iterative morphing engine.
This module computes the motion curve (wave function) and per-frame morph
parameters without touching GPU tensors, images, or any I/O.

Inputs are plain numbers/strings; outputs are plain lists/strings.
The actual image warping/blur/color-shift is left to the ComfyUI runtime;
this node only produces the deterministic motion schedule and a compact
JSON summary that a downstream node can consume.

Wave functions supported: sine, triangle, saw, beat.
"""

import json
import math

# ---------------------------------------------------------------------------
# Wave function helpers (pure math, stdlib only)
# ---------------------------------------------------------------------------

_WAVE_MODES = ["sine", "triangle", "saw", "beat"]


def _wave_value(mode: str, phase: float) -> float:
    """Return the wave value in [-1, 1] for a given mode and phase (radians)."""
    if mode == "sine":
        return math.sin(phase)
    if mode == "triangle":
        # Triangle wave: period 2*pi, amplitude 1
        # Map phase to [0, 2*pi)
        p = phase % (2.0 * math.pi)
        if p < math.pi:
            return (2.0 / math.pi) * p - 1.0
        else:
            return 3.0 - (2.0 / math.pi) * p
    if mode == "saw":
        # Sawtooth wave: period 2*pi, ramps from -1 to 1
        p = phase % (2.0 * math.pi)
        return (p / math.pi) - 1.0
    if mode == "beat":
        # Beat: |sin(phase)| shaped pulse, always non-negative, scaled to [-1,1]
        return abs(math.sin(phase)) * 2.0 - 1.0
    raise ValueError(f"Unknown wave mode: {mode!r}")


def _build_motion_curve(
    wave_function: str,
    frequency: float,
    amplitude: float,
    num_frames: int,
) -> list:
    """
    Build the motion curve as a list of (frame_index, wave_value) tuples.
    wave_value is in [-1, 1] * amplitude.
    """
    if wave_function not in _WAVE_MODES:
        raise ValueError(f"wave_function must be one of {_WAVE_MODES}, got {wave_function!r}")
    if num_frames < 1:
        raise ValueError("num_frames must be >= 1")
    if frequency < 0:
        raise ValueError("frequency must be >= 0")
    if amplitude < 0:
        raise ValueError("amplitude must be >= 0")

    curve = []
    for i in range(num_frames):
        # phase advances by frequency * 2*pi per frame
        phase = frequency * 2.0 * math.pi * i
        raw = _wave_value(wave_function, phase)
        curve.append((i, raw * amplitude))
    return curve


def _compute_morph_params(
    motion_curve: list,
    motion_strength: float,
) -> list:
    """
    For each frame, compute the morph operation parameters.
    Returns a list of dicts with keys:
      frame, wave_value, warp_amount, blur_amount, color_shift
    All scaled by motion_strength.
    """
    if motion_strength < 0:
        raise ValueError("motion_strength must be >= 0")

    params = []
    for frame_idx, wave_val in motion_curve:
        # Distribute motion_strength across three sub-operations
        # warp: 50%, blur: 30%, color_shift: 20%
        warp = abs(wave_val) * motion_strength * 0.5
        blur = abs(wave_val) * motion_strength * 0.3
        color_shift = wave_val * motion_strength * 0.2  # signed
        params.append({
            "frame": frame_idx,
            "wave_value": wave_val,
            "warp_amount": warp,
            "blur_amount": blur,
            "color_shift": color_shift,
        })
    return params


def _curve_to_json(motion_curve: list) -> str:
    """Serialize motion curve to a compact JSON string."""
    return json.dumps([{"frame": f, "value": round(v, 6)} for f, v in motion_curve])


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/Morphing"


class PSN_Iterative_Morphing_Engine:
    """
    Generates a Deforum-style iterative morphing schedule.

    Pure-logic node: computes the wave-based motion curve and per-frame
    morph parameters (warp, blur, color shift) as plain data. No image
    tensors, no GPU, no I/O. Downstream nodes consume the JSON summary
    and the parameter list to perform the actual pixel operations.

    Inputs:
      wave_function : one of sine, triangle, saw, beat
      frequency     : cycles per frame (>= 0)
      amplitude     : wave amplitude (>= 0)
      num_frames    : number of frames (>= 1)
      motion_strength : overall morph intensity (>= 0)

    Outputs:
      motion_curve_json : JSON string of the wave curve
      morph_params_json : JSON string of per-frame morph parameters
      frame_count       : number of frames
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wave_function": (_WAVE_MODES,),
                "frequency": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 10.0, "step": 0.001}),
                "amplitude": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "num_frames": ("INT", {"default": 10, "min": 1, "max": 10000, "step": 1}),
                "motion_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("motion_curve_json", "morph_params_json", "frame_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        wave_function: str,
        frequency: float,
        amplitude: float,
        num_frames: int,
        motion_strength: float,
    ):
        # Validate inputs
        if wave_function not in _WAVE_MODES:
            raise ValueError(f"wave_function must be one of {_WAVE_MODES}, got {wave_function!r}")
        if frequency < 0:
            raise ValueError("frequency must be >= 0")
        if amplitude < 0:
            raise ValueError("amplitude must be >= 0")
        if num_frames < 1:
            raise ValueError("num_frames must be >= 1")
        if motion_strength < 0:
            raise ValueError("motion_strength must be >= 0")

        curve = _build_motion_curve(wave_function, frequency, amplitude, num_frames)
        params = _compute_morph_params(curve, motion_strength)

        curve_json = _curve_to_json(curve)
        params_json = json.dumps(params)

        return (curve_json, params_json, num_frames)


# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Iterative_Morphing_Engine": PSN_Iterative_Morphing_Engine,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Iterative_Morphing_Engine": "PSN Iterative Morphing Engine",
}
