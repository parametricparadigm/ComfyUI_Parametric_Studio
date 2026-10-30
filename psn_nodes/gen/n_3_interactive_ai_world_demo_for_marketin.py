"""
PSN Matrix-Game Interactive World Demo (Pure Logic / Secure-by-Design)

This module implements the pure-logic, secure-by-design components for the
'Interactive AI World Demo for Marketing' spec. It does NOT load models,
access the network, open files, or use GPU/torch/ComfyUI internals.

Instead, it provides:
1. PSN_MatrixGame_Load: Validates model path and device configuration,
   returning a safe, opaque 'model handle' (a validated config dict) that
   downstream nodes can use for metadata/telemetry purposes.
2. PSN_MatrixGame_Generate: Validates generation parameters (prompt, fps,
   mouse icon), simulates a deterministic 'world state' based on inputs,
   and returns a structured state string and a mock video metadata dict.

All functions take plain values (strings, numbers, dicts) and return plain
values. No side effects, no I/O, no external dependencies.
"""

import json
import re
import hashlib

# Allowed devices for model loading
ALLOWED_DEVICES = ["cuda", "cpu"]

# Allowed mouse icon types (simplified for demo)
ALLOWED_MOUSE_ICONS = ["default", "crosshair", "hand", "pointer"]

# Max prompt length to prevent abuse
MAX_PROMPT_LENGTH = 1024

# FPS bounds
MIN_FPS = 1
MAX_FPS = 120


def _validate_model_path(model_path: str) -> tuple[bool, str]:
    """
    Validate model path string.
    Returns (is_valid, reason).
    """
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if not model_path.strip():
        return False, "model_path cannot be empty"
    # Basic sanity: no null bytes, reasonable length
    if "\x00" in model_path:
        return False, "model_path contains null bytes"
    if len(model_path) > 512:
        return False, "model_path too long"
    # Disallow path traversal patterns (basic check)
    if ".." in model_path:
        return False, "model_path contains path traversal"
    return True, "ok"


def _validate_device(device: str) -> tuple[bool, str]:
    """
    Validate device string.
    Returns (is_valid, reason).
    """
    if not isinstance(device, str):
        return False, "device must be a string"
    if device not in ALLOWED_DEVICES:
        return False, f"device must be one of {ALLOWED_DEVICES}"
    return True, "ok"


def _validate_prompt(prompt: str) -> tuple[bool, str]:
    """
    Validate prompt string.
    Returns (is_valid, reason).
    """
    if not isinstance(prompt, str):
        return False, "prompt must be a string"
    if not prompt.strip():
        return False, "prompt cannot be empty"
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, f"prompt exceeds max length {MAX_PROMPT_LENGTH}"
    return True, "ok"


def _validate_fps(fps: int) -> tuple[bool, str]:
    """
    Validate fps integer.
    Returns (is_valid, reason).
    """
    if not isinstance(fps, int) or isinstance(fps, bool):
        return False, "fps must be an integer"
    if fps < MIN_FPS or fps > MAX_FPS:
        return False, f"fps must be between {MIN_FPS} and {MAX_FPS}"
    return True, "ok"


def _validate_mouse_icon(mouse_icon: str) -> tuple[bool, str]:
    """
    Validate mouse icon string.
    Returns (is_valid, reason).
    """
    if not isinstance(mouse_icon, str):
        return False, "mouse_icon must be a string"
    if mouse_icon not in ALLOWED_MOUSE_ICONS:
        return False, f"mouse_icon must be one of {ALLOWED_MOUSE_ICONS}"
    return True, "ok"


def _compute_state_hash(prompt: str, fps: int, mouse_icon: str) -> str:
    """
    Compute a deterministic hash for the world state.
    """
    payload = f"{prompt}|{fps}|{mouse_icon}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _build_state_metadata(prompt: str, fps: int, mouse_icon: str, state_hash: str) -> str:
    """
    Build a JSON string representing the world state metadata.
    """
    state = {
        "prompt": prompt,
        "fps": fps,
        "mouse_icon": mouse_icon,
        "state_hash": state_hash,
        "status": "generated",
        "duration_seconds": 5.0,  # Fixed 5-second clip for demo
        "resolution": "1280x720",
    }
    return json.dumps(state, sort_keys=True)


