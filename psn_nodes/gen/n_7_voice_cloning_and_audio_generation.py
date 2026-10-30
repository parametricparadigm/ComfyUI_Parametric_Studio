"""ParametricStudio - Voice Cloning and Audio Generation (torch/stdlib core).

Implements the core of the idea using only torch (CPU) and the standard
library.  Real neural TTS / speaker-embedding inference (onnxruntime,
librosa, etc.) is NOT implemented because those packages are not available
in this environment.  Instead:

* PSN_Load_Voice_Reference derives a deterministic, hash-based speaker
  embedding from the reference audio path + speaker id.  The embedding is a
  small float tensor that downstream nodes can use to modulate synthesis.
* PSN_Generate_Speech synthesises a simple formant-like waveform from the
  text and the voice embedding.  The output is a ComfyUI AUDIO tuple
  (waveform tensor [1, samples, channels], sample_rate int).

No network, no subprocess, no file I/O, no third-party audio libraries.
"""

import hashlib
import math

import torch

CAT = "ParametricStudio/Voice"

# Fixed embedding dimensionality for the (mock) speaker embedding.
EMBED_DIM = 32

# Default sample rate for the generated audio.
SAMPLE_RATE = 22050

# Approximate seconds of audio per character of text (used to size output).
SECONDS_PER_CHAR = 0.06

# Minimum / maximum seconds of generated audio.
MIN_SECONDS = 0.1
MAX_SECONDS = 30.0


def _hash_to_seed(text: str) -> int:
    """Deterministic 64-bit hash of a string, used as a PRNG seed."""
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def _make_embedding(audio_path: str, speaker_id: str) -> torch.Tensor:
    """Build a deterministic pseudo speaker-embedding from the inputs.

    In a real implementation this would run a speaker-verification model
    (e.g. ECAPA-TDNN) over the reference audio.  Here we derive a stable
    vector from the path + id so that the same reference always yields the
    same embedding, and different references yield different embeddings.
    """
    key = f"{audio_path}::{speaker_id}"
    seed = _hash_to_seed(key)
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)
    # Draw a unit-norm vector in EMBED_DIM space.
    v = torch.randn(EMBED_DIM, generator=g)
    v = v / (v.norm() + 1e-8)
    return v


def _clamp_speed(speed: float) -> float:
    """Clamp speed to a sane range."""
    return max(0.25, min(4.0, float(speed)))


def _text_to_phoneme_weights(text: str) -> torch.Tensor:
    """Map text characters to a sequence of scalar weights in [0, 1].

    This is a very rough stand-in for a text-to-phoneme front-end.  Each
    character is mapped to a value derived from its unicode code point.
    Whitespace and punctuation produce near-zero energy (silence).
    """
    weights = []
    for ch in text:
        if ch.isspace() or ch in ".,!?;:\"'()[]{}-—…":
            weights.append(0.05)
        else:
            # Deterministic pseudo-random weight in [0.2, 1.0].
            h = _hash_to_seed(ch)
            weights.append(0.2 + 0.8 * ((h % 1000) / 1000.0))
    if not weights:
        weights = [0.0]
    return torch.tensor(weights, dtype=torch.float32)


