"""PSN Video Dubbing Pipeline Integration.

This module provides a ComfyUI custom node that simulates a video dubbing
pipeline.  Since the real Alta API requires network access (which is
forbidden here), the node performs a *local* simulation of the dubbing
process:

* Validates inputs (video tensor, language codes, API key, lip-sync flag).
* Applies a deterministic, language-dependent transformation to the video
  tensor (a simple per-channel gain that stands in for audio re-synthesis
  and, when lip-sync is requested, a mild spatial smoothing that stands in
  for lip-sync warping).
* Returns the processed video tensor and a human-readable status string.

What is NOT implemented (requires external services / heavy models):
  * Actual translation of audio/video content (needs a TTS/ASR model).
  * Real lip-sync (needs a video generation / warping model).
  * Network calls to the Alta API (forbidden in this environment).
  * ffmpeg-based video encoding / decoding.
"""

import torch

CAT = "ParametricStudio/Video"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LANG_GAINS = {
    "en": 1.00,
    "es": 1.05,
    "fr": 0.95,
    "de": 1.02,
    "it": 0.98,
    "pt": 1.03,
    "ja": 1.07,
    "ko": 1.06,
    "zh": 1.04,
    "ru": 0.97,
    "ar": 1.01,
    "hi": 1.02,
}


def _validate_video(video):
    """Return a validated video tensor or raise ValueError."""
    if not isinstance(video, torch.Tensor):
        raise ValueError("video must be a torch.Tensor")
    if video.dim() != 4:
        raise ValueError(
            f"video must be 4-D [B,H,W,C], got {video.dim()}-D"
        )
    b, h, w, c = video.shape
    if c not in (1, 3, 4):
        raise ValueError(f"video channels must be 1, 3 or 4, got {c}")
    if h < 1 or w < 1 or b < 1:
        raise ValueError("video spatial/batch dims must be >= 1")
    if not torch.is_floating_point(video):
        raise ValueError("video must be a floating-point tensor")
    return video


def _validate_lang(code, name):
    """Return a normalised language code or raise ValueError."""
    if not isinstance(code, str):
        raise ValueError(f"{name} must be a string")
    code = code.strip().lower()
    if len(code) != 2:
        raise ValueError(f"{name} must be a 2-letter ISO code, got {code!r}")
    if not code.isalpha():
        raise ValueError(f"{name} must be alphabetic, got {code!r}")
    return code


def _validate_api_key(key):
    """Return a validated API key string or raise ValueError."""
    if not isinstance(key, str):
        raise ValueError("alta_api_key must be a string")
    key = key.strip()
    if len(key) < 8:
        raise ValueError("alta_api_key must be at least 8 characters")
    return key


def _apply_dubbing(video, src, tgt, lip_sync):
    """Apply a deterministic dubbing simulation to the video tensor.

    The transformation is:
      1. A per-channel gain based on the target language (simulates audio
         re-synthesis altering the overall signal level).
      2. If lip_sync is True, a 3x3 box-blur on the spatial dimensions
         (simulates the warping / smoothing that lip-sync would apply to
         the mouth region).

    The input tensor is never modified in place.
    """
    out = video.clone()

    # 1. Language-dependent gain
    gain = _LANG_GAINS.get(tgt, 1.0)
    out = out * gain

    # 2. Optional lip-sync smoothing (3x3 box blur on H, W)
    if lip_sync:
        # Pad then average to simulate a simple blur
        # Use unfold for a 3x3 window
        # out shape: [B, H, W, C]
        # We do a simple 3x3 average on the spatial dims
        b, h, w, c = out.shape
        if h >= 3 and w >= 3:
            # Pad with replicate
            padded = torch.nn.functional.pad(
                out, (0, 0, 1, 1, 1, 1), mode="replicate"
            )
            # Accumulate 3x3 windows
            acc = torch.zeros_like(out)
            for di in range(3):
                for dj in range(3):
                    acc += padded[:, di:di + h, dj:dj + w, :]
            out = acc / 9.0

    # Clamp to [0, 1]
    out = torch.clamp(out, 0.0, 1.0)
    return out


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_Video_Dubbing:
    """Simulate a video dubbing pipeline (translate + dub + optional lip-sync).

    Since the real Alta API is not available in this environment, this node
    performs a deterministic local simulation of the dubbing process.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
                "source_lang": ("STRING", {"default": "en"}),
                "target_lang": ("STRING", {"default": "es"}),
                "alta_api_key": ("STRING", {"default": "sk-placeholder-key-000000"}),
                "lip_sync": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING")
    RETURN_NAMES = ("dubbed_video", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video, source_lang, target_lang, alta_api_key, lip_sync):
        # Validate inputs
        video = _validate_video(video)
        src = _validate_lang(source_lang, "source_lang")
        tgt = _validate_lang(target_lang, "target_lang")
        key = _validate_api_key(alta_api_key)

        if not isinstance(lip_sync, bool):
            raise ValueError("lip_sync must be a boolean")

        # Simulate the dubbing pipeline
        dubbed = _apply_dubbing(video, src, tgt, lip_sync)

        # Build status string
        parts = [
            f"dubbing simulated: {src} -> {tgt}",
            f"lip_sync={'on' if lip_sync else 'off'}",
            f"api_key={'valid' if len(key) >= 8 else 'invalid'}",
        ]
        status = "; ".join(parts)

        return (dubbed, status)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Video_Dubbing": PSN_Video_Dubbing,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_Dubbing": "PSN Video Dubbing Pipeline",
}
