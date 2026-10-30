"""
Stateful Multi-Step Video Generation nodes.

This module provides a secure, pure-logic implementation of stateful storage
and retrieval for multi-step video generation workflows. It uses a module-level
dictionary to store intermediate latent states or frame indices across multiple
nodes.

Security & Design Notes:
- Pure Python standard library only.
- No file, network, subprocess, or OS access.
- No eval/exec or dunder tricks.
- State is stored in a module-level dict (`_STATE_STORE`).
- To mitigate memory leaks, a `PSN_State_Clear` node is provided to clear
  specific keys or the entire store.
- To mitigate race conditions in concurrent graphs, keys are expected to be
  namespaced by the user (e.g., "graph_id/last_latent").
"""

from typing import Any, Dict, Optional

# Module-level state store
_STATE_STORE: Dict[str, Any] = {}

# Category for these nodes
CAT = "ParametricStudio/StatefulVideo"


class PSN_State_Store:
    """
    Stores a value in a global dictionary keyed by `key`.
    
    Inputs:
        key (STRING): The key under which to store the value.
        value (ANY): The value to store (e.g., LATENT, INT, etc.).
    
    Outputs:
        status (BOOLEAN): True if the value was stored successfully.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": "state_key"}),
                "value": ("ANY", {}),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("status",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, key: str, value: Any) -> tuple:
        """
        Store the value in the global state dictionary.
        
        Args:
            key: The key to store the value under.
            value: The value to store.
            
        Returns:
            A tuple containing a boolean indicating success.
        """
        if not isinstance(key, str) or not key.strip():
            return (False,)
        
        _STATE_STORE[key] = value
        return (True,)


class PSN_State_Retrieve:
    """
    Retrieves a value from the global dictionary.
    
    Inputs:
        key (STRING): The key to retrieve the value from.
        default (ANY, optional): The value to return if the key is not found.
    
    Outputs:
        value (ANY): The retrieved value, or the default if not found.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": "state_key"}),
            },
            "optional": {
                "default": ("ANY", {}),
            }
        }

    RETURN_TYPES = ("ANY",)
    RETURN_NAMES = ("value",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, key: str, default: Any = None) -> tuple:
        """
        Retrieve the value from the global state dictionary.
        
        Args:
            key: The key to retrieve the value from.
            default: The value to return if the key is not found.
            
        Returns:
            A tuple containing the retrieved value or the default.
        """
        if not isinstance(key, str) or not key.strip():
            return (default,)
        
        return (_STATE_STORE.get(key, default),)


class PSN_State_Clear:
    """
    Clears state from the global dictionary to prevent memory leaks.
    
    Inputs:
        key (STRING, optional): The specific key to clear. If empty, clears all.
    
    Outputs:
        status (BOOLEAN): True if the clear operation was successful.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("status",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, key: str) -> tuple:
        """
        Clear a specific key or all keys from the state store.
        
        Args:
            key: The key to clear. If empty, clears all keys.
            
        Returns:
            A tuple containing a boolean indicating success.
        """
        if key and key.strip():
            _STATE_STORE.pop(key, None)
        else:
            _STATE_STORE.clear()
        
        return (True,)


# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_State_Store": PSN_State_Store,
    "PSN_State_Retrieve": PSN_State_Retrieve,
    "PSN_State_Clear": PSN_State_Clear,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_State_Store": "State Store",
    "PSN_State_Retrieve": "State Retrieve",
    "PSN_State_Clear": "State Clear",
}
