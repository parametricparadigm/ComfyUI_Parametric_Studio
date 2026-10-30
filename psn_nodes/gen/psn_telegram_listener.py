"""PSN_Telegram_Listener: pure-logic, secure-by-design Telegram message handling.

This module implements ONLY the safe, offline logic for a Telegram listener node.
It does NOT open sockets, make network calls, import torch, or access the file system.
Instead it provides:
  - bot token redaction for safe logging,
  - allow-list parsing and membership checks for chat IDs,
  - command-prefix detection,
  - parsing of a JSON `getUpdates` payload into a normalized message dict,
  - rate limiting for poll intervals,
  - a `run` function that takes plain values (JSON text, token, allow-list, etc.)
    and returns the node outputs.

The actual long-polling / image download / tensor decode is left to the host
environment; this node formats and validates the data flow.
"""

import json
from typing import Any, Dict, List, Tuple

CAT = "ParametricStudio/Telegram"

# Allowed command prefixes that mark a message as a command.
COMMAND_PREFIXES = ("/", "!")

# Minimum poll interval in seconds to avoid hammering the API.
MIN_POLL_INTERVAL = 1


def psn_redact_token(token: str) -> str:
    """Redact a Telegram bot token for safe logging.

    Keeps the first 4 and last 4 characters, masking the middle.
    If the token is too short, mask everything after the first 2 chars.
    """
    if not isinstance(token, str):
        return "<invalid-token>"
    if len(token) <= 8:
        return token[:2] + "*" * max(0, len(token) - 2)
    return token[:4] + "*" * (len(token) - 8) + token[-4:]


def psn_parse_allow_list(allowed_chat_ids: str) -> List[int]:
    """Parse a comma-separated string of chat IDs into a list of ints.

    Raises ValueError if any entry is not a valid integer.
    """
    if not isinstance(allowed_chat_ids, str):
        raise ValueError("allowed_chat_ids must be a string")
    ids: List[int] = []
    for part in allowed_chat_ids.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            raise ValueError(f"Invalid chat ID in allow-list: {part!r}")
    return ids


def psn_is_allowed(chat_id: int, allow_list: List[int]) -> bool:
    """Check whether chat_id is in the allow-list."""
    return chat_id in allow_list


def psn_is_command(text: str) -> bool:
    """Return True if the text starts with a defined command prefix."""
    if not isinstance(text, str) or not text:
        return False
    return any(text.startswith(p) for p in COMMAND_PREFIXES)


def psn_rate_limit_ok(poll_interval: int) -> Tuple[bool, str]:
    """Validate poll_interval against the minimum allowed value."""
    if not isinstance(poll_interval, int) or isinstance(poll_interval, bool):
        return False, "poll_interval must be an integer"
    if poll_interval < MIN_POLL_INTERVAL:
        return False, f"poll_interval must be >= {MIN_POLL_INTERVAL} second(s)"
    return True, "ok"


def psn_parse_updates_payload(payload: str) -> Dict[str, Any]:
    """Parse a JSON `getUpdates` response into a normalized message dict.

    Returns a dict with keys:
      chat_id (int), text_prompt (str), has_image (bool), is_command (bool)
    If no message is found, returns a dict with chat_id=-1 and empty fields.
    """
    if not isinstance(payload, str):
        raise ValueError("payload must be a JSON string")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object")

    updates = data.get("result", [])
    if not isinstance(updates, list) or not updates:
        return {
            "chat_id": -1,
            "text_prompt": "",
            "has_image": False,
            "is_command": False,
        }

    # Take the first update that contains a message.
    for update in updates:
        if not isinstance(update, dict):
            continue
        msg = update.get("message")
        if not isinstance(msg, dict):
            continue
        chat = msg.get("chat", {})
        chat_id = chat.get("id", -1)
        text = msg.get("text", "")
        has_image = "photo" in msg
        return {
            "chat_id": int(chat_id),
            "text_prompt": text if isinstance(text, str) else "",
            "has_image": bool(has_image),
            "is_command": psn_is_command(text if isinstance(text, str) else ""),
        }

    return {
        "chat_id": -1,
        "text_prompt": "",
        "has_image": False,
        "is_command": False,
    }


class PSN_Telegram_Listener:
    """Pure-logic Telegram listener node.

    Takes a JSON `getUpdates` payload (as a string), a bot token, an allow-list
    of chat IDs, and a poll interval. Validates and parses the payload, checks
    the chat against the allow-list, and returns normalized outputs.

    No network, file, or GPU access is performed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bot_token": ("STRING", {"default": "", "multiline": False}),
                "allowed_chat_ids": ("STRING", {"default": "", "multiline": False}),
                "poll_interval": ("INT", {"default": 5, "min": 1, "max": 3600, "step": 1}),
                "updates_payload": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("INT", "STRING", "BOOLEAN", "BOOLEAN", "STRING")
    RETURN_NAMES = ("chat_id", "text_prompt", "is_command", "is_allowed", "redacted_token")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        bot_token: str,
        allowed_chat_ids: str,
        poll_interval: int,
        updates_payload: str,
    ) -> Tuple[int, str, bool, bool, str]:
        # Validate poll interval
        rate_ok, rate_why = psn_rate_limit_ok(poll_interval)
        if not rate_ok:
            raise ValueError(rate_why)

        # Parse allow-list
        allow_list = psn_parse_allow_list(allowed_chat_ids)

        # Parse the updates payload
        parsed = psn_parse_updates_payload(updates_payload)
        chat_id = parsed["chat_id"]
        text_prompt = parsed["text_prompt"]
        is_command = parsed["is_command"]

        # Check allow-list
        is_allowed = psn_is_allowed(chat_id, allow_list) if chat_id != -1 else False

        # Redact token for safe output
        redacted = psn_redact_token(bot_token)

        return (chat_id, text_prompt, is_command, is_allowed, redacted)


NODE_CLASS_MAPPINGS = {"PSN_Telegram_Listener": PSN_Telegram_Listener}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Telegram_Listener": "PSN Telegram Listener"}
