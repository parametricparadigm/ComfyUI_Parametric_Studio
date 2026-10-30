"""PSN_ScRNA_Normalize: pure-logic normalization of a single-cell expression matrix.

This module implements the *mathematical* core of sc.pp.normalize_total + sc.pp.log1p
without depending on scanpy, torch, or any I/O. It operates on a plain 2D list of
floats (the expression matrix) and returns a new normalized matrix plus metadata.

The AnnData object is represented here as a dict with at least:
    {"X": [[...], ...], "n_obs": int, "n_vars": int}
The node accepts that dict (or a plain 2D list) and returns a dict of the same shape
with the normalized matrix under "X".

No file, network, subprocess, or GPU access is performed.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/SingleCell"

# Allowed modes for the gate (kept for consistency with other PSN nodes)
_MODES = ("ge", "gt", "le", "lt", "eq")


# ---------------------------------------------------------------------------
# Core pure-logic helpers
# ---------------------------------------------------------------------------

def _validate_matrix(matrix: Any) -> List[List[float]]:
    """Validate and coerce the input matrix to a list of lists of floats.

    Raises ValueError on malformed input.
    """
    if matrix is None:
        raise ValueError("matrix must not be None")
    if not isinstance(matrix, (list, tuple)):
        raise ValueError("matrix must be a list or tuple of rows")
    if len(matrix) == 0:
        raise ValueError("matrix must have at least one row")

    rows: List[List[float]] = []
    for i, row in enumerate(matrix):
        if not isinstance(row, (list, tuple)):
            raise ValueError(f"row {i} must be a list or tuple")
        if len(row) == 0:
            raise ValueError(f"row {i} must have at least one column")
        coerced: List[float] = []
        for j, val in enumerate(row):
            if isinstance(val, bool):
                raise ValueError(f"element [{i}][{j}] is a bool, expected a number")
            if not isinstance(val, (int, float)):
                raise ValueError(f"element [{i}][{j}] is not a number: {type(val).__name__}")
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                raise ValueError(f"element [{i}][{j}] is NaN or Inf")
            if f < 0:
                raise ValueError(f"element [{i}][{j}] is negative: {f}")
            coerced.append(f)
        rows.append(coerced)

    # All rows must have the same length
    width = len(rows[0])
    for i, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f"row {i} has length {len(row)}, expected {width}")

    return rows


def _normalize_total(matrix: List[List[float]], target_sum: float) -> List[List[float]]:
    """Scale each row so its sum equals target_sum.

    Rows with zero sum are left as all-zeros (no division by zero).
    """
    if target_sum < 0:
        raise ValueError("target_sum must be non-negative")

    normalized: List[List[float]] = []
    for row in matrix:
        row_sum = sum(row)
        if row_sum == 0.0:
            normalized.append([0.0] * len(row))
        else:
            scale = target_sum / row_sum
            normalized.append([v * scale for v in row])
    return normalized


def _apply_log1p(matrix: List[List[float]]) -> List[List[float]]:
    """Apply natural log(1 + x) element-wise."""
    return [[math.log1p(v) for v in row] for row in matrix]


def _extract_matrix(adata: Any) -> Tuple[List[List[float]], Dict[str, Any]]:
    """Extract the expression matrix from an AnnData-like dict or a plain 2D list.

    Returns (matrix, meta) where meta carries n_obs, n_vars, and any extra keys.
    """
    if adata is None:
        raise ValueError("adata must not be None")

    if isinstance(adata, (list, tuple)):
        matrix = _validate_matrix(adata)
        meta = {"n_obs": len(matrix), "n_vars": len(matrix[0])}
        return matrix, meta

    if isinstance(adata, dict):
        if "X" not in adata:
            raise ValueError("AnnData dict must contain key 'X'")
        matrix = _validate_matrix(adata["X"])
        meta = {k: v for k, v in adata.items() if k != "X"}
        meta.setdefault("n_obs", len(matrix))
        meta.setdefault("n_vars", len(matrix[0]))
        return matrix, meta

    raise ValueError(f"adata must be a dict with 'X' or a 2D list, got {type(adata).__name__}")


def _build_output(matrix: List[List[float]], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Build the output AnnData-like dict."""
    out: Dict[str, Any] = dict(meta)
    out["X"] = matrix
    return out


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_ScRNA_Normalize:
    """Normalize a single-cell expression matrix to a target sum per cell,
    optionally applying log1p. Pure-logic implementation (no scanpy)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "adata": ("OBJECT",),
                "target_sum": ("FLOAT", {"default": 10000.0, "min": 0.0, "max": 1e12, "step": 1.0}),
                "log1p": ("BOOLEAN", {"default": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("OBJECT",)
    RETURN_NAMES = ("adata_norm",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, adata: Any, target_sum: float, log1p: bool) -> Tuple[Dict[str, Any]]:
        matrix, meta = _extract_matrix(adata)

        if not isinstance(target_sum, (int, float)) or isinstance(target_sum, bool):
            raise ValueError("target_sum must be a number")
        target_sum = float(target_sum)
        if math.isnan(target_sum) or math.isinf(target_sum):
            raise ValueError("target_sum must be finite")
        if target_sum < 0:
            raise ValueError("target_sum must be non-negative")

        normalized = _normalize_total(matrix, target_sum)
        if log1p:
            normalized = _apply_log1p(normalized)

        result = _build_output(normalized, meta)
        return (result,)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ScRNA_Normalize": PSN_ScRNA_Normalize,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ScRNA_Normalize": "PSN ScRNA Normalize",
}
