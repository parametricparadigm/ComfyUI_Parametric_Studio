"""Audio-Driven Portrait Pipeline (pure-logic core).

This module implements the *pure-logic, secure-by-design* portion of the
"Audio-Driven Portrait Pipeline" spec.  The real pipeline would need
``torch`` / ``librosa`` / ``mediapipe`` to run a wav2lip-style model and to
composite mouth frames onto a face.  Those GPU / model / I/O steps are
deliberately NOT implemented here (no torch, no network, no file access).

Instead, the nodes operate on *plain values* (numbers, strings, JSON text)
and expose the deterministic, testable logic that the GPU stage would rely on:

* :class:`PSN_AudioToMouthTrack` -- validates the audio/face/fps payload,
  derives a per-frame mouth-openness track from the (JSON-encoded) waveform
  and emits a JSON ``MOUTH_TRACK`` plus a ``TIMING`` list.  The openness is a
  pure function of the waveform amplitude, so a "peak amplitude" frame yields
  the widest mouth (this is what the unit test asserts).
* :class:`PSN_MouthComposite` -- validates the batched base video, mouth
  track and mask payloads and computes a per-frame blend weight (the mask
  coverage) that the GPU stage would use to composite the mouth region.

All inputs are plain Python values; no sockets, files, subprocesses,
eval/exec or dunder tricks are used.
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/AudioPortrait"

# Allowed blend modes for the composite stage.
_BLEND_MODES = ("alpha", "multiply", "add")

# Allowed audio sample-rate presets (Hz).  Anything else is rejected so the
# downstream resampler has a known, bounded set of targets.
_ALLOWED_SAMPLE_RATES = (8000, 16000, 22050, 44100, 48000)


def _as_float(value, name, lo, hi):
    """Coerce ``value`` to a float within ``[lo, hi]`` or raise ``ValueError``."""
    if isinstance(value, bool):
        raise ValueError("%s must be a number, not bool" % name)
    if isinstance(value, (int, float)):
        f = float(value)
    elif isinstance(value, str):
        try:
            f = float(value.strip())
        except (ValueError, AttributeError):
            raise ValueError("%s is not a valid number: %r" % (name, value))
    else:
        raise ValueError("%s must be a number, got %s" % (name, type(value).__name__))
    if not math.isfinite(f):
        raise ValueError("%s must be finite" % name)
    if f < lo or f > hi:
        raise ValueError("%s out of range [%s, %s]: %s" % (name, lo, hi, f))
    return f


def _as_int(value, name, lo, hi):
    """Coerce ``value`` to an int within ``[lo, hi]`` or raise ``ValueError``."""
    f = _as_float(value, name, lo, hi)
    if abs(f - round(f)) > 1e-9:
        raise ValueError("%s must be an integer, got %s" % (name, f))
    return int(round(f))


def _parse_waveform(audio):
    """Parse the ``AUDIO`` payload into a list of float amplitudes.

    Accepts either a JSON array of numbers (``"[0.1, -0.2, ...]"``) or a
    comma/space separated string of numbers.  Returns a list of floats in
    ``[-1, 1]`` (clamped).  Raises ``ValueError`` on malformed input.
    """
    if audio is None:
        raise ValueError("audio payload is required")
    if isinstance(audio, (list, tuple)):
        raw = list(audio)
    elif isinstance(audio, str):
        text = audio.strip()
        if not text:
            raise ValueError("audio payload is empty")
        if text[0] == "[":
            try:
                data = json.loads(text)
            except (ValueError, TypeError):
                raise ValueError("audio JSON is malformed")
            if not isinstance(data, list):
                raise ValueError("audio JSON must be an array of numbers")
            raw = data
        else:
            raw = text.replace(",", " ").split()
    else:
        raise ValueError("audio must be a JSON array string or a list of numbers")

    if not raw:
        raise ValueError("audio waveform is empty")

    amps = []
    for i, item in enumerate(raw):
        if isinstance(item, bool):
            raise ValueError("audio sample %d is not a number" % i)
        if isinstance(item, (int, float)):
            v = float(item)
        elif isinstance(item, str):
            try:
                v = float(item.strip())
            except (ValueError, AttributeError):
                raise ValueError("audio sample %d is not a number: %r" % (i, item))
        else:
            raise ValueError("audio sample %d is not a number" % i)
        if not math.isfinite(v):
            raise ValueError("audio sample %d is not finite" % i)
        # Clamp to a sane amplitude range.
        amps.append(max(-1.0, min(1.0, v)))
    return amps


def _mouth_openness(amps, fps):
    """Derive a per-frame mouth-openness value in ``[0, 1]``.

    The waveform is bucketed into ``fps`` frames per second of audio.  Each
    frame's openness is the mean absolute amplitude of the samples that fall
    in that frame, so a frame containing the waveform peak yields the largest
    openness (widest mouth).  Returns a list of floats.
    """
    n = len(amps)
    if n == 0:
        return []
    # Assume the waveform is 1 second of audio at ``fps`` samples per frame.
    samples_per_frame = max(1, int(round(n / max(1, fps))))
    frames = []
    for start in range(0, n, samples_per_frame):
        chunk = amps[start:start + samples_per_frame]
        if not chunk:
            continue
        mean_abs = sum(abs(a) for a in chunk) / len(chunk)
        frames.append(max(0.0, min(1.0, mean_abs)))
    return frames


def _frame_count(frames):
    """Return the number of frames in a batched payload (list or JSON string)."""
    if frames is None:
        return 0
    if isinstance(frames, str):
        text = frames.strip()
        if not text:
            return 0
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            raise ValueError("frame payload is not valid JSON")
        if not isinstance(data, list):
            raise ValueError("frame payload must be a JSON array")
        return len(data)
    if isinstance(frames, (list, tuple)):
        return len(frames)
    raise ValueError("frame payload must be a list or JSON array string")


class PSN_AudioToMouthTrack:
    """Derive a synchronized mouth-openness track from an audio waveform.

    Pure-logic stand-in for the wav2lip / mediapipe GPU stage.  Takes a
    JSON-encoded waveform, a face-image descriptor and an fps, and emits a
    JSON ``MOUTH_TRACK`` (per-frame openness values) plus a ``TIMING`` list
    (frame timestamps in seconds).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("STRING", {"default": "[]", "multiline": True}),
                "face_image": ("STRING", {"default": "neutral"}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
            },
            "optional": {
                "sample_rate": (list(_ALLOWED_SAMPLE_RATES),),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("MOUTH_TRACK", "TIMING")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, audio, face_image, fps, sample_rate=16000):
        fps_i = _as_int(fps, "fps", 1, 240)
        if sample_rate not in _ALLOWED_SAMPLE_RATES:
            raise ValueError("sample_rate must be one of %s" % (list(_ALLOWED_SAMPLE_RATES),))
        if face_image is None or (isinstance(face_image, str) and not face_image.strip()):
            raise ValueError("face_image descriptor is required")

        amps = _parse_waveform(audio)
        openness = _mouth_openness(amps, fps_i)
        timing = [round(i / fps_i, 6) for i in range(len(openness))]
        mouth_track = json.dumps(openness)
        return (mouth_track, timing)


