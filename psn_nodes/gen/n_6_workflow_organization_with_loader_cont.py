"""PSN Workflow Organization: Loader -> Controller -> Sampler structure node.

This module provides a pass-through node that validates the presence of
expected inputs and organizes them into a standard dictionary for the
next stage in a ComfyUI workflow.
"""

import json
import torch

CAT = "ParametricStudio/Workflow"


def _is_tensor(x):
    """Check if x is a torch tensor."""
    return isinstance(x, torch.Tensor)


def _tensor_summary(x):
    """Return a short summary string for a tensor."""
    if _is_tensor(x):
        return f"Tensor(shape={list(x.shape)}, dtype={x.dtype})"
    return f"{type(x).__name__}"


def _validate_loader(loader_output):
    """Validate the loader output. Accepts tensors, dicts, lists, strings, numbers."""
    if loader_output is None:
        return False, "loader_output is None"
    if _is_tensor(loader_output):
        return True, f"tensor {_tensor_summary(loader_output)}"
    if isinstance(loader_output, (dict, list, str, int, float, bool)):
        return True, f"{type(loader_output).__name__}"
    return False, f"unsupported loader type: {type(loader_output).__name__}"


def _validate_controller(controller_settings):
    """Validate controller settings: must be a dict (or None for defaults)."""
    if controller_settings is None:
        return True, "default settings"
    if isinstance(controller_settings, dict):
        return True, f"dict with {len(controller_settings)} keys"
    return False, f"controller_settings must be a dict, got {type(controller_settings).__name__}"


def _validate_sampler(sampler_input):
    """Validate sampler input. Accepts tensors, dicts, lists, strings, numbers."""
    if sampler_input is None:
        return False, "sampler_input is None"
    if _is_tensor(sampler_input):
        return True, f"tensor {_tensor_summary(sampler_input)}"
    if isinstance(sampler_input, (dict, list, str, int, float, bool)):
        return True, f"{type(sampler_input).__name__}"
    return False, f"unsupported sampler type: {type(sampler_input).__name__}"


class PSN_Workflow_Structure:
    """Enforce a logical structure (Loader, Controller, Sampler) in complex workflows.

    Acts as a pass-through node that validates the presence of expected inputs
    and organizes them into a standard dictionary. Can also log the structure
    for debugging.

    Data Flow: Loader -> Controller -> Sampler (via this node).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "loader_output": ("ANY",),
                "controller_settings": ("DICT",),
                "sampler_input": ("ANY",),
            },
            "optional": {
                "log_structure": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("DICT", "BOOLEAN")
    RETURN_NAMES = ("structured_data", "validation_status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, loader_output, controller_settings, sampler_input, log_structure=False):
        """Validate and organize inputs into a standard structure dictionary."""
        # Validate each input
        loader_ok, loader_msg = _validate_loader(loader_output)
        controller_ok, controller_msg = _validate_controller(controller_settings)
        sampler_ok, sampler_msg = _validate_sampler(sampler_input)

        all_valid = loader_ok and controller_ok and sampler_ok

        # Build the structured data dictionary
        structured = {
            "loader": {
                "data": loader_output,
                "valid": loader_ok,
                "info": loader_msg,
            },
            "controller": {
                "settings": controller_settings if controller_settings is not None else {},
                "valid": controller_ok,
                "info": controller_msg,
            },
            "sampler": {
                "data": sampler_input,
                "valid": sampler_ok,
                "info": sampler_msg,
            },
            "structure": "Loader -> Controller -> Sampler",
            "all_valid": all_valid,
        }

        # Optionally log the structure for debugging
        if log_structure:
            log_lines = [
                "=== PSN_Workflow_Structure ===",
                f"  Loader:    {'OK' if loader_ok else 'FAIL'} - {loader_msg}",
                f"  Controller:{'OK' if controller_ok else 'FAIL'} - {controller_msg}",
                f"  Sampler:   {'OK' if sampler_ok else 'FAIL'} - {sampler_msg}",
                f"  All valid: {all_valid}",
            ]
            # We cannot print in ComfyUI nodes, but we store the log in the dict
            structured["log"] = "\n".join(log_lines)

        return (structured, all_valid)


# Module-level mappings required by ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_Workflow_Structure": PSN_Workflow_Structure,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Workflow_Structure": "PSN Workflow Structure (Loader-Controller-Sampler)",
}
