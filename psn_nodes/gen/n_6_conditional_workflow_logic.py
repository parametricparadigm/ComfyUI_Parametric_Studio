"""
Conditional Workflow Logic nodes for ParametricStudio.

This module provides pure-logic nodes for boolean operations and type casting.
It does not use torch, ComfyUI internals, network, file I/O, or subprocess.
All operations are safe-by-design and operate on plain Python values.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Logic"

# Placeholder for ComfyUI's ANY type; in a real ComfyUI environment this would be imported.
# For this pure-logic module, we define it as a string marker.
ANY = "ANY"

# --- PSN_Boolean_Logic ---

class PSN_Boolean_Logic:
    """
    Performs a boolean operation (AND, OR, NOT, XOR) on inputs a and b.
    For NOT, only input a is used; b is ignored.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("BOOLEAN", {"default": False}),
                "b": ("BOOLEAN", {"default": False}),
                "operation": (["AND", "OR", "NOT", "XOR"],),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("result",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, a, b, operation):
        a = bool(a)
        b = bool(b)
        if operation == "AND":
            result = a and b
        elif operation == "OR":
            result = a or b
        elif operation == "NOT":
            result = not a
        elif operation == "XOR":
            result = a != b
        else:
            raise ValueError(f"Unknown operation: {operation}")
        return (result,)


# --- PSN_Type_Caster ---

class PSN_Type_Caster:
    """
    Converts an input value to a target type (STRING, INT, FLOAT, BOOLEAN).
    On failure, returns the specified default value.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": (ANY,),
                "target_type": (["STRING", "INT", "FLOAT", "BOOLEAN"],),
                "default_value": (ANY,),
            }
        }

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("casted_value",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, value, target_type, default_value):
        try:
            if target_type == "STRING":
                result = str(value)
            elif target_type == "INT":
                if isinstance(value, bool):
                    result = int(value)
                elif isinstance(value, float):
                    result = int(value)
                elif isinstance(value, str):
                    result = int(value.strip())
                else:
                    result = int(value)
            elif target_type == "FLOAT":
                if isinstance(value, bool):
                    result = float(value)
                elif isinstance(value, int):
                    result = float(value)
                elif isinstance(value, str):
                    result = float(value.strip())
                else:
                    result = float(value)
            elif target_type == "BOOLEAN":
                if isinstance(value, bool):
                    result = value
                elif isinstance(value, (int, float)):
                    result = bool(value)
                elif isinstance(value, str):
                    v = value.strip().lower()
                    if v in ("true", "1", "yes", "on"):
                        result = True
                    elif v in ("false", "0", "no", "off"):
                        result = False
                    else:
                        raise ValueError(f"Cannot cast string '{value}' to BOOLEAN")
                else:
                    # None or other types that are not bool/int/float/str
                    # Treat as invalid for strict boolean casting
                    raise ValueError(f"Cannot cast {type(value).__name__} to BOOLEAN")
            else:
                raise ValueError(f"Unknown target type: {target_type}")
        except (ValueError, TypeError, OverflowError):
            result = default_value
        return (result,)


NODE_CLASS_MAPPINGS = {
    "PSN_Boolean_Logic": PSN_Boolean_Logic,
    "PSN_Type_Caster": PSN_Type_Caster,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Boolean_Logic": "Boolean Logic",
    "PSN_Type_Caster": "Type Caster",
}
