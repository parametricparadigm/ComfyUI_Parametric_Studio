"""
PSN Workflow State Management nodes.

This module provides pure-logic, secure-by-design state management nodes for
ComfyUI workflows. It implements:

- PSN_State_Container: Stores a value in a session-scoped in-memory state
  dictionary keyed by a string key.
- PSN_State_Retriever: Retrieves a value from a state dictionary with a
  default fallback.
- PSN_Iteration_Toggle: Alternates between two values based on iteration
  parity and reports whether the current iteration is the last one.

All state is held in a module-level dictionary (session-only; lost on
re-queue). No GPU, torch, ComfyUI internals, network, file I/O, or
subprocess usage is performed. All functions take and return plain Python
values (strings, numbers, dicts, booleans, or arbitrary hashable/plain
objects).
"""

# ComfyUI uses the string "ANY" as a type marker for arbitrary inputs/outputs.
# We define it locally so the module is self-contained and testable without
# importing ComfyUI internals.
ANY = "ANY"

# Session-scoped state store. Lost when the process restarts or the
# workflow is re-queued.
_STATE_STORE = {}


def _psn_state_store():
    """Return the module-level state dictionary (for testing/inspection)."""
    return _STATE_STORE


def _psn_state_clear():
    """Clear the module-level state dictionary (for testing)."""
    _STATE_STORE.clear()


class PSN_State_Container:
    """Stores a value in a session-scoped state dictionary keyed by `key`."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": "state_key"}),
                "value": (ANY,),
            }
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("state",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/State"

    def run(self, key, value):
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        if not key:
            raise ValueError("key must be a non-empty string")
        _STATE_STORE[key] = value
        return (dict(_STATE_STORE),)


class PSN_State_Retriever:
    """Retrieves a value from a state dictionary, returning `default` if absent."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state": ("DICT",),
                "key": ("STRING", {"default": "state_key"}),
                "default": (ANY,),
            }
        }

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("value",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/State"

    def run(self, state, key, default):
        if not isinstance(state, dict):
            raise TypeError("state must be a dict")
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        if key in state:
            return (state[key],)
        return (default,)


class PSN_Iteration_Toggle:
    """
    Alternates between `mode_a` (even iterations) and `mode_b` (odd iterations)
    based on `current_iteration` parity. Reports whether this is the last
    iteration.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "current_iteration": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "total_iterations": ("INT", {"default": 1, "min": 1, "max": 1000000, "step": 1}),
                "mode_a": (ANY,),
                "mode_b": (ANY,),
            }
        }

    RETURN_TYPES = (ANY, "BOOLEAN")
    RETURN_NAMES = ("selected_value", "is_last_iteration")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/State"

    def run(self, current_iteration, total_iterations, mode_a, mode_b):
        if not isinstance(current_iteration, int) or isinstance(current_iteration, bool):
            raise TypeError("current_iteration must be an integer")
        if not isinstance(total_iterations, int) or isinstance(total_iterations, bool):
            raise TypeError("total_iterations must be an integer")
        if current_iteration < 0:
            raise ValueError("current_iteration must be >= 0")
        if total_iterations < 1:
            raise ValueError("total_iterations must be >= 1")

        is_last = (current_iteration == total_iterations)
        if current_iteration % 2 == 0:
            selected = mode_a
        else:
            selected = mode_b
        return (selected, is_last)


NODE_CLASS_MAPPINGS = {
    "PSN_State_Container": PSN_State_Container,
    "PSN_State_Retriever": PSN_State_Retriever,
    "PSN_Iteration_Toggle": PSN_Iteration_Toggle,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_State_Container": "PSN State Container",
    "PSN_State_Retriever": "PSN State Retriever",
    "PSN_Iteration_Toggle": "PSN Iteration Toggle",
}
