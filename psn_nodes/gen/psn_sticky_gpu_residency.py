"""
PSN_Sticky_GPU_Residency

Pure-logic, secure-by-design implementation of a "sticky GPU residency" policy
for ComfyUI. This module does NOT touch torch, GPU, or ComfyUI internals.
It models the residency policy as a state machine over a plain Python
representation of a model's weight tensors (dict of name -> device string).

The node validates inputs (priority 0-10, sticky flag), computes the
residency decision (whether a tensor should stay on GPU or be offloaded),
and returns a policy descriptor plus the updated device map.

Inputs are plain values (numbers, strings, JSON text). No sockets, no file
I/O, no network, no subprocess, no eval/exec.
"""

import json
import re

# Allowed device strings
_VALID_DEVICES = ("cpu", "cuda:0", "cuda:1", "cuda:2", "cuda:3")

# Priority bounds
_PRIORITY_MIN = 0
_PRIORITY_MAX = 10


def _validate_priority(priority):
    """Validate priority is an int in [0, 10]. Returns (ok, error_msg)."""
    if not isinstance(priority, int) or isinstance(priority, bool):
        return False, "priority must be an integer"
    if priority < _PRIORITY_MIN or priority > _PRIORITY_MAX:
        return False, f"priority must be between {_PRIORITY_MIN} and {_PRIORITY_MAX}"
    return True, ""


def _validate_device(device_str):
    """Validate a device string. Returns (ok, error_msg)."""
    if not isinstance(device_str, str):
        return False, "device must be a string"
    if device_str not in _VALID_DEVICES:
        return False, f"device must be one of {_VALID_DEVICES}, got {device_str!r}"
    return True, ""


def _parse_weight_map(weight_map_json):
    """
    Parse a JSON string representing {tensor_name: device_string}.
    Returns (dict, error_msg).
    """
    if not isinstance(weight_map_json, str):
        return None, "weight_map must be a JSON string"
    try:
        data = json.loads(weight_map_json)
    except (json.JSONDecodeError, TypeError) as e:
        return None, f"invalid JSON: {e}"
    if not isinstance(data, dict):
        return None, "weight_map JSON must be an object"
    for name, dev in data.items():
        if not isinstance(name, str) or not name:
            return None, f"tensor name must be a non-empty string, got {name!r}"
        ok, err = _validate_device(dev)
        if not ok:
            return None, f"tensor {name!r}: {err}"
    return data, ""


def compute_residency_policy(sticky, priority, weight_map):
    """
    Core pure-logic function.

    Given the current device map and residency parameters, compute:
      - new_device_map: dict of tensor_name -> device after applying policy
      - offloaded: list of tensor names that were moved to CPU
      - kept: list of tensor names that stayed on GPU
      - reason: human-readable explanation

    Policy:
      - If sticky is True: all tensors currently on a CUDA device stay on
        that device (no offload). Tensors on CPU remain on CPU.
      - If sticky is False: tensors on CUDA with priority < 5 are offloaded
        to CPU; tensors with priority >= 5 stay. Tensors on CPU stay on CPU.
      - Priority acts as a threshold: higher priority = more likely to stay.

    Returns (new_device_map, offloaded, kept, reason).
    """
    new_map = {}
    offloaded = []
    kept = []

    for name, dev in weight_map.items():
        if dev.startswith("cuda"):
            if sticky:
                new_map[name] = dev
                kept.append(name)
            else:
                if priority >= 5:
                    new_map[name] = dev
                    kept.append(name)
                else:
                    new_map[name] = "cpu"
                    offloaded.append(name)
        else:
            # Already on CPU, stays on CPU
            new_map[name] = dev
            kept.append(name)

    if sticky:
        reason = "sticky=True: all CUDA tensors retained on GPU"
    else:
        reason = (
            f"sticky=False, priority={priority}: "
            f"CUDA tensors with priority<5 offloaded to CPU"
        )

    return new_map, offloaded, kept, reason


def build_policy_descriptor(sticky, priority, weight_map, new_device_map,
                            offloaded, kept, reason):
    """
    Build a JSON-serializable policy descriptor dict.
    """
    return {
        "sticky": bool(sticky),
        "priority": int(priority),
        "original_map": weight_map,
        "new_map": new_device_map,
        "offloaded": offloaded,
        "kept": kept,
        "reason": reason,
    }


class PSN_Sticky_GPU_Residency:
    """
    ComfyUI node that computes a sticky GPU residency policy for model
    weight tensors. Pure logic only; no torch or GPU access.

    Input: weight_map as a JSON string {tensor_name: device}.
    Output: updated device map (JSON string), list of offloaded tensors,
            list of kept tensors, and a reason string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sticky": ("BOOLEAN", {"default": True}),
                "priority": ("INT", {"default": 5, "min": 0, "max": 10, "step": 1}),
                "weight_map": ("STRING", {
                    "default": "{}",
                    "multiline": True,
                    "tooltip": "JSON object mapping tensor names to device strings (cpu, cuda:0, etc.)"
                }),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("new_device_map", "offloaded", "kept", "reason")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/GPU"

    def run(self, sticky, priority, weight_map):
        # Validate priority
        ok, err = _validate_priority(priority)
        if not ok:
            return (json.dumps({}), json.dumps([]), json.dumps([]), f"ERROR: {err}")

        # Parse weight map
        parsed, err = _parse_weight_map(weight_map)
        if parsed is None:
            return (json.dumps({}), json.dumps([]), json.dumps([]), f"ERROR: {err}")

        # Compute policy
        new_map, offloaded, kept, reason = compute_residency_policy(
            sticky, priority, parsed
        )

        return (
            json.dumps(new_map),
            json.dumps(offloaded),
            json.dumps(kept),
            reason,
        )


NODE_CLASS_MAPPINGS = {
    "PSN_Sticky_GPU_Residency": PSN_Sticky_GPU_Residency,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Sticky_GPU_Residency": "PSN Sticky GPU Residency",
}
