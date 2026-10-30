"""PSN_Latent_Forensics: pure-logic latent integrity forensics.

This module implements the secure, pure-Python portion of a latent
forensics node. Because the full spec requires torch/GPU tensor access,
this implementation operates on plain Python values (lists, tuples,
strings, numbers) that represent the *metadata* and *sampled values*
of a latent tensor. It performs:

- NaN / Inf detection on sampled numeric values.
- Shape validation against an expected shape (e.g., (1, 4, 64, 64)).
- Dtype validation against an expected dtype string.
- Generation of a structured integrity report (JSON text).
- A boolean validity flag.

No torch, no ComfyUI imports, no file/network/OS access.
"""

import json
import math

CAT = "ParametricStudio/Forensics"

# Allowed dtype strings for validation
_ALLOWED_DTYPES = ("float16", "float32", "bfloat16", "int8", "uint8")


def _is_nan_or_inf(value):
    """Return True if value is NaN or Inf."""
    if isinstance(value, (int, float)):
        return math.isnan(value) or math.isinf(value)
    return False


def _flatten(values):
    """Recursively flatten a nested list/tuple into a flat list of scalars."""
    flat = []
    if isinstance(values, (list, tuple)):
        for item in values:
            flat.extend(_flatten(item))
    else:
        flat.append(values)
    return flat


def _check_shape(actual_shape, expected_shape):
    """Compare actual shape (tuple of ints) with expected shape.

    Returns (matches: bool, detail: str).
    """
    if not isinstance(actual_shape, (list, tuple)):
        return False, "actual_shape is not a list/tuple"
    if not isinstance(expected_shape, (list, tuple)):
        return False, "expected_shape is not a list/tuple"
    if len(actual_shape) != len(expected_shape):
        return False, f"rank mismatch: actual {len(actual_shape)} vs expected {len(expected_shape)}"
    for i, (a, e) in enumerate(zip(actual_shape, expected_shape)):
        if a != e:
            return False, f"dim {i} mismatch: actual {a} vs expected {e}"
    return True, "shape matches"


def _check_dtype(actual_dtype, expected_dtype):
    """Compare dtype strings. Returns (matches: bool, detail: str)."""
    if actual_dtype not in _ALLOWED_DTYPES:
        return False, f"unknown dtype: {actual_dtype!r}"
    if expected_dtype not in _ALLOWED_DTYPES:
        return False, f"unknown expected dtype: {expected_dtype!r}"
    if actual_dtype != expected_dtype:
        return False, f"dtype mismatch: actual {actual_dtype} vs expected {expected_dtype}"
    return True, "dtype matches"


def _scan_values(sampled_values):
    """Scan a flat list of numeric values for NaN/Inf.

    Returns (has_nan: bool, has_inf: bool, nan_count: int, inf_count: int).
    """
    nan_count = 0
    inf_count = 0
    for v in sampled_values:
        if isinstance(v, (int, float)):
            if math.isnan(v):
                nan_count += 1
            elif math.isinf(v):
                inf_count += 1
    return nan_count > 0, inf_count > 0, nan_count, inf_count


def _build_report(run_id, shape_ok, shape_detail, dtype_ok, dtype_detail,
                  has_nan, has_inf, nan_count, inf_count,
                  actual_shape, expected_shape, actual_dtype, expected_dtype,
                  sampled_count):
    """Build a JSON integrity report string."""
    is_valid = shape_ok and dtype_ok and not has_nan and not has_inf
    report = {
        "run_id": run_id,
        "is_valid": is_valid,
        "shape": {
            "actual": list(actual_shape) if isinstance(actual_shape, (list, tuple)) else str(actual_shape),
            "expected": list(expected_shape) if isinstance(expected_shape, (list, tuple)) else str(expected_shape),
            "matches": shape_ok,
            "detail": shape_detail,
        },
        "dtype": {
            "actual": actual_dtype,
            "expected": expected_dtype,
            "matches": dtype_ok,
            "detail": dtype_detail,
        },
        "values": {
            "sampled_count": sampled_count,
            "has_nan": has_nan,
            "has_inf": has_inf,
            "nan_count": nan_count,
            "inf_count": inf_count,
        },
    }
    return json.dumps(report, indent=2), is_valid


class PSN_LatentForensics:
    """Inspects latent tensor metadata and sampled values for NaNs, Infs,
    and unexpected shape/dtype changes. Pure-logic implementation operating
    on plain Python values (no torch)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_id": ("STRING", {"default": "run_001"}),
                "actual_shape": ("STRING", {"default": "1,4,64,64", "placeholder": "comma-separated dims"}),
                "expected_shape": ("STRING", {"default": "1,4,64,64", "placeholder": "comma-separated dims"}),
                "actual_dtype": (list(_ALLOWED_DTYPES), {"default": "float16"}),
                "expected_dtype": (list(_ALLOWED_DTYPES), {"default": "float16"}),
                "sampled_values": ("STRING", {"default": "[]", "placeholder": "JSON list of numbers"}),
            },
            "optional": {
                "max_sampled": ("INT", {"default": 1024, "min": 1, "max": 100000, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("integrity_report", "is_valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, run_id, actual_shape, expected_shape, actual_dtype, expected_dtype,
            sampled_values, max_sampled=1024):
        # Parse shapes
        try:
            a_shape = tuple(int(x.strip()) for x in actual_shape.split(","))
        except (ValueError, AttributeError):
            a_shape = ()
        try:
            e_shape = tuple(int(x.strip()) for x in expected_shape.split(","))
        except (ValueError, AttributeError):
            e_shape = ()

        # Parse sampled values
        try:
            vals = json.loads(sampled_values)
            if not isinstance(vals, list):
                vals = [vals]
        except (json.JSONDecodeError, TypeError):
            vals = []

        # Flatten and limit
        flat = _flatten(vals)
        if len(flat) > max_sampled:
            flat = flat[:max_sampled]

        # Checks
        shape_ok, shape_detail = _check_shape(a_shape, e_shape)
        dtype_ok, dtype_detail = _check_dtype(actual_dtype, expected_dtype)
        has_nan, has_inf, nan_count, inf_count = _scan_values(flat)

        report, is_valid = _build_report(
            run_id, shape_ok, shape_detail, dtype_ok, dtype_detail,
            has_nan, has_inf, nan_count, inf_count,
            a_shape, e_shape, actual_dtype, expected_dtype,
            len(flat),
        )
        return (report, is_valid)


NODE_CLASS_MAPPINGS = {
    "PSN_LatentForensics": PSN_LatentForensics,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LatentForensics": "PSN Latent Forensics",
}
