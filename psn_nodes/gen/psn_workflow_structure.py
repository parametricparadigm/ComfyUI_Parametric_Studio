"""PSN_Workflow_Structure: Enforce a logical structure (Loader, Controller, Sampler) in complex workflows.

This module provides a pure-logic, secure-by-design node that validates the presence of expected
inputs and organizes them into a standard dictionary for the next stage. It acts as a pass-through
node that ensures the data flow follows the pattern: Loader -> Controller -> Sampler.

No GPU, torch, ComfyUI internals, network, file I/O, or subprocess usage. Only pure Python standard
library (json) is used for serialization/validation.
"""

import json

class _AnyType(str):
    """ComfyUI wildcard socket type: compares equal to every type."""
    def __ne__(self, other): return False
ANY = _AnyType("*")


CAT = "ParametricStudio/Structure"


class PSN_WorkflowStructure:
    """Enforce a logical structure (Loader, Controller, Sampler) in complex workflows.

    Validates the presence of expected inputs and organizes them into a standard dictionary.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "loader_output": (ANY,),
                "controller_settings": ("DICT",),
                "sampler_input": (ANY,),
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
        """Validate and organize workflow structure.

        Args:
            loader_output: Output from the Loader section.
            controller_settings: Settings from the Controller section (must be a dict).
            sampler_input: Input to the Sampler section.
            log_structure: If True, include a serialized structure summary in the output.

        Returns:
            Tuple of (structured_data, validation_status)
        """
        # Validate controller_settings is a dict
        if not isinstance(controller_settings, dict):
            return ({}, False)

        # Validate that all required inputs are present (not None)
        if loader_output is None or sampler_input is None:
            return ({}, False)

        # Build the structured data
        structured_data = {
            "loader": loader_output,
            "controller": controller_settings,
            "sampler": sampler_input,
        }

        # Optionally include a serialized structure summary for debugging
        if log_structure:
            try:
                # Create a safe summary that only includes types and keys, not full values
                summary = {
                    "loader_type": type(loader_output).__name__,
                    "controller_keys": list(controller_settings.keys()),
                    "sampler_type": type(sampler_input).__name__,
                }
                structured_data["structure_summary"] = json.dumps(summary, sort_keys=True)
            except (TypeError, ValueError):
                # If serialization fails, just omit the summary
                pass

        return (structured_data, True)


# ComfyUI node mappings
NODE_CLASS_MAPPINGS = {
    "PSN_WorkflowStructure": PSN_WorkflowStructure,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_WorkflowStructure": "PSN Workflow Structure",
}
