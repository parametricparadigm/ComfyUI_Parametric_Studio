"""
PSN_Param_Hub: A pure-logic parameter store for dynamic workflow configuration.

This module implements a secure, in-memory parameter hub that allows LLM agents
or other nodes to set and retrieve global or local parameters without hardcoding
values. It uses a shared dictionary to store parameters.

No network, file, or GPU access is performed. All operations are pure Python
standard library logic.
"""

from typing import Any, Dict, Optional, Tuple

# Module-level shared parameter store
_param_store: Dict[str, Any] = {}

# Allowed scopes
_SCOPES = ("GLOBAL", "LOCAL")


def _validate_param_name(name: str) -> Tuple[bool, str]:
    """Validate that a parameter name is a non-empty string with safe characters."""
    if not isinstance(name, str):
        return False, "param_name must be a string"
    if not name.strip():
        return False, "param_name must not be empty"
    # Allow alphanumeric, underscore, hyphen, dot
    for ch in name:
        if not (ch.isalnum() or ch in "_-."):
            return False, f"param_name contains invalid character: {ch!r}"
    return True, "ok"


def _validate_scope(scope: str) -> Tuple[bool, str]:
    """Validate that scope is one of the allowed values."""
    if scope not in _SCOPES:
        return False, f"scope must be one of {_SCOPES}, got {scope!r}"
    return True, "ok"


def _validate_value(value: Any) -> Tuple[bool, str]:
    """Validate that value is a supported type (FLOAT, INT, STRING)."""
    if isinstance(value, (int, float, str)):
        return True, "ok"
    return False, f"value must be FLOAT, INT, or STRING, got {type(value).__name__}"


def set_param(param_name: str, value: Any, scope: str) -> Tuple[bool, str]:
    """
    Store a parameter in the hub.
    
    Returns:
        (success, message)
    """
    ok, msg = _validate_param_name(param_name)
    if not ok:
        return False, msg
    ok, msg = _validate_scope(scope)
    if not ok:
        return False, msg
    ok, msg = _validate_value(value)
    if not ok:
        return False, msg

    key = f"{scope}:{param_name}"
    _param_store[key] = value
    return True, f"Set {key} = {value!r}"


def get_param(param_name: str, scope: str = "GLOBAL") -> Tuple[bool, Any, str]:
    """
    Retrieve a parameter from the hub.
    
    Returns:
        (found, value, message)
    """
    ok, msg = _validate_param_name(param_name)
    if not ok:
        return False, None, msg
    ok, msg = _validate_scope(scope)
    if not ok:
        return False, None, msg

    key = f"{scope}:{param_name}"
    if key in _param_store:
        return True, _param_store[key], f"Found {key}"
    return False, None, f"Parameter {key} not found"


def list_params(scope: Optional[str] = None) -> Dict[str, Any]:
    """
    List all parameters, optionally filtered by scope.
    
    Returns:
        Dictionary of key -> value
    """
    if scope is None:
        return dict(_param_store)
    if scope not in _SCOPES:
        return {}
    prefix = f"{scope}:"
    return {k: v for k, v in _param_store.items() if k.startswith(prefix)}


def clear_params(scope: Optional[str] = None) -> int:
    """
    Clear parameters, optionally filtered by scope.
    
    Returns:
        Number of parameters cleared
    """
    if scope is None:
        count = len(_param_store)
        _param_store.clear()
        return count
    if scope not in _SCOPES:
        return 0
    prefix = f"{scope}:"
    keys_to_remove = [k for k in _param_store if k.startswith(prefix)]
    for k in keys_to_remove:
        del _param_store[k]
    return len(keys_to_remove)


class PSN_ParamHub:
    """
    ComfyUI custom node that stores parameters in a shared dictionary.
    
    Allows LLM agents to dynamically adjust global workflow parameters
    without hardcoding values. Other nodes can read from this hub.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "param_name": ("STRING", {"default": "cfg_scale", "multiline": False}),
                "value": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "scope": (list(_SCOPES),),
            },
            "optional": {
                "value_int": ("INT", {"default": 0, "min": -1e9, "max": 1e9}),
                "value_str": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("PARAM_HUB", "BOOLEAN", "STRING")
    RETURN_NAMES = ("hub_handle", "success", "message")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/ParamHub"

    def run(
        self,
        param_name: str,
        value: float,
        scope: str,
        value_int: Optional[int] = None,
        value_str: Optional[str] = None,
    ):
        """
        Store a parameter in the hub.
        
        The primary value is taken from `value` (FLOAT). If `value_int` or
        `value_str` are provided and non-default, they take precedence.
        """
        # Determine the actual value to store
        actual_value = value
        if value_str is not None and value_str != "":
            actual_value = value_str
        elif value_int is not None and value_int != 0:
            actual_value = value_int

        success, message = set_param(param_name, actual_value, scope)
        # hub_handle is a sentinel object representing the shared store
        hub_handle = _param_store
        return (hub_handle, success, message)


class PSN_ParamHubRead:
    """
    ComfyUI custom node that reads a parameter from the shared hub.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "param_name": ("STRING", {"default": "cfg_scale", "multiline": False}),
                "scope": (list(_SCOPES),),
            },
            "optional": {
                "default_value": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
            },
        }

    RETURN_TYPES = ("FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("value", "found", "message")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/ParamHub"

    def run(self, param_name: str, scope: str, default_value: float = 0.0):
        """
        Read a parameter from the hub. Returns default_value if not found.
        """
        found, val, message = get_param(param_name, scope)
        if found:
            # Convert to float if possible
            try:
                result = float(val)
            except (TypeError, ValueError):
                result = default_value
        else:
            result = default_value
        return (result, found, message)


NODE_CLASS_MAPPINGS = {
    "PSN_ParamHub": PSN_ParamHub,
    "PSN_ParamHubRead": PSN_ParamHubRead,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ParamHub": "PSN Param Hub (Set)",
    "PSN_ParamHubRead": "PSN Param Hub (Read)",
}