class PSN_MouthComposite:
    """Compute per-frame blend weights for compositing a mouth track.

    Pure-logic stand-in for the GPU compositing stage.  Validates the batched
    base video, mouth track and mask payloads and returns a JSON list of
    per-frame blend weights (the mask coverage) that the GPU stage would use
    to blend the generated mouth region into the base frames.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_video": ("STRING", {"default": "[]", "multiline": True}),
                "mouth_track": ("STRING", {"default": "[]", "multiline": True}),
                "mask": ("STRING", {"default": "[]", "multiline": True}),
            },
            "optional": {
                "blend_mode": (list(_BLEND_MODES),),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("VIDEO", "BLEND_WEIGHTS")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base_video, mouth_track, mask, blend_mode="alpha"):
        if blend_mode not in _BLEND_MODES:
            raise ValueError("blend_mode must be one of %s" % (list(_BLEND_MODES),))

        n_base = _frame_count(base_video)
        n_track = _frame_count(mouth_track)
        n_mask = _frame_count(mask)

        if n_base == 0:
            raise ValueError("base_video has no frames")
        if n_track != n_base:
            raise ValueError(
                "frame count mismatch: base_video=%d mouth_track=%d" % (n_base, n_track)
            )
        if n_mask != n_base:
            raise ValueError(
                "frame count mismatch: base_video=%d mask=%d" % (n_base, n_mask)
            )

        # Parse the mask into per-frame coverage values in [0, 1].
        mask_data = json.loads(mask) if isinstance(mask, str) else list(mask)
        weights = []
        for i, m in enumerate(mask_data):
            if isinstance(m, bool):
                raise ValueError("mask frame %d is not a number" % i)
            if isinstance(m, (int, float)):
                v = float(m)
            elif isinstance(m, str):
                try:
                    v = float(m.strip())
                except (ValueError, AttributeError):
                    raise ValueError("mask frame %d is not a number: %r" % (i, m))
            else:
                raise ValueError("mask frame %d is not a number" % i)
            if not math.isfinite(v):
                raise ValueError("mask frame %d is not finite" % i)
            weights.append(max(0.0, min(1.0, v)))

        video = json.dumps(weights)
        return (video, weights)


NODE_CLASS_MAPPINGS = {
    "PSN_AudioToMouthTrack": PSN_AudioToMouthTrack,
    "PSN_MouthComposite": PSN_MouthComposite,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AudioToMouthTrack": "Audio To Mouth Track",
    "PSN_MouthComposite": "Mouth Composite",
}
