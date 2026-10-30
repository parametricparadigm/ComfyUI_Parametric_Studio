"""
PSN_Dynamic_Switch: A pure-logic routing node for ComfyUI.

This module implements a dynamic parameter switching node that routes data
from one of multiple inputs to a single output based on a boolean condition
or an index. It is designed to fix issues with nodes getting information
from bypassed nodes by providing explicit, state-based routing.

Pure Python standard library only. No torch, no ComfyUI imports, no network,
no file/OS access, no eval/exec.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Routing"

# Placeholder for ComfyUI's ANY type; in a real ComfyUI environment this
# would be imported from the ComfyUI API. Here we use a string sentinel.
ANY = "ANY"


class PSN_Dynamic_Switch:
    """
    Routes data from one of multiple inputs to a single output based on a
    boolean condition or an index.

    - If `use_index` is False (default), the boolean `condition` selects
      between `input_1` (False) and `input_2` (True).
    - If `use_index` is True, the integer `index` selects among all provided
      inputs (1-based: 1=input_1, 2=input_2, 3=input_3, 4=input_4).
      Out-of-range indices fall back to `input_1`.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_1": (ANY,),
                "input_2": (ANY,),
                "condition": ("BOOLEAN", {"default": False}),
                "use_index": ("BOOLEAN", {"default": False}),
                "index": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
            },
            "optional": {
                "input_3": (ANY,),
                "input_4": (ANY,),
            },
        }

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, input_1, input_2, condition, use_index, index, input_3=None, input_4=None):
        """
        Select the appropriate input based on mode.

        Args:
            input_1: First data stream.
            input_2: Second data stream.
            condition: Boolean condition for 2-way switching.
            use_index: If True, use index-based selection; otherwise use condition.
            index: 1-based index for multi-switch (1-4).
            input_3: Optional third data stream.
            input_4: Optional fourth data stream.

        Returns:
            The selected data stream.
        """
        if use_index:
            # Clamp index to valid range [1, 4]
            idx = max(1, min(4, int(index)))
            if idx == 1:
                return input_1
            elif idx == 2:
                return input_2
            elif idx == 3:
                return input_3 if input_3 is not None else input_1
            else:  # idx == 4
                return input_4 if input_4 is not None else input_1
        else:
            # Boolean-based 2-way switch
            if condition:
                return input_2
            else:
                return input_1


NODE_CLASS_MAPPINGS = {
    "PSN_Dynamic_Switch": PSN_Dynamic_Switch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Dynamic_Switch": "PSN Dynamic Switch",
}
