"""
Gaze-Aware Portrait Enhancement (pure-logic core).

This module implements the *secure, pure-Python* control logic for a
gaze-aware portrait enhancement pipeline. The real pipeline would use
torch/mediapipe/opencv to estimate gaze from pixels and warp the eye
region; those GPU/vision dependencies are intentionally NOT used here.

Instead, this module provides:
  * PSN_GazeEstimator  - validates a numeric 3D gaze vector and a pupil
    position, normalizes the gaze vector, and reports a confidence score.
  * PSN_GazeCorrector  - computes a bounded correction offset from a
    current gaze vector toward a target gaze vector, scaled by a clamped
    strength, and reports whether the correction is safe (not too strong).

All functions take plain values (numbers, lists, strings) and return
plain values. No sockets, no file/OS access, no network, no eval/exec.
"""

import math

CAT = "ParametricStudio/Gaze"

# Allowed magnitude range for a normalized gaze vector (unit-ish).
_MIN_NORM = 0.0
_MAX_NORM = 1.0001

# Maximum allowed correction magnitude before we flag it as unsafe.
_MAX_SAFE_CORRECTION = 0.5


def _is_number(value):
    """Return True if value is a real number (int/float, not bool)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return False


def _clamp(value, lo, hi):
    """Clamp value into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _normalize_vector(vec):
    """
    Normalize a 3D vector to unit length.
    Returns (normalized_list, ok, reason).
    """
    if not isinstance(vec, (list, tuple)):
        return None, False, "gaze vector must be a list or tuple"
    if len(vec) != 3:
        return None, False, "gaze vector must have exactly 3 components"
    for i, c in enumerate(vec):
        if not _is_number(c):
            return None, False, "gaze component %d is not a number" % i
        if isinstance(c, float) and (math.isnan(c) or math.isinf(c)):
            return None, False, "gaze component %d is not finite" % i
    x, y, z = float(vec[0]), float(vec[1]), float(vec[2])
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-9:
        return None, False, "gaze vector is zero (cannot normalize)"
    nx, ny, nz = x / norm, y / norm, z / norm
    return [nx, ny, nz], True, "ok"


def _confidence_from_vector(vec):
    """
    Heuristic confidence: a gaze vector close to unit length and with a
    dominant forward (z) component is considered more confident.
    Returns a float in [0, 1].
    """
    x, y, z = float(vec[0]), float(vec[1]), float(vec[2])
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-9:
        return 0.0
    # How close to unit length (1.0 is best).
    length_score = 1.0 - min(abs(norm - 1.0), 1.0)
    # How forward-facing (z positive and large is best).
    forward_score = _clamp(z / norm, 0.0, 1.0)
    return _clamp(0.5 * length_score + 0.5 * forward_score, 0.0, 1.0)


def _validate_pupil_position(pos):
    """
    Validate a pupil position given as a list/tuple of 2 or 3 ints.
    Returns (pos_list, ok, reason).
    """
    if not isinstance(pos, (list, tuple)):
        return None, False, "pupil position must be a list or tuple"
    if len(pos) not in (2, 3):
        return None, False, "pupil position must have 2 or 3 components"
    out = []
    for i, c in enumerate(pos):
        if isinstance(c, bool) or not isinstance(c, int):
            return None, False, "pupil component %d is not an integer" % i
        out.append(c)
    return out, True, "ok"


def _correction_offset(current, target, strength):
    """
    Compute the correction offset to move `current` gaze toward `target`.
    Both are normalized 3D vectors. Returns (offset_list, magnitude, ok, reason).
    """
    if not isinstance(current, (list, tuple)) or len(current) != 3:
        return None, 0.0, False, "current gaze must be a 3-component vector"
    if not isinstance(target, (list, tuple)) or len(target) != 3:
        return None, 0.0, False, "target gaze must be a 3-component vector"
    if not _is_number(strength):
        return None, 0.0, False, "strength must be a number"
    if isinstance(strength, float) and (math.isnan(strength) or math.isinf(strength)):
        return None, 0.0, False, "strength is not finite"

    strength = _clamp(float(strength), 0.0, 1.0)

    offset = [
        (float(target[0]) - float(current[0])) * strength,
        (float(target[1]) - float(current[1])) * strength,
        (float(target[2]) - float(current[2])) * strength,
    ]
    magnitude = math.sqrt(sum(c * c for c in offset))
    return offset, magnitude, True, "ok"


