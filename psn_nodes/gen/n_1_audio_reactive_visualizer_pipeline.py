"""
PSN Audio-Reactive Visualizer Pipeline (pure-logic core).

This module implements the *pure-logic, secure-by-design* portion of the
Audio-Reactive Visualizer Pipeline. It does NOT perform real FFT, audio
decoding, or GPU work. Instead it operates on plain Python values:

  * `audio` is supplied as a JSON string containing a list of float samples
    (e.g. "[0.1, -0.2, 0.3, ...]"). This keeps the node free of numpy/scipy
    and file/network I/O.
  * `curve` is supplied as a JSON string containing a list of floats in
    [0, 1] (the amplitude curve produced by the extractor).

The nodes:
  * PSN_Audio_Amplitude_Extractor : parses the sample list, frames it,
    computes per-frame RMS amplitude, normalizes to [0, 1], and returns the
    curve as JSON plus the peak value.
  * PSN_Audio_Reactive_Driver     : parses the curve, applies exponential
    smoothing, maps [0,1] -> [min_val, max_val], and returns the value at a
    given frame index plus the full mapped curve as JSON.

All inputs are plain numbers/strings; no sockets, files, subprocess, or
eval/exec are used.
"""

import json
import math

CAT = "ParametricStudio/AudioReactive"

BANDS = ["low", "mid", "high", "full"]
TARGET_PARAMS = ["scale", "rotation", "brightness", "particle_rate"]


def _psn_parse_float_list(text):
    """Parse a JSON string into a list of floats. Returns (ok, list_or_err)."""
    if text is None:
        return False, "audio/curve input is empty"
    if not isinstance(text, str):
        return False, "input must be a JSON string of numbers"
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return False, "input is not valid JSON"
    if not isinstance(data, list):
        return False, "JSON must be a list of numbers"
    out = []
    for i, v in enumerate(data):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False, "element %d is not a number" % i
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return False, "element %d is not finite" % i
        out.append(fv)
    return True, out


def _psn_rms(samples):
    """Root-mean-square of a list of floats."""
    if not samples:
        return 0.0
    s = 0.0
    for x in samples:
        s += x * x
    return math.sqrt(s / len(samples))


def _psn_frame(samples, window_size, hop_size):
    """Yield overlapping frames of `window_size` stepping by `hop_size`."""
    n = len(samples)
    if window_size <= 0 or hop_size <= 0:
        return
    start = 0
    while start + window_size <= n:
        yield samples[start:start + window_size]
        start += hop_size
    # If a trailing partial frame remains, pad with zeros to window_size.
    if start < n:
        tail = samples[start:]
        tail = tail + [0.0] * (window_size - len(tail))
        yield tail


def _psn_band_rms(frame, band, sample_rate):
    """
    Approximate band-limited RMS without an FFT.

    We use a simple zero-crossing / energy heuristic is not reliable, so
    instead we approximate frequency content by measuring the signal's
    high-frequency energy via first-difference (a crude high-pass) and
    low-frequency energy via the raw signal. This is a pure-logic stand-in
    for a real FFT band extraction.

    - low  : energy of the raw (low-pass-ish) signal
    - high : energy of the first difference (high-pass-ish)
    - mid  : difference between raw and high, clamped
    - full : raw RMS
    """
    raw_rms = _psn_rms(frame)
    if len(frame) < 2:
        diff_rms = 0.0
    else:
        diffs = [frame[i + 1] - frame[i] for i in range(len(frame) - 1)]
        diff_rms = _psn_rms(diffs)

    if band == "full":
        return raw_rms
    if band == "low":
        # Low band: raw energy minus a fraction of high-pass energy.
        return max(0.0, raw_rms - 0.5 * diff_rms)
    if band == "high":
        return diff_rms
    # mid
    return max(0.0, raw_rms - diff_rms)


def _psn_smooth(values, alpha):
    """Exponential moving average. alpha in [0,1]; 0 = no smoothing (raw)."""
    if not values:
        return []
    if alpha <= 0.0:
        return list(values)
    if alpha >= 1.0:
        return [values[0]] * len(values)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * out[-1] + (1.0 - alpha) * v)
    return out


class PSN_Audio_Amplitude_Extractor:
    """Extract a normalized amplitude curve from a JSON list of audio samples."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("STRING", {"default": "[]", "multiline": True}),
                "window_size": ("INT", {"default": 1024, "min": 1, "max": 1 << 20, "step": 1}),
                "hop_size": ("INT", {"default": 512, "min": 1, "max": 1 << 20, "step": 1}),
                "band": (BANDS,),
                "sample_rate": ("INT", {"default": 44100, "min": 1, "max": 1 << 20, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("amplitude_curve", "peak_value")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, audio, window_size, hop_size, band, sample_rate):
        ok, samples = _psn_parse_float_list(audio)
        if not ok:
            return (json.dumps([]), 0.0)

        if window_size <= 0 or hop_size <= 0:
            return (json.dumps([]), 0.0)

        # Require at least one full window of samples to produce a frame.
        if len(samples) < window_size:
            return (json.dumps([]), 0.0)

        frames = list(_psn_frame(samples, window_size, hop_size))
        if not frames:
            return (json.dumps([]), 0.0)

        raw = [_psn_band_rms(f, band, sample_rate) for f in frames]
        peak = max(raw) if raw else 0.0
        if peak > 0.0:
            curve = [v / peak for v in raw]
        else:
            curve = [0.0 for v in raw]

        # Clamp to [0,1]
        curve = [min(1.0, max(0.0, v)) for v in curve]
        return (json.dumps(curve), float(peak))


class PSN_Audio_Reactive_Driver:
    """Map a [0,1] curve to [min_val, max_val] with optional smoothing."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "curve": ("STRING", {"default": "[]", "multiline": True}),
                "target_param": (TARGET_PARAMS,),
                "min_val": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "max_val": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "smoothing": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 1 << 20, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("driven_value", "driven_curve")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, curve, target_param, min_val, max_val, smoothing, frame_index):
        ok, values = _psn_parse_float_list(curve)
        if not ok or not values:
            return (float(min_val), json.dumps([]))

        # Clamp input to [0,1]
        values = [min(1.0, max(0.0, v)) for v in values]

        smoothed = _psn_smooth(values, smoothing)

        span = max_val - min_val
        mapped = [min_val + span * v for v in smoothed]

        idx = frame_index
        if idx < 0:
            idx = 0
        if idx >= len(mapped):
            idx = len(mapped) - 1

        return (float(mapped[idx]), json.dumps(mapped))


NODE_CLASS_MAPPINGS = {
    "PSN_Audio_Amplitude_Extractor": PSN_Audio_Amplitude_Extractor,
    "PSN_Audio_Reactive_Driver": PSN_Audio_Reactive_Driver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Audio_Amplitude_Extractor": "PSN Audio Amplitude Extractor",
    "PSN_Audio_Reactive_Driver": "PSN Audio Reactive Driver",
}