def _build_video_metadata(fps: int, duration_seconds: float = 5.0) -> dict:
    """
    Build a mock video metadata dict.
    """
    total_frames = int(fps * duration_seconds)
    return {
        "fps": fps,
        "duration_seconds": duration_seconds,
        "total_frames": total_frames,
        "width": 1280,
        "height": 720,
        "codec": "h264",
        "format": "mp4",
    }


class PSN_MatrixGame_Load:
    """
    Validates Matrix-Game model loading parameters and returns a safe model handle.
    Does NOT actually load the model.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {"default": "models/matrix_game_17b.safetensors", "multiline": False}),
                "device": (ALLOWED_DEVICES,),
            }
        }

    RETURN_TYPES = ("MATRIX_GAME_MODEL", "STRING")
    RETURN_NAMES = ("model", "load_status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/MatrixGame"

    def run(self, model_path: str, device: str) -> tuple[dict, str]:
        """
        Validate inputs and return a model handle dict and status string.
        """
        path_ok, path_reason = _validate_model_path(model_path)
        if not path_ok:
            return ({"error": path_reason, "loaded": False}, f"FAIL: {path_reason}")

        dev_ok, dev_reason = _validate_device(device)
        if not dev_ok:
            return ({"error": dev_reason, "loaded": False}, f"FAIL: {dev_reason}")

        # Create a safe model handle (no actual loading)
        model_handle = {
            "model_path": model_path,
            "device": device,
            "loaded": True,
            "param_count": 17_000_000_000,  # 17B
            "status": "ready",
        }
        return (model_handle, "OK: model handle created")


class PSN_MatrixGame_Generate:
    """
    Validates generation parameters and simulates world state generation.
    Does NOT actually generate video.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MATRIX_GAME_MODEL",),
                "prompt": ("STRING", {"default": "A cyberpunk city at night", "multiline": False}),
                "mouse_icon": (ALLOWED_MOUSE_ICONS,),
                "fps": ("INT", {"default": 30, "min": MIN_FPS, "max": MAX_FPS, "step": 1}),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING")
    RETURN_NAMES = ("video", "state")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/MatrixGame"

    def run(self, model: dict, prompt: str, mouse_icon: str, fps: int) -> tuple[dict, str]:
        """
        Validate inputs and return mock video metadata and state string.
        """
        # Validate model handle
        if not isinstance(model, dict):
            return ({"error": "model must be a dict", "generated": False}, "FAIL: invalid model handle")
        if not model.get("loaded", False):
            return ({"error": "model not loaded", "generated": False}, "FAIL: model not loaded")

        # Validate prompt
        prompt_ok, prompt_reason = _validate_prompt(prompt)
        if not prompt_ok:
            return ({"error": prompt_reason, "generated": False}, f"FAIL: {prompt_reason}")

        # Validate mouse icon
        icon_ok, icon_reason = _validate_mouse_icon(mouse_icon)
        if not icon_ok:
            return ({"error": icon_reason, "generated": False}, f"FAIL: {icon_reason}")

        # Validate fps
        fps_ok, fps_reason = _validate_fps(fps)
        if not fps_ok:
            return ({"error": fps_reason, "generated": False}, f"FAIL: {fps_reason}")

        # Compute state
        state_hash = _compute_state_hash(prompt, fps, mouse_icon)
        state_str = _build_state_metadata(prompt, fps, mouse_icon, state_hash)
        video_meta = _build_video_metadata(fps)
        video_meta["generated"] = True
        video_meta["state_hash"] = state_hash

        return (video_meta, state_str)


NODE_CLASS_MAPPINGS = {
    "PSN_MatrixGame_Load": PSN_MatrixGame_Load,
    "PSN_MatrixGame_Generate": PSN_MatrixGame_Generate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MatrixGame_Load": "MatrixGame Load (Pure Logic)",
    "PSN_MatrixGame_Generate": "MatrixGame Generate (Pure Logic)",
}