def _synthesize(text: str, embedding: torch.Tensor, speed: float) -> torch.Tensor:
    """Generate a simple formant-like waveform.

    Returns a tensor of shape [1, num_samples, 1] (mono).
    """
    speed = _clamp_speed(speed)
    weights = _text_to_phoneme_weights(text)
    n_chars = weights.shape[0]

    # Duration scales with text length and inversely with speed.
    duration = max(MIN_SECONDS, min(MAX_SECONDS, n_chars * SECONDS_PER_CHAR / speed))
    n_samples = int(duration * SAMPLE_RATE)
    n_samples = max(n_samples, SAMPLE_RATE // 10)  # at least 100 ms

    t = torch.linspace(0.0, duration, n_samples, dtype=torch.float32)

    # Base fundamental frequency modulated by the first few embedding dims.
    f0 = 120.0 + 80.0 * (embedding[0].item() + 1.0) / 2.0  # ~120-200 Hz
    f1 = 500.0 + 300.0 * (embedding[1].item() + 1.0) / 2.0  # first formant
    f2 = 1200.0 + 600.0 * (embedding[2].item() + 1.0) / 2.0  # second formant

    # Per-character amplitude envelope.
    # Each character occupies duration/n_chars seconds.
    char_dur = duration / n_chars
    char_idx = (t / char_dur).long().clamp(0, n_chars - 1)
    env = weights[char_idx]

    # Smooth the envelope a bit with a short moving average (same-length output).
    k = max(1, n_samples // 200)
    if k > 1:
        kernel = torch.ones(k) / k
        env = torch.nn.functional.conv1d(
            env.unsqueeze(0).unsqueeze(0), kernel.view(1, 1, k), padding=k // 2
        ).squeeze()
        # conv1d with padding=k//2 may change length by 1 when k is even.
        if env.shape[0] != n_samples:
            env = env[:n_samples] if env.shape[0] > n_samples else torch.nn.functional.pad(
                env, (0, n_samples - env.shape[0])
            )

    # Build the waveform: fundamental + two formants, amplitude-modulated.
    phase0 = 2.0 * math.pi * f0 * t
    phase1 = 2.0 * math.pi * f1 * t
    phase2 = 2.0 * math.pi * f2 * t
    wave = (
        0.5 * torch.sin(phase0)
        + 0.3 * torch.sin(phase1)
        + 0.2 * torch.sin(phase2)
    )
    wave = wave * env

    # Normalise to [-1, 1] and scale to a comfortable level.
    peak = wave.abs().max()
    if peak > 1e-6:
        wave = wave / peak * 0.8

    # ComfyUI AUDIO format: [1, samples, channels]
    return wave.unsqueeze(0).unsqueeze(-1)


class PSN_Load_Voice_Reference:
    """Extract (mock) voice embedding from a reference audio path + speaker id.

    In a full implementation this would load the audio file and run a
    speaker-verification model.  Here the embedding is derived
    deterministically from the path and id so the node is testable without
    any audio files or external models.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio_path": ("STRING", {"default": ""}),
                "speaker_id": ("STRING", {"default": "speaker_0"}),
            }
        }

    RETURN_TYPES = ("HIDDEN",)
    RETURN_NAMES = ("voice_embedding",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, audio_path: str, speaker_id: str):
        if not isinstance(audio_path, str):
            raise TypeError("audio_path must be a string")
        if not isinstance(speaker_id, str):
            raise TypeError("speaker_id must be a string")
        emb = _make_embedding(audio_path, speaker_id)
        return (emb,)


class PSN_Generate_Speech:
    """Synthesise a short speech clip from text + voice embedding.

    Returns a ComfyUI AUDIO tuple: (waveform [1, samples, 1], sample_rate).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "Hello world"}),
                "voice_embedding": ("HIDDEN",),
                "speed": ("FLOAT", {"default": 1.0, "min": 0.25, "max": 4.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, text: str, voice_embedding: torch.Tensor, speed: float):
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not isinstance(voice_embedding, torch.Tensor):
            raise TypeError("voice_embedding must be a torch.Tensor")
        if voice_embedding.shape[0] != EMBED_DIM:
            raise ValueError(
                f"voice_embedding must have {EMBED_DIM} dims, got {voice_embedding.shape[0]}"
            )
        speed = _clamp_speed(speed)
        wave = _synthesize(text, voice_embedding, speed)
        return (wave, SAMPLE_RATE)


NODE_CLASS_MAPPINGS = {
    "PSN_Load_Voice_Reference": PSN_Load_Voice_Reference,
    "PSN_Generate_Speech": PSN_Generate_Speech,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Load_Voice_Reference": "PSN Load Voice Reference",
    "PSN_Generate_Speech": "PSN Generate Speech",
}
