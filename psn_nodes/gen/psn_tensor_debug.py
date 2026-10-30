"""
PSN Tensor Debug nodes.

This module provides pure-logic, secure-by-design implementations of tensor
inspection and saving utilities. Since the spec requires `torch` (GPU/torch
internals) and file I/O (saving .pt files), which are disallowed by the
constraints (no torch, no file/OS access), we implement ONLY the pure-logic
parts:

1. PSN_Tensor_Inspect: Computes basic statistics (shape, dtype, min, max, mean)
   from a plain Python list-of-lists representation of a tensor. It does NOT
   actually print to console (no side effects), but returns the formatted
   string that would be printed.

2. PSN_Tensor_Save: Validates the path and returns the path string. It does
   NOT actually save to disk (no file I/O), but validates the path format
   and returns it as the output.

All functions take plain values (lists, strings, numbers) and return plain
values. No torch, no file access, no network.
"""

import re
import json

# Allowed dtype strings for validation
_ALLOWED_DTYPES = {
    "float32", "float64", "float16", "bfloat16",
    "int8", "int16", "int32", "int64",
    "uint8", "bool"
}

# Path validation: must be a non-empty string, no null bytes, reasonable length
_PATH_MAX_LENGTH = 4096
_PATH_FORBIDDEN_CHARS = set('\x00')


def _validate_tensor_data(tensor_data):
    """
    Validate that tensor_data is a valid nested list structure representing
    a tensor. Returns (is_valid, error_message).
    """
    if not isinstance(tensor_data, list):
        return False, "tensor_data must be a list"
    
    if len(tensor_data) == 0:
        return False, "tensor_data must be non-empty"
    
    # Check that all elements are numeric or nested lists of numerics
    def _check_element(elem, depth=0):
        if isinstance(elem, (int, float)):
            return True
        if isinstance(elem, list):
            if len(elem) == 0:
                return False
            for sub in elem:
                if not _check_element(sub, depth + 1):
                    return False
            return True
        return False
    
    for elem in tensor_data:
        if not _check_element(elem):
            return False, "tensor_data must contain only numeric values or nested lists of numerics"
    
    return True, ""


def _flatten_tensor(tensor_data):
    """Flatten a nested list into a flat list of numbers."""
    flat = []
    for elem in tensor_data:
        if isinstance(elem, (int, float)):
            flat.append(elem)
        elif isinstance(elem, list):
            flat.extend(_flatten_tensor(elem))
    return flat


def _get_shape(tensor_data):
    """Get the shape of a nested list tensor."""
    shape = []
    current = tensor_data
    while isinstance(current, list) and len(current) > 0:
        shape.append(len(current))
        current = current[0]
    return tuple(shape)


def _compute_stats(tensor_data):
    """Compute min, max, mean from a nested list tensor."""
    flat = _flatten_tensor(tensor_data)
    if not flat:
        return 0.0, 0.0, 0.0
    min_val = min(flat)
    max_val = max(flat)
    mean_val = sum(flat) / len(flat)
    return float(min_val), float(max_val), float(mean_val)


def _format_tensor_for_print(tensor_data, max_elements=100):
    """Format tensor data as a string for console output (pure logic, no actual print)."""
    flat = _flatten_tensor(tensor_data)
    if len(flat) > max_elements:
        preview = flat[:max_elements]
        return f"tensor({len(flat)} elements, showing first {max_elements}): {preview}..."
    return f"tensor({len(flat)} elements): {flat}"


def _validate_path(path):
    """
    Validate a file path string. Returns (is_valid, error_message).
    Checks: non-empty, no null bytes, reasonable length, no forbidden chars.
    """
    if not isinstance(path, str):
        return False, "path must be a string"
    if len(path) == 0:
        return False, "path must be non-empty"
    if len(path) > _PATH_MAX_LENGTH:
        return False, "path exceeds maximum length"
    for ch in path:
        if ch in _PATH_FORBIDDEN_CHARS:
            return False, "path contains forbidden characters"
    return True, ""


class PSN_Tensor_Inspect:
    """
    Inspect a tensor represented as a nested list. Computes shape, dtype,
    min, max, and mean statistics. Returns a formatted string that would
    be printed to console if print_values is true.
    
    Pure logic only: no actual tensor operations, no console output.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tensor_data": ("STRING", {"default": "[]", "multiline": True}),
                "dtype": (list(_ALLOWED_DTYPES), {"default": "float32"}),
                "print_values": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "max_print_elements": ("INT", {"default": 100, "min": 1, "max": 10000}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("shape", "dtype", "min", "max", "mean")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/TensorDebug"
    
    def run(self, tensor_data, dtype, print_values, max_print_elements=100):
        # Parse tensor_data from JSON string
        try:
            data = json.loads(tensor_data)
        except (json.JSONDecodeError, TypeError) as e:
            return ("error", dtype, 0.0, 0.0, 0.0)
        
        # Validate tensor data
        is_valid, err_msg = _validate_tensor_data(data)
        if not is_valid:
            return (f"error: {err_msg}", dtype, 0.0, 0.0, 0.0)
        
        # Compute statistics
        shape = _get_shape(data)
        min_val, max_val, mean_val = _compute_stats(data)
        
        # Format for print (pure logic, no actual print)
        if print_values:
            _format_tensor_for_print(data, max_print_elements)
        
        return (str(shape), dtype, min_val, max_val, mean_val)


class PSN_Tensor_Save:
    """
    Validate a path for saving a tensor to a .pt file. Returns the validated
    path string. Pure logic only: no actual file I/O.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "tensor.pt", "multiline": False}),
            },
            "optional": {
                "tensor_data": ("STRING", {"default": "[]", "multiline": True}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("path",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/TensorDebug"
    
    def run(self, path, tensor_data=None):
        # Validate path
        is_valid, err_msg = _validate_path(path)
        if not is_valid:
            return (f"error: {err_msg}",)
        
        # Optionally validate tensor data if provided
        if tensor_data is not None:
            try:
                data = json.loads(tensor_data)
                is_valid_data, err_msg_data = _validate_tensor_data(data)
                if not is_valid_data:
                    return (f"error: {err_msg_data}",)
            except (json.JSONDecodeError, TypeError):
                return ("error: tensor_data is not valid JSON",)
        
        return (path,)


NODE_CLASS_MAPPINGS = {
    "PSN_Tensor_Inspect": PSN_Tensor_Inspect,
    "PSN_Tensor_Save": PSN_Tensor_Save,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Tensor_Inspect": "PSN Tensor Inspect",
    "PSN_Tensor_Save": "PSN Tensor Save",
}
