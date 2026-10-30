"""
PSN Audio Notification System (pure-logic, secure-by-design).

This module implements the *logic* of an audio notification node for ComfyUI
without performing any actual audio playback, file I/O, or OS access.

Because the spec requires playing local WAV files (which needs pygame/simpleaudio
and file access), this implementation is restricted to:
- Validating the requested `sound_type` against an allow-list.
- Validating the `volume` range.
- Selecting the correct bundled asset path (as a string) for the requested cue.
- Producing a `trigger` boolean and a human-readable `reason` string.

The node is safe to run in headless/CI environments: it never opens a socket,
never reads/writes files, and never imports audio libraries.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Audio"

# Allow-list of supported sound cues and their bundled asset paths.
# Paths are relative to a hypothetical bundled assets directory; they are
# returned as strings only and never opened.
_SOUND_ASSETS = {
    "success": "assets/sounds/success.wav",
    "error": "assets/sounds/error.wav",
    "info": "assets/sounds/info.wav",
}

_SOUND_TYPES = list(_SOUND_ASSETS.keys())


def _select_asset(sound_type: str) -> str:
    """Return the bundled asset path for a valid sound_type, or raise ValueError."""
    if sound_type not in _SOUND_ASSETS:
        raise ValueError(f"Unknown sound_type: {sound_type!r}. Allowed: {_SOUND_TYPES}")
    return _SOUND_ASSETS[sound_type]


def _validate_volume(volume: float) -> bool:
    """Return True if volume is within [0.0, 1.0]."""
    return 0.0 <= volume <= 1.0


class PSN_Notif_Play:
    """
    Selects the correct bundled WAV asset for a workflow stage and reports
    whether the notification should be triggered.

    Inputs:
        sound_type: One of "success", "error", "info".
        volume:     Playback volume in [0.0, 1.0].

    Outputs:
        trigger:    True if the sound_type is valid and volume is in range.
        asset_path: The bundled WAV file path (string) for the selected cue.
        reason:     Human-readable explanation of the trigger decision.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sound_type": (_SOUND_TYPES,),
                "volume": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("trigger", "asset_path", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, sound_type: str, volume: float):
        # Validate sound_type against allow-list.
        if sound_type not in _SOUND_ASSETS:
            return (False, "", f"Invalid sound_type: {sound_type!r}")

        # Validate volume range.
        if not _validate_volume(volume):
            return (False, _SOUND_ASSETS[sound_type], f"Volume {volume} out of range [0.0, 1.0]")

        asset_path = _select_asset(sound_type)
        reason = f"Play {sound_type} cue at volume {volume:.2f}"
        return (True, asset_path, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Notif_Play": PSN_Notif_Play,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Notif_Play": "PSN Audio Notification Play",
}
