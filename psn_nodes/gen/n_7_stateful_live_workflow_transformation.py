"""
Stateful Live Workflow Transformation nodes.

This module implements a pure-logic, secure-by-design stateful loop for
ComfyUI. It transforms one-shot generation processes into continuous,
live-updating workflows that respond to new inputs.

No GPU, torch, ComfyUI internals, network, file I/O, or OS access is used.
The state is a plain Python dict that tracks:
  - 'value': the current accumulated state value
  - 'history': a bounded list of recent (input, output) pairs
  - 'step': the number of updates processed
  - 'last_input': the most recent input received

The 'PSN_Live_State_Loop' node does NOT actually sleep or block; it
simulates a wait/timeout decision based on whether new input is pending,
returning a 'continue' flag. This keeps the logic pure and testable.
"""

from psn import expr, orchestration as _orch

# In ComfyUI, ANY is a special type constant. Since we cannot import from
# ComfyUI directly, we define a placeholder string that represents "any type".
# In a real ComfyUI environment, this would be imported from comfy.
ANY = "ANY"

CAT = "ParametricStudio/Live"

# Maximum history length to prevent unbounded memory growth
_MAX_HISTORY = 100


def _make_initial_state(initial_state):
    """Create a well-formed state dict from an arbitrary initial value."""
    if isinstance(initial_state, dict):
        state = dict(initial_state)
    else:
        state = {}
    state.setdefault("value", initial_state if not isinstance(initial_state, dict) else None)
    state.setdefault("history", [])
    state.setdefault("step", 0)
    state.setdefault("last_input", None)
    # Enforce bounded history
    if len(state["history"]) > _MAX_HISTORY:
        state["history"] = state["history"][-_MAX_HISTORY:]
    return state


def _apply_update(state, new_input):
    """
    Process a new input against the current state.
    Returns (updated_state, output).
    The output is the new accumulated value.
    """
    if not isinstance(state, dict):
        state = _make_initial_state(state)

    current_value = state.get("value", None)
    step = state.get("step", 0) + 1

    # Simple accumulation logic: if both are numeric, sum; otherwise,
    # the new input replaces the value (last-write-wins).
    if isinstance(current_value, (int, float)) and isinstance(new_input, (int, float)):
        new_value = current_value + new_input
    elif isinstance(current_value, str) and isinstance(new_input, str):
        new_value = current_value + new_input
    else:
        new_value = new_input

    history = list(state.get("history", []))
    history.append({"input": new_input, "output": new_value})
    if len(history) > _MAX_HISTORY:
        history = history[-_MAX_HISTORY:]

    updated_state = {
        "value": new_value,
        "history": history,
        "step": step,
        "last_input": new_input,
    }
    return updated_state, new_value


def _loop_decision(state, wait_ms):
    """
    Simulate a wait/timeout decision.
    Returns (state, continue_flag, reason).
    If wait_ms <= 0, we assume input is always available (continue=True).
    If wait_ms > 0, we check if the state has a pending input marker.
    For pure logic, we treat 'continue' as True if step > 0 (we've done work)
    or if wait_ms is 0 (immediate polling).
    """
    if not isinstance(state, dict):
        state = _make_initial_state(state)

    step = state.get("step", 0)
    # In a real system, this would check a queue. Here, we continue
    # if we have processed at least one step, or if wait_ms is 0.
    if wait_ms <= 0:
        continue_flag = True
        reason = "immediate_poll"
    elif step > 0:
        continue_flag = True
        reason = "has_processed_input"
    else:
        continue_flag = False
        reason = "timeout_no_input"

    return state, continue_flag, reason


class PSN_Live_State_Init:
    """Initializes the stateful live workflow loop with an initial state value."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "initial_state": (ANY,),
            }
        }

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("state",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, initial_state):
        state = _make_initial_state(initial_state)
        return (state,)


class PSN_Live_State_Update:
    """Processes a new input, updates the state, and emits an output."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state": (ANY,),
                "new_input": (ANY,),
            }
        }

    RETURN_TYPES = (ANY, ANY)
    RETURN_NAMES = ("updated_state", "output")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, state, new_input):
        updated_state, output = _apply_update(state, new_input)
        return (updated_state, output)


class PSN_Live_State_Loop:
    """
    Simulates a wait/timeout decision in the live loop.
    Returns the state and a continue flag indicating whether to loop back.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state": (ANY,),
                "wait_ms": ("INT", {"default": 100, "min": 0, "max": 100000, "step": 1}),
            }
        }

    RETURN_TYPES = (ANY, "BOOLEAN", "STRING")
    RETURN_NAMES = ("state", "continue", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, state, wait_ms):
        state, continue_flag, reason = _loop_decision(state, wait_ms)
        return (state, continue_flag, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Live_State_Init": PSN_Live_State_Init,
    "PSN_Live_State_Update": PSN_Live_State_Update,
    "PSN_Live_State_Loop": PSN_Live_State_Loop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Live_State_Init": "Live State Init",
    "PSN_Live_State_Update": "Live State Update",
    "PSN_Live_State_Loop": "Live State Loop",
}
