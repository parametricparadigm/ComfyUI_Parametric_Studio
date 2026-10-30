"""Secure API key management for ComfyUI workflows.

This module provides in-memory storage for API keys and sensitive configuration
data, preventing them from being hardcoded in the graph JSON. Keys are stored
in a module-level dictionary and can be retrieved by other nodes that need
external services.

Security notes:
- Keys are stored in memory only (no file I/O, no network).
- The store is cleared on module reload (session boundary).
- No encryption is applied; this is a convenience layer, not a vault.
- Key names and values are validated to prevent injection or abuse.

Nodes:
- PSN_Key_Store: Stores a key-value pair in the in-memory store.
- PSN_Key_Retriever: Retrieves a value by key name; returns empty string if not found.
"""

import re
import string

# Allowed characters for key names: letters, digits, underscore, hyphen, dot
_KEY_NAME_ALLOWED = set(string.ascii_letters + string.digits + "_-.")
_KEY_NAME_MAX_LEN = 128
_KEY_VALUE_MAX_LEN = 4096

# Module-level in-memory store
_KEY_STORE = {}


def _validate_key_name(name):
    """Validate a key name. Returns (is_valid, reason)."""
    if not isinstance(name, str):
        return False, "key_name must be a string"
    if len(name) == 0:
        return False, "key_name must not be empty"
    if len(name) > _KEY_NAME_MAX_LEN:
        return False, "key_name exceeds maximum length of %d" % _KEY_NAME_MAX_LEN
    for ch in name:
        if ch not in _KEY_NAME_ALLOWED:
            return False, "key_name contains invalid character: %r" % ch
    return True, "ok"


def _validate_key_value(value):
    """Validate a key value. Returns (is_valid, reason)."""
    if not isinstance(value, str):
        return False, "key_value must be a string"
    if len(value) > _KEY_VALUE_MAX_LEN:
        return False, "key_value exceeds maximum length of %d" % _KEY_VALUE_MAX_LEN
    return True, "ok"


def psn_store_key(key_name, key_value):
    """Store a key-value pair. Returns (success, reason)."""
    valid_name, name_reason = _validate_key_name(key_name)
    if not valid_name:
        return False, name_reason
    valid_value, value_reason = _validate_key_value(key_value)
    if not valid_value:
        return False, value_reason
    _KEY_STORE[key_name] = key_value
    return True, "stored"


def psn_retrieve_key(key_name):
    """Retrieve a value by key name. Returns (value, found)."""
    valid_name, name_reason = _validate_key_name(key_name)
    if not valid_name:
        return "", False
    value = _KEY_STORE.get(key_name, "")
    return value, key_name in _KEY_STORE


def psn_delete_key(key_name):
    """Delete a key from the store. Returns (success, reason)."""
    valid_name, name_reason = _validate_key_name(key_name)
    if not valid_name:
        return False, name_reason
    if key_name in _KEY_STORE:
        del _KEY_STORE[key_name]
        return True, "deleted"
    return False, "key not found"


def psn_clear_store():
    """Clear all keys from the store."""
    _KEY_STORE.clear()


def psn_list_keys():
    """Return a list of stored key names (not values)."""
    return sorted(_KEY_STORE.keys())


CAT = "ParametricStudio/Secure"


class PSN_Key_Store:
    """Store an API key or sensitive value in the in-memory key store."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key_name": ("STRING", {"default": "", "multiline": False}),
                "key_value": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("status",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, key_name, key_value):
        success, reason = psn_store_key(key_name, key_value)
        return (success,)


class PSN_Key_Retriever:
    """Retrieve a stored API key or sensitive value by name."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key_name": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("key_value",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, key_name):
        value, found = psn_retrieve_key(key_name)
        return (value,)


NODE_CLASS_MAPPINGS = {
    "PSN_Key_Store": PSN_Key_Store,
    "PSN_Key_Retriever": PSN_Key_Retriever,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Key_Store": "PSN Key Store",
    "PSN_Key_Retriever": "PSN Key Retriever",
}
