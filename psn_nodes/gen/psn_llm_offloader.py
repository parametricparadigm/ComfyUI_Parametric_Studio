"""PSN_LLM_Offloader: pure-logic offload command builder and status parser.

This module implements the secure, pure-logic portion of an LLM offloader node.
It does NOT open sockets, spawn processes, or touch the filesystem. Instead it:
  - validates offload targets against an allow-list,
  - builds a JSON API payload for llama-server (swap-to-RAM or terminate),
  - parses a mock/real API response into a status string and estimated freed VRAM,
  - applies a simple rate-limit guard so repeated triggers are throttled.

Use the returned `api_payload` string with your own transport layer (e.g. the
Setmaster__comfyui-llamacpp server control node) to actually perform the offload.
"""

import json
import time

# Allow-list of valid offload targets
_OFFLOAD_TARGETS = ("RAM", "DISK")

# Status constants
_STATUS_OFFLOADED = "OFFLOADED"
_STATUS_FAILED = "FAILED"
_STATUS_NO_ACTION = "NO_ACTION"

# Rate-limit: minimum seconds between offload attempts
_RATE_LIMIT_SECONDS = 2.0


def _validate_target(target):
    """Return True if target is in the allow-list."""
    return target in _OFFLOAD_TARGETS


def _build_payload(target, model_id="default"):
    """Build a JSON API payload string for llama-server.

    For RAM:  {"action": "swap_to_cpu", "model": model_id}
    For DISK: {"action": "terminate", "model": model_id}
    """
    if target == "RAM":
        action = "swap_to_cpu"
    else:
        action = "terminate"
    payload = {"action": action, "model": model_id}
    return json.dumps(payload, sort_keys=True)


def _parse_response(response_text, target):
    """Parse an API response JSON string into (status, freed_vram_gb).

    Expected response shape:
      {"success": true, "freed_vram_gb": 4.2}
      {"success": false, "error": "model not loaded"}

    Returns (status_string, freed_vram_float).
    """
    try:
        data = json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        return (_STATUS_FAILED, 0.0)

    if not isinstance(data, dict):
        return (_STATUS_FAILED, 0.0)

    success = data.get("success", False)
    if not success:
        return (_STATUS_FAILED, 0.0)

    freed = data.get("freed_vram_gb", 0.0)
    try:
        freed = float(freed)
    except (TypeError, ValueError):
        freed = 0.0

    return (_STATUS_OFFLOADED, freed)


def _rate_limit_ok(last_trigger_time, now=None):
    """Return True if enough time has passed since last trigger."""
    if now is None:
        now = time.time()
    if last_trigger_time is None:
        return True
    return (now - last_trigger_time) >= _RATE_LIMIT_SECONDS


class PSN_LLM_Offloader:
    """Builds offload commands and parses responses for LLM VRAM offloading.

    Pure-logic node: no network, no process control, no file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trigger": ("BOOLEAN", {"default": False}),
                "offload_target": (list(_OFFLOAD_TARGETS),),
            },
            "optional": {
                "model_id": ("STRING", {"default": "default", "multiline": False}),
                "api_response": ("STRING", {"default": "", "multiline": True}),
                "last_trigger_time": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e12, "step": 0.001}),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT", "STRING")
    RETURN_NAMES = ("offload_status", "freed_vram", "api_payload")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/LLM"

    def run(self, trigger, offload_target, model_id="default", api_response="", last_trigger_time=0.0):
        # Validate target
        if not _validate_target(offload_target):
            return (_STATUS_FAILED, 0.0, "")

        # If not triggered, no action
        if not trigger:
            return (_STATUS_NO_ACTION, 0.0, "")

        # Rate-limit check
        if not _rate_limit_ok(last_trigger_time):
            return (_STATUS_NO_ACTION, 0.0, "")

        # Build the API payload
        payload = _build_payload(offload_target, model_id)

        # If no API response provided, we cannot determine final status;
        # return NO_ACTION with the payload so the caller can send it.
        if not api_response or not api_response.strip():
            return (_STATUS_NO_ACTION, 0.0, payload)

        # Parse the response
        status, freed = _parse_response(api_response, offload_target)
        return (status, freed, payload)


NODE_CLASS_MAPPINGS = {
    "PSN_LLM_Offloader": PSN_LLM_Offloader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_Offloader": "PSN LLM Offloader",
}
