"""
PSN_Audio_Loader: Pure-logic validation and metadata computation for audio loading.

This module implements the secure-by-design, pure-logic portion of an audio loader node.
It does NOT open files, access the OS, or use torch/soundfile/librosa. Instead, it:
- Validates file paths against an allow-list of safe extensions.
- Validates sample rate and channel count.
- Computes expected duration from a provided byte count (simulating metadata extraction).
- Returns a structured payload that a real loader (with soundfile/librosa) could consume.

The node is designed to be paired with a backend that performs actual I/O.
"""

import re
import json

# Allow-list of safe audio file extensions
_ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aiff", ".aif"}

# Allowed sample rates (common audio rates)
_ALLOWED_SAMPLE_RATES = {8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000}

# Allowed channel counts
_ALLOWED_CHANNELS = {1, 2}


def _validate_file_path(file_path: str) -> tuple[bool, str]:
    """Validate that the file path is a string, non-empty, and has an allowed extension."""
    if not isinstance(file_path, str):
        return False, "file_path must be a string"
    if not file_path.strip():
        return False, "file_path must not be empty"
    # Normalize path separators for extension check
    normalized = file_path.replace("\\", "/")
    # Get the last segment
    basename = normalized.rsplit("/", 1)[-1]
    # Check extension
    dot_idx = basename.rfind(".")
    if dot_idx == -1:
        return False, "file_path must have a file extension"
    ext = basename[dot_idx:].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        return False, f"file extension '{ext}' not in allow-list: {sorted(_ALLOWED_EXTENSIONS)}"
    return True, "ok"


def _validate_sample_rate(sample_rate: int) -> tuple[bool, str]:
    """Validate that the sample rate is a positive integer in the allowed set."""
    if not isinstance(sample_rate, int) or isinstance(sample_rate, bool):
        return False, "sample_rate must be an integer"
    if sample_rate <= 0:
        return False, "sample_rate must be positive"
    if sample_rate not in _ALLOWED_SAMPLE_RATES:
        return False, f"sample_rate {sample_rate} not in allowed set: {sorted(_ALLOWED_SAMPLE_RATES)}"
    return True, "ok"


def _validate_channels(channels: int) -> tuple[bool, str]:
    """Validate that channels is 1 or 2."""
    if not isinstance(channels, int) or isinstance(channels, bool):
        return False, "channels must be an integer"
    if channels not in _ALLOWED_CHANNELS:
        return False, "channels must be 1 (mono) or 2 (stereo)"
    return True, "ok"


def compute_duration(byte_count: int, sample_rate: int, channels: int, bits_per_sample: int = 16) -> float:
    """
    Compute duration in seconds from byte count, sample rate, channels, and bits per sample.
    
    For PCM audio:
      total_samples = byte_count / (channels * bytes_per_sample)
      duration = total_samples / sample_rate
    
    bytes_per_sample = bits_per_sample // 8
    """
    if byte_count < 0:
        raise ValueError("byte_count must be non-negative")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if channels <= 0:
        raise ValueError("channels must be positive")
    if bits_per_sample not in (8, 16, 24, 32):
        raise ValueError("bits_per_sample must be 8, 16, 24, or 32")
    
    bytes_per_sample = bits_per_sample // 8
    bytes_per_frame = channels * bytes_per_sample
    if bytes_per_frame == 0:
        raise ValueError("bytes_per_frame must be positive")
    
    total_samples = byte_count / bytes_per_frame
    duration = total_samples / sample_rate
    return duration


class PSN_Audio_Loader:
    """
    Validates audio file parameters and computes metadata for a standardized audio load.
    
    This node does NOT perform file I/O. It validates inputs and returns a payload
    that a backend loader (using soundfile/librosa) can use to perform the actual load.
    
    Outputs:
      - audio_payload (STRING): JSON string with validated parameters for the backend.
      - duration (FLOAT): Estimated duration in seconds (requires byte_count input).
      - valid (BOOLEAN): Whether all inputs are valid.
      - reason (STRING): Validation reason or error message.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "", "multiline": False}),
                "sample_rate": ("INT", {"default": 44100, "min": 1, "max": 192000, "step": 1}),
                "channels": ("INT", {"default": 1, "min": 1, "max": 2, "step": 1}),
            },
            "optional": {
                "byte_count": ("INT", {"default": 0, "min": 0, "max": 10**12, "step": 1}),
                "bits_per_sample": ("INT", {"default": 16, "min": 8, "max": 32, "step": 8}),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("audio_payload", "duration", "valid", "reason")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Audio"

    def run(self, file_path: str, sample_rate: int, channels: int, byte_count: int = 0, bits_per_sample: int = 16):
        # Validate file path
        path_ok, path_reason = _validate_file_path(file_path)
        if not path_ok:
            return ("", 0.0, False, path_reason)

        # Validate sample rate
        sr_ok, sr_reason = _validate_sample_rate(sample_rate)
        if not sr_ok:
            return ("", 0.0, False, sr_reason)

        # Validate channels
        ch_ok, ch_reason = _validate_channels(channels)
        if not ch_ok:
            return ("", 0.0, False, ch_reason)

        # Compute duration if byte_count is provided
        duration = 0.0
        if byte_count > 0:
            try:
                duration = compute_duration(byte_count, sample_rate, channels, bits_per_sample)
            except ValueError as e:
                return ("", 0.0, False, f"duration computation error: {e}")

        # Build payload for backend loader
        payload = {
            "file_path": file_path,
            "sample_rate": sample_rate,
            "channels": channels,
            "bits_per_sample": bits_per_sample,
            "byte_count": byte_count,
            "estimated_duration": duration,
            "format": "float32",
            "normalized": True,
        }
        payload_json = json.dumps(payload, sort_keys=True)

        return (payload_json, duration, True, "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_Audio_Loader": PSN_Audio_Loader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Audio_Loader": "PSN Audio Loader (Validation)",
}
