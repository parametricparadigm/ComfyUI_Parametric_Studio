"""
Complex Workflow Control Flow nodes for ParametricStudio.

This module provides pure-logic nodes for managing complex control flow in ComfyUI workflows.
It implements list filtering and set operations to help skip invalid data or manage
conditional execution paths without requiring GPU/torch/ComfyUI internals.

Nodes:
- PSN_List_Filter: Filters a list based on conditions (is_not_none, is_not_empty, custom).
- PSN_Set_Operation: Performs set operations (union, intersection, difference).

All functions take plain values (lists, sets, strings) and return plain values.
No file I/O, network access, or external dependencies are used.
"""

from typing import Any, List, Set, Tuple

# Category for these nodes
CAT = "ParametricStudio/ControlFlow"

# Valid condition types for list filtering
CONDITION_TYPES = ["is_not_none", "is_not_empty", "custom"]

# Valid set operations
SET_OPERATIONS = ["union", "intersection", "difference"]


def _is_not_none(item: Any) -> bool:
    """Check if item is not None."""
    return item is not None


def _is_not_empty(item: Any) -> bool:
    """Check if item is not empty (None, empty string, empty list, empty dict, etc.)."""
    if item is None:
        return False
    if isinstance(item, (str, list, dict, set, tuple)):
        return len(item) > 0
    # For other types, consider them non-empty if they are not None
    return True


def _apply_custom_filter(item: Any, custom_func: str) -> bool:
    """
    Apply a custom filter function specified by name.
    Only supports a limited set of safe built-in checks.
    """
    if not custom_func or not isinstance(custom_func, str):
        return True  # If no custom func specified, keep the item
    
    func_name = custom_func.strip().lower()
    
    # Safe allow-list of custom filter functions
    if func_name == "is_string":
        return isinstance(item, str)
    elif func_name == "is_number":
        return isinstance(item, (int, float)) and not isinstance(item, bool)
    elif func_name == "is_list":
        return isinstance(item, list)
    elif func_name == "is_dict":
        return isinstance(item, dict)
    elif func_name == "is_bool":
        return isinstance(item, bool)
    elif func_name == "is_positive":
        return isinstance(item, (int, float)) and not isinstance(item, bool) and item > 0
    elif func_name == "is_negative":
        return isinstance(item, (int, float)) and not isinstance(item, bool) and item < 0
    elif func_name == "is_zero":
        return isinstance(item, (int, float)) and not isinstance(item, bool) and item == 0
    elif func_name == "is_even":
        return isinstance(item, int) and not isinstance(item, bool) and item % 2 == 0
    elif func_name == "is_odd":
        return isinstance(item, int) and not isinstance(item, bool) and item % 2 != 0
    elif func_name == "is_true":
        return item is True
    elif func_name == "is_false":
        return item is False
    else:
        # Unknown custom function - keep the item by default
        return True


class PSN_List_Filter:
    """
    Filters an input list based on a specified condition.
    
    Conditions:
    - is_not_none: Removes None values
    - is_not_empty: Removes empty values (None, empty strings, empty lists, etc.)
    - custom: Uses a custom filter function specified by name
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_list": ("LIST",),
                "condition_type": (CONDITION_TYPES,),
            },
            "optional": {
                "custom_func": ("STRING", {"default": "", "multiline": False}),
            }
        }
    
    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("filtered_list",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, input_list: List[Any], condition_type: str, custom_func: str = "") -> Tuple[List[Any]]:
        """
        Filter the input list based on the condition type.
        
        Args:
            input_list: The list to filter
            condition_type: One of "is_not_none", "is_not_empty", "custom"
            custom_func: Name of the custom filter function (only used if condition_type is "custom")
        
        Returns:
            Tuple containing the filtered list
        """
        if not isinstance(input_list, list):
            # If input is not a list, wrap it in a list
            input_list = [input_list]
        
        filtered = []
        for item in input_list:
            if condition_type == "is_not_none":
                if _is_not_none(item):
                    filtered.append(item)
            elif condition_type == "is_not_empty":
                if _is_not_empty(item):
                    filtered.append(item)
            elif condition_type == "custom":
                if _apply_custom_filter(item, custom_func):
                    filtered.append(item)
            else:
                # Unknown condition type - keep all items
                filtered.append(item)
        
        return (filtered,)


class PSN_Set_Operation:
    """
    Performs set operations on two sets.
    
    Operations:
    - union: Returns the union of both sets
    - intersection: Returns the intersection of both sets
    - difference: Returns elements in set_a that are not in set_b
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "set_a": ("SET",),
                "set_b": ("SET",),
                "operation": (SET_OPERATIONS,),
            }
        }
    
    RETURN_TYPES = ("SET",)
    RETURN_NAMES = ("result_set",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, set_a: Set[Any], set_b: Set[Any], operation: str) -> Tuple[Set[Any]]:
        """
        Perform the specified set operation.
        
        Args:
            set_a: The first set
            set_b: The second set
            operation: One of "union", "intersection", "difference"
        
        Returns:
            Tuple containing the result set
        """
        # Ensure inputs are sets
        if not isinstance(set_a, set):
            set_a = set(set_a) if hasattr(set_a, '__iter__') else {set_a}
        if not isinstance(set_b, set):
            set_b = set(set_b) if hasattr(set_b, '__iter__') else {set_b}
        
        if operation == "union":
            result = set_a | set_b
        elif operation == "intersection":
            result = set_a & set_b
        elif operation == "difference":
            result = set_a - set_b
        else:
            # Unknown operation - return empty set
            result = set()
        
        return (result,)


# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_List_Filter": PSN_List_Filter,
    "PSN_Set_Operation": PSN_Set_Operation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_List_Filter": "PSN List Filter",
    "PSN_Set_Operation": "PSN Set Operation",
}
