"""PSN_Memory_Store: in-process, pure-logic memory store for agent preferences.

This module implements the secure-by-design, pure-logic portion of a file-based
memory store. It does NOT perform any file I/O, OS access, or network calls.
Instead, it maintains an in-memory dictionary keyed by (agent_id, key) and
returns a handle string that can be used for future recall. The actual file
persistence (writing to output/memory/<agent_id>.json with file locking) is
left to the host environment; this node only manages the logical store and
validates inputs.

Supported modes:
  - "SET":    Replace the value for the given (agent_id, key).
  - "APPEND": Append the value to the existing value (newline-separated if
              the existing value is non-empty).

The returned handle is a deterministic string encoding the agent_id and key,
suitable for passing to a companion recall node.
"""

import json
import hashlib

CAT = "ParametricStudio/Memory"

_MODES = ("SET", "APPEND")


def _make_handle(agent_id: str, key: str) -> str:
    """Build a deterministic handle string for a (agent_id, key) pair."""
    raw = f"{agent_id}::{key}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"mem:{agent_id}:{key}:{digest}"


def _validate_agent_id(agent_id: str) -> str:
    if not isinstance(agent_id, str):
        raise ValueError("agent_id must be a string")
    stripped = agent_id.strip()
    if not stripped:
        raise ValueError("agent_id must not be empty")
    if len(stripped) > 256:
        raise ValueError("agent_id must be at most 256 characters")
    return stripped


def _validate_key(key: str) -> str:
    if not isinstance(key, str):
        raise ValueError("key must be a string")
    stripped = key.strip()
    if not stripped:
        raise ValueError("key must not be empty")
    if len(stripped) > 512:
        raise ValueError("key must be at most 512 characters")
    return stripped


def _validate_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    if len(value) > 1_000_000:
        raise ValueError("value must be at most 1,000,000 characters")
    return value


def _validate_mode(mode: str) -> str:
    if not isinstance(mode, str):
        raise ValueError("mode must be a string")
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")
    return mode


# In-process store: {(agent_id, key): value}
_STORE: dict = {}


class PSN_Memory_Store:
    """Stores a key-value pair in an in-process memory store and returns a handle."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "agent_id": ("STRING", {"default": "default_agent"}),
                "key": ("STRING", {"default": "preferred_style"}),
                "value": ("STRING", {"default": ""}),
                "mode": (list(_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("store_handle",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, agent_id: str, key: str, value: str, mode: str) -> tuple:
        agent_id = _validate_agent_id(agent_id)
        key = _validate_key(key)
        value = _validate_value(value)
        mode = _validate_mode(mode)

        store_key = (agent_id, key)

        if mode == "SET":
            _STORE[store_key] = value
        elif mode == "APPEND":
            existing = _STORE.get(store_key, "")
            if existing:
                _STORE[store_key] = existing + "\n" + value
            else:
                _STORE[store_key] = value

        handle = _make_handle(agent_id, key)
        return (handle,)


NODE_CLASS_MAPPINGS = {
    "PSN_Memory_Store": PSN_Memory_Store,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Memory_Store": "PSN Memory Store",
}
