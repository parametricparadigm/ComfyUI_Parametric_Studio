"""PSN_Param_Adjuster: blends current workflow parameters with VLM-suggested parameters.

This module implements a pure-logic node that merges two parameter dictionaries
using a blend factor. It does not perform any file I/O, network access, or
GPU operations. All inputs are plain Python values (dicts, floats).

The blending rule is:
    new_value = current_value * (1 - blend_factor) + suggested_value * blend_factor

For non-numeric values, the suggested value is used if blend_factor > 0.5,
otherwise the current value is retained.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Adjust"


class PSN_Param_Adjuster:
    """Applies suggested parameters from PSN_VLM_Analyzer to the next iteration."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "current_params": ("DICT", {}),
                "suggested_params": ("DICT", {}),
                "blend_factor": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("new_params",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, current_params, suggested_params, blend_factor):
        """Blend current and suggested parameters using the given blend factor.

        Args:
            current_params: dict of current workflow parameters.
            suggested_params: dict of VLM-suggested parameters.
            blend_factor: float in [0.0, 1.0]; 0.0 means keep current, 1.0 means use suggested.

        Returns:
            tuple containing the merged parameter dict.
        """
        # Clamp blend_factor to [0, 1] for safety
        blend = max(0.0, min(1.0, float(blend_factor)))

        new_params = {}

        # Collect all keys from both dicts
        all_keys = set(current_params.keys()) | set(suggested_params.keys())

        for key in all_keys:
            in_current = key in current_params
            in_suggested = key in suggested_params

            if in_current and in_suggested:
                cur_val = current_params[key]
                sug_val = suggested_params[key]

                # If both are numeric, blend them
                if isinstance(cur_val, (int, float)) and isinstance(sug_val, (int, float)):
                    new_val = cur_val * (1.0 - blend) + sug_val * blend
                    # Preserve int type if both were int and blend is 0 or 1
                    if isinstance(cur_val, int) and isinstance(sug_val, int) and blend in (0.0, 1.0):
                        new_val = int(round(new_val))
                    new_params[key] = new_val
                else:
                    # Non-numeric: use suggested if blend > 0.5, else current
                    if blend > 0.5:
                        new_params[key] = sug_val
                    else:
                        new_params[key] = cur_val

            elif in_current:
                # Only in current: keep it, but scale numeric values toward 0 if blend > 0
                cur_val = current_params[key]
                if isinstance(cur_val, (int, float)) and blend > 0.0:
                    new_val = cur_val * (1.0 - blend)
                    if isinstance(cur_val, int) and blend == 1.0:
                        new_val = 0
                    new_params[key] = new_val
                else:
                    new_params[key] = cur_val

            elif in_suggested:
                # Only in suggested: include it, scaled by blend if numeric
                sug_val = suggested_params[key]
                if isinstance(sug_val, (int, float)) and blend < 1.0:
                    new_val = sug_val * blend
                    if isinstance(sug_val, int) and blend == 0.0:
                        new_val = 0
                    new_params[key] = new_val
                else:
                    new_params[key] = sug_val

        return (new_params,)


NODE_CLASS_MAPPINGS = {
    "PSN_Param_Adjuster": PSN_Param_Adjuster,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Param_Adjuster": "PSN Param Adjuster",
}