class PSN_GazeEstimator:
    """
    Validate and normalize a 3D gaze vector and a pupil position.

    In a full pipeline this would run a vision model on an IMAGE tensor.
    Here it accepts the *already-estimated* numeric gaze vector and pupil
    position (as plain values) and returns a normalized gaze vector, the
    validated pupil position, and a confidence score.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gaze_vector": ("STRING", {"default": "0.0, 0.0, 1.0"}),
                "pupil_position": ("STRING", {"default": "512, 384"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("FLOAT", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("GAZE_VECTOR", "PUPIL_POSITION", "CONFIDENCE", "REASON")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, gaze_vector, pupil_position):
        # Parse gaze vector from a comma/space separated string.
        vec, ok, reason = self._parse_vector_string(gaze_vector)
        if not ok:
            return ([0.0, 0.0, 1.0], [0, 0], 0.0, reason)
        normalized, ok, reason = _normalize_vector(vec)
        if not ok:
            return ([0.0, 0.0, 1.0], [0, 0], 0.0, reason)
        confidence = _confidence_from_vector(normalized)

        # Parse pupil position.
        pos, ok, reason = self._parse_pupil_string(pupil_position)
        if not ok:
            return (normalized, [0, 0], 0.0, reason)

        return (normalized, pos, confidence, "ok")

    @staticmethod
    def _parse_vector_string(text):
        if not isinstance(text, str):
            return None, False, "gaze_vector must be a string"
        parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
        if len(parts) != 3:
            return None, False, "gaze_vector must have 3 components"
        out = []
        for i, p in enumerate(parts):
            try:
                out.append(float(p))
            except (ValueError, TypeError):
                return None, False, "gaze component %d is not a number" % i
        return out, True, "ok"

    @staticmethod
    def _parse_pupil_string(text):
        if not isinstance(text, str):
            return None, False, "pupil_position must be a string"
        parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
        if len(parts) not in (2, 3):
            return None, False, "pupil_position must have 2 or 3 components"
        out = []
        for i, p in enumerate(parts):
            try:
                out.append(int(p))
            except (ValueError, TypeError):
                return None, False, "pupil component %d is not an integer" % i
        return out, True, "ok"


class PSN_GazeCorrector:
    """
    Compute a bounded correction offset that moves a current gaze vector
    toward a target gaze vector, scaled by a clamped strength.

    In a full pipeline this would warp the eye region of an IMAGE tensor.
    Here it accepts the current and target gaze vectors (as plain values)
    and returns the correction offset, its magnitude, and whether the
    correction is considered safe (magnitude within a safe bound).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "current_gaze": ("STRING", {"default": "0.0, 0.0, 1.0"}),
                "target_gaze": ("STRING", {"default": "0.0, 0.0, 1.0"}),
                "strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("CORRECTION_OFFSET", "MAGNITUDE", "SAFE", "REASON")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, current_gaze, target_gaze, strength):
        cur, ok, reason = self._parse_vector_string(current_gaze)
        if not ok:
            return ([0.0, 0.0, 0.0], 0.0, False, reason)
        tgt, ok, reason = self._parse_vector_string(target_gaze)
        if not ok:
            return ([0.0, 0.0, 0.0], 0.0, False, reason)

        cur_norm, ok, reason = _normalize_vector(cur)
        if not ok:
            return ([0.0, 0.0, 0.0], 0.0, False, reason)
        tgt_norm, ok, reason = _normalize_vector(tgt)
        if not ok:
            return ([0.0, 0.0, 0.0], 0.0, False, reason)

        offset, magnitude, ok, reason = _correction_offset(cur_norm, tgt_norm, strength)
        if not ok:
            return ([0.0, 0.0, 0.0], 0.0, False, reason)

        safe = magnitude <= _MAX_SAFE_CORRECTION
        if not safe:
            reason = "correction magnitude %.4f exceeds safe bound %.2f" % (magnitude, _MAX_SAFE_CORRECTION)
        return (offset, magnitude, safe, reason)

    @staticmethod
    def _parse_vector_string(text):
        if not isinstance(text, str):
            return None, False, "gaze input must be a string"
        parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
        if len(parts) != 3:
            return None, False, "gaze input must have 3 components"
        out = []
        for i, p in enumerate(parts):
            try:
                out.append(float(p))
            except (ValueError, TypeError):
                return None, False, "gaze component %d is not a number" % i
        return out, True, "ok"


NODE_CLASS_MAPPINGS = {
    "PSN_GazeEstimator": PSN_GazeEstimator,
    "PSN_GazeCorrector": PSN_GazeCorrector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_GazeEstimator": "Gaze Estimator (PSN)",
    "PSN_GazeCorrector": "Gaze Corrector (PSN)",
}
