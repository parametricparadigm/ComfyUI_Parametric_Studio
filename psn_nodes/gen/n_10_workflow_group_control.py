"""ParametricStudio - Workflow Group Control.

Lightweight group-bypass / node-gate helpers for ComfyUI.

Data flow:  PSN_Group_Bypass  ->  PSN_Node_Gate  ->  (process or pass-through)

The idea is to let a user disable whole groups of nodes (e.g. an audio
branch) without rewiring the graph.  A *group bypass* node emits a single
BOOLEAN signal that is fanned out to every *node gate* in the group.  When
the signal is True the gate passes its input through untouched; when False
the gate applies a small, deterministic transform (here: a no-op identity
for tensors, a normalisation for numbers, a strip for strings) so the
behaviour is observable in tests.

No external dependencies beyond torch (CPU) and the Python stdlib.
"""

import torch

CAT = "ParametricStudio/GroupControl"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_bool(value):
    """Coerce a value to a strict Python bool (rejects ambiguous inputs)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value in (0, 1):
            return bool(value)
        raise ValueError("bypass_signal must be 0/1 or a bool, got %r" % (value,))
    if isinstance(value, torch.Tensor):
        if value.numel() != 1:
            raise ValueError("bypass_signal tensor must be a scalar")
        v = value.item()
        if v in (0, 1):
            return bool(v)
        raise ValueError("bypass_signal tensor must be 0/1, got %r" % (v,))
    raise TypeError("bypass_signal must be bool/0/1, got %s" % type(value).__name__)


def _process(value):
    """The 'processing' half of a gate.

    Deterministic, cheap, and type-preserving so the gate is observable:
      * torch.Tensor  -> clone (never mutate) and, for float tensors, clamp
                         to [0, 1] (matches ComfyUI IMAGE/MASK conventions)
      * int/float     -> round to 4 decimals
      * str           -> strip surrounding whitespace
      * list/tuple    -> element-wise processing
      * dict          -> shallow copy with processed values
      * None / other  -> returned unchanged
    """
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        out = value.clone()
        if out.is_floating_point():
            out = torch.clamp(out, 0.0, 1.0)
        return out
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        processed = [_process(v) for v in value]
        return tuple(processed) if isinstance(value, tuple) else processed
    if isinstance(value, dict):
        return {k: _process(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

class PSN_Group_Bypass:
    """Emit a bypass signal for a named workflow group.

    When `enabled` is False the group is considered *bypassed*, so the
    output signal is True (gates will pass their inputs through).  When
    `enabled` is True the group runs normally and the signal is False.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "group_id": ("STRING", {"default": "group_a", "multiline": False}),
                "enabled": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("bypass_signal",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, group_id, enabled):
        if not isinstance(group_id, str):
            raise TypeError("group_id must be a string")
        if not group_id.strip():
            raise ValueError("group_id must be a non-empty string")
        enabled = _as_bool(enabled)
        # bypass = group is disabled
        return (not enabled,)


class PSN_Node_Gate:
    """Gate a single node's input behind a bypass signal.

    bypass_signal True  -> pass `input` through unchanged (skip processing)
    bypass_signal False -> apply the group's processing transform
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("*",),
                "bypass_signal": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, input, bypass_signal):
        bypass = _as_bool(bypass_signal)
        if bypass:
            return (input,)
        return (_process(input),)


NODE_CLASS_MAPPINGS = {
    "PSN_Group_Bypass": PSN_Group_Bypass,
    "PSN_Node_Gate": PSN_Node_Gate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Group_Bypass": "Group Bypass (ParametricStudio)",
    "PSN_Node_Gate": "Node Gate (ParametricStudio)",
}
