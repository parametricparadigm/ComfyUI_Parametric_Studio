"""
PSN_Audio_Notifier: Validates audio notification configuration and formats the playback payload.

This node does NOT play audio. It performs secure-by-design validation:
- Validates volume is within [0.0, 1.0]
- Validates sound_file extension is in an allow-list (wav, mp3)
- Formats a JSON payload describing the intended playback action
- Returns a boolean indicating whether the configuration is valid for playback

Pure Python standard library only. No file access, no audio playback, no network.
"""

import json
import re

CAT = "ParametricStudio/Audio"

ALLOWED_EXTENSIONS = {".wav", ".mp3"}

def _validate_sound_file(sound_file: str) -> tuple[bool, str]:
    """Validate that sound_file is a non-empty string with an allowed extension."""
    if not isinstance(sound_file, str):
        return False, "sound_file must be a string"
    if not sound_file.strip():
        return False, "sound_file must not be empty"
    # Normalize to lowercase for extension check
    lower = sound_file.lower().strip()
    # Check if it ends with an allowed extension
    for ext in ALLOWED_EXTENSIONS:
        if lower.endswith(ext):
            return True, "ok"
    return False, f"sound_file must end with one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

def _validate_volume(volume: float) -> tuple[bool, str]:
    """Validate that volume is a float in [0.0, 1.0]."""
    if not isinstance(volume, (int, float)):
        return False, "volume must be a number"
    if isinstance(volume, bool):
        return False, "volume must be a number, not a boolean"
    vol = float(volume)
    if vol < 0.0 or vol > 1.0:
        return False, "volume must be between 0.0 and 1.0"
    return True, "ok"

def _format_payload(sound_file: str, volume: float) -> str:
    """Format the playback payload as a JSON string."""
    payload = {
        "action": "play_audio",
        "sound_file": sound_file.strip(),
        "volume": round(float(volume), 4),
        "non_blocking": True
    }
    return json.dumps(payload, sort_keys=True)

class PSN_AudioNotifier:
    """
    Validates audio notification configuration and formats the playback payload.
    
    Inputs:
        sound_file (STRING): Path to the audio file (WAV/MP3).
        volume (FLOAT): Volume level from 0.0 to 1.0.
    
    Outputs:
        played (BOOLEAN): True if the configuration is valid for playback.
        payload (STRING): JSON-formatted payload describing the playback action.
        reason (STRING): Human-readable reason for pass/fail.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sound_file": ("STRING", {"default": "notification.wav", "multiline": False}),
                "volume": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {}
        }
    
    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("played", "payload", "reason")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, sound_file: str, volume: float) -> tuple[bool, str, str]:
        """
        Validate the audio notification configuration and format the payload.
        
        Returns:
            played: True if both sound_file and volume are valid.
            payload: JSON string with the playback action details (empty string if invalid).
            reason: Explanation of why the configuration passed or failed.
        """
        # Validate sound_file
        file_ok, file_reason = _validate_sound_file(sound_file)
        if not file_ok:
            return (False, "", file_reason)
        
        # Validate volume
        vol_ok, vol_reason = _validate_volume(volume)
        if not vol_ok:
            return (False, "", vol_reason)
        
        # Both valid: format payload
        payload = _format_payload(sound_file, volume)
        return (True, payload, "ok")

NODE_CLASS_MAPPINGS = {
    "PSN_AudioNotifier": PSN_AudioNotifier
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AudioNotifier": "PSN Audio Notifier"
}
