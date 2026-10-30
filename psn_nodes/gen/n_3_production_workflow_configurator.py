"""
PSN_Workflow_Configurator: A session-scoped registry for managing reusable workflow
configurations across different pipelines (video, music, image).

This node provides a pure-logic, secure-by-design implementation of a scoped key-value
store. It supports three scopes: "Global", "Pipeline", and "Node". Values set in a
narrower scope (e.g., Pipeline) override values in broader scopes (e.g., Global)
when inheritance is enabled.

No file I/O, network access, or external dependencies are used. All state is held
in a module-level dictionary simulating a session registry.
"""

import copy
import json

# Module-level session registry
# Structure: { scope: { config_name: { key: value } } }
_SESSION_REGISTRY = {
    "Global": {},
    "Pipeline": {},
    "Node": {}
}

# Scope hierarchy for inheritance (narrowest to broadest)
_SCOPE_HIERARCHY = ["Node", "Pipeline", "Global"]

# Allowed scopes
_ALLOWED_SCOPES = ["Global", "Pipeline", "Node"]

# Allowed modes
_ALLOWED_MODES = ["Get", "Set", "Delete"]


def _get_inherited_value(config_name, scope, key, inherit=True):
    """
    Retrieve a value from the registry, optionally inheriting from broader scopes.
    
    Args:
        config_name: The name of the configuration profile.
        scope: The current scope ("Global", "Pipeline", "Node").
        key: The parameter key to retrieve.
        inherit: If True, check broader scopes if key not found in current scope.
    
    Returns:
        Tuple of (found: bool, value: any, source_scope: str or None)
    """
    # Determine which scopes to check based on inheritance
    if inherit:
        # Check from narrowest to broadest (current scope first, then broader)
        # Find the index of the current scope in the hierarchy
        if scope not in _SCOPE_HIERARCHY:
            return (False, None, None)
        
        scope_index = _SCOPE_HIERARCHY.index(scope)
        # Check from current scope to broadest
        scopes_to_check = _SCOPE_HIERARCHY[scope_index:]
    else:
        # Only check the current scope
        scopes_to_check = [scope]
    
    for check_scope in scopes_to_check:
        if check_scope not in _SESSION_REGISTRY:
            continue
        if config_name in _SESSION_REGISTRY[check_scope]:
            config_dict = _SESSION_REGISTRY[check_scope][config_name]
            if key in config_dict:
                return (True, copy.deepcopy(config_dict[key]), check_scope)
    
    return (False, None, None)


def _set_value(config_name, scope, key, value):
    """
    Set a value in the registry for the given scope and config.
    
    Args:
        config_name: The name of the configuration profile.
        scope: The scope to set the value in.
        key: The parameter key.
        value: The value to store.
    
    Returns:
        True if successful.
    """
    if scope not in _SESSION_REGISTRY:
        return False
    if config_name not in _SESSION_REGISTRY[scope]:
        _SESSION_REGISTRY[scope][config_name] = {}
    _SESSION_REGISTRY[scope][config_name][key] = copy.deepcopy(value)
    return True


def _delete_value(config_name, scope, key):
    """
    Delete a value from the registry for the given scope and config.
    
    Args:
        config_name: The name of the configuration profile.
        scope: The scope to delete from.
        key: The parameter key.
    
    Returns:
        True if the key was found and deleted, False otherwise.
    """
    if scope not in _SESSION_REGISTRY:
        return False
    if config_name not in _SESSION_REGISTRY[scope]:
        return False
    config_dict = _SESSION_REGISTRY[scope][config_name]
    if key in config_dict:
        del config_dict[key]
        return True
    return False


def _clear_registry():
    """Clear the entire session registry (for testing purposes)."""
    for scope in _SESSION_REGISTRY:
        _SESSION_REGISTRY[scope].clear()


class PSN_Workflow_Configurator:
    """
    A node that acts as a central registry for workflow parameters.
    It stores key-value pairs in a session-scoped dictionary and allows
    different pipelines to share or isolate settings based on scope.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config_name": ("STRING", {"default": "default_config", "multiline": False}),
                "scope": (_ALLOWED_SCOPES, {"default": "Global"}),
                "key": ("STRING", {"default": "param_key", "multiline": False}),
                "mode": (_ALLOWED_MODES, {"default": "Get"}),
            },
            "optional": {
                "value": ("*", {"forceInput": True}),
                "inherit": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("*", "STRING", "BOOLEAN")
    RETURN_NAMES = ("result", "source_scope", "success")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Workflow"
    
    def run(self, config_name, scope, key, mode, value=None, inherit=True):
        """
        Execute the configured operation (Get, Set, or Delete) on the session registry.
        
        Args:
            config_name: Name of the saved configuration profile.
            scope: The scope ("Global", "Pipeline", "Node").
            key: The parameter key to set/get/delete.
            mode: The operation mode ("Get", "Set", "Delete").
            value: The value to set (only used in Set mode).
            inherit: Whether to inherit from broader scopes (only used in Get mode).
        
        Returns:
            Tuple of (result, source_scope, success)
        """
        # Validate inputs
        if not isinstance(config_name, str) or not config_name.strip():
            return (None, "error", False)
        
        if scope not in _ALLOWED_SCOPES:
            return (None, "error", False)
        
        if not isinstance(key, str) or not key.strip():
            return (None, "error", False)
        
        if mode not in _ALLOWED_MODES:
            return (None, "error", False)
        
        # Perform the operation
        if mode == "Get":
            found, val, source_scope = _get_inherited_value(config_name, scope, key, inherit)
            if found:
                return (val, source_scope, True)
            else:
                return (None, "not_found", False)
        
        elif mode == "Set":
            success = _set_value(config_name, scope, key, value)
            if success:
                return (True, scope, True)
            else:
                return (None, "error", False)
        
        elif mode == "Delete":
            success = _delete_value(config_name, scope, key)
            if success:
                return (True, scope, True)
            else:
                return (None, "not_found", False)
        
        return (None, "error", False)


# Module-level mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_Workflow_Configurator": PSN_Workflow_Configurator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Workflow_Configurator": "PSN Workflow Configurator"
}
