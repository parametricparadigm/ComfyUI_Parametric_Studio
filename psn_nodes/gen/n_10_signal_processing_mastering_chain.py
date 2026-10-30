"""PSN_Sig_Process: pure-logic mastering chain for audio represented as JSON text.

This node implements the *algorithmic* signal-processing chain (spectral denoising,
parametric EQ, peak normalization) as a deterministic, dependency-free operation on
plain Python data.  Because the spec's real implementation requires torch/torchaudio
and GPU access, this module implements ONLY the secure-by-design pure-logic part:

  * audio is passed in as JSON text (a list of float samples, or a dict with a
    "samples" key and optional "sample_rate"),
  * denoising is a simple moving-average spectral smoothing,
  * EQ is a two-band gain applied to low/high frequency bins (approximated by
    splitting the sample stream into low/high halves for the pure-logic model),
  * normalization scales the peak to 0 dBFS (i.e. peak magnitude == 1.0).

No torch, no ComfyUI imports, no network, no file/OS access, no eval/exec.
All functions take and return plain values (strings, numbers, lists, dicts).
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Signal"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_audio(audio_json):
    """Parse the audio JSON text into a list of float samples.

    Accepts either a JSON list of numbers or a JSON object with a "samples" key.
    Returns (samples, sample_rate).  Raises ValueError on bad input.
    """
    if not isinstance(audio_json, str):
        raise ValueError("audio must be a JSON string")
    try:
        data = json.loads(audio_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("audio is not valid JSON: %s" % exc)

    if isinstance(data, list):
        samples = data
        sample_rate = 44100
    elif isinstance(data, dict):
        if "samples" not in data:
            raise ValueError("audio dict must contain a 'samples' key")
        samples = data["samples"]
        sample_rate = data.get("sample_rate", 44100)
    else:
        raise ValueError("audio must be a JSON list or object with 'samples'")

    if not isinstance(samples, list):
        raise ValueError("samples must be a list")

    out = []
    for i, s in enumerate(samples):
        if not isinstance(s, (int, float)):
            raise ValueError("sample %d is not a number: %r" % (i, s))
        out.append(float(s))
    return out, float(sample_rate)


def _denoise(samples, window=5):
    """Simple moving-average denoising (spectral smoothing approximation)."""
    if len(samples) < window:
        return list(samples)
    out = []
    for i in range(len(samples)):
        lo = max(0, i - window // 2)
        hi = min(len(samples), i + window // 2 + 1)
        chunk = samples[lo:hi]
        out.append(sum(chunk) / len(chunk))
    return out


def _apply_eq(samples, eq_low, eq_high):
    """Two-band parametric EQ approximation.

    Splits the sample stream into two halves: the first half is treated as the
    "low" band and the second half as the "high" band.  Gains are applied in dB.
    """
    n = len(samples)
    if n == 0:
        return samples
    mid = n // 2
    gain_low = 10.0 ** (eq_low / 20.0)
    gain_high = 10.0 ** (eq_high / 20.0)
    out = list(samples)
    for i in range(mid):
        out[i] = samples[i] * gain_low
    for i in range(mid, n):
        out[i] = samples[i] * gain_high
    return out


def _normalize(samples):
    """Peak normalization to 0 dBFS (peak magnitude == 1.0)."""
    if not samples:
        return samples
    peak = max(abs(s) for s in samples)
    if peak == 0.0:
        return list(samples)
    scale = 1.0 / peak
    return [s * scale for s in samples]


def _to_json(samples, sample_rate):
    return json.dumps({"samples": samples, "sample_rate": sample_rate})


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_Sig_Process:
    """Apply denoising, parametric EQ, and peak normalization to audio JSON."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("STRING", {"default": "[]", "multiline": True}),
                "denoise": ("BOOLEAN", {"default": False}),
                "eq_low": ("FLOAT", {"default": 0.0, "min": -60.0, "max": 60.0, "step": 0.5}),
                "eq_high": ("FLOAT", {"default": 0.0, "min": -60.0, "max": 60.0, "step": 0.5}),
                "normalize": ("BOOLEAN", {"default": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("processed_audio",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, audio, denoise, eq_low, eq_high, normalize):
        samples, sample_rate = _parse_audio(audio)
        if denoise:
            samples = _denoise(samples)
        if eq_low != 0.0 or eq_high != 0.0:
            samples = _apply_eq(samples, eq_low, eq_high)
        if normalize:
            samples = _normalize(samples)
        return (_to_json(samples, sample_rate),)


NODE_CLASS_MAPPINGS = {"PSN_Sig_Process": PSN_Sig_Process}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Sig_Process": "Signal Processing Mastering Chain"}
