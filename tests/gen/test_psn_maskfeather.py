"""Tests for psn_nodes.gen.psn_maskfeather."""

import json
import math

import pytest

from psn_nodes.gen.psn_maskfeather import (
    PSN_MaskFeather,
    psn_feather_mask,
    _psn_gaussian_kernel,
    _psn_mask_from_input,
    _psn_mask_to_json,
)


def _make_binary_mask(rows, cols, filled_rows=None, filled_cols=None):
    """Create a binary mask with a filled rectangle."""
    if filled_rows is None:
        filled_rows = (rows // 4, rows - rows // 4)
    if filled_cols is None:
        filled_cols = (cols // 4, cols - cols // 4)
    mask = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if filled_rows[0] <= r < filled_rows[1] and filled_cols[0] <= c < filled_cols[1]:
                row.append(1.0)
            else:
                row.append(0.0)
        mask.append(row)
    return mask


def test_psn_feather_binary_edges_no_longer_binary():
    """Feathering a 64x64 binary mask should produce non-binary edge values."""
    mask = _make_binary_mask(64, 64)
    feathered = psn_feather_mask(mask, feather_radius=4)
    assert len(feathered) == 64
    assert len(feathered[0]) == 64
    # Check that at least one edge pixel is no longer strictly 0 or 1
    found_non_binary = False
    for r in range(64):
        for c in range(64):
            v = feathered[r][c]
            if 0.0 < v < 1.0:
                found_non_binary = True
                break
        if found_non_binary:
            break
    assert found_non_binary, "Expected some non-binary values after feathering"


def test_psn_feather_preserves_dimensions():
    """Feathering should not change the mask dimensions."""
    mask = _make_binary_mask(32, 48)
    feathered = psn_feather_mask(mask, feather_radius=3)
    assert len(feathered) == 32
    assert all(len(row) == 48 for row in feathered)


def test_psn_feather_values_clamped_to_unit_interval():
    """All output values must be in [0, 1]."""
    mask = _make_binary_mask(16, 16)
    feathered = psn_feather_mask(mask, feather_radius=5)
    for row in feathered:
        for v in row:
            assert 0.0 <= v <= 1.0, "Value %f out of [0,1]" % v


def test_psn_feather_zero_radius_is_identity():
    """With radius 0, the mask should be unchanged (identity blur)."""
    mask = _make_binary_mask(8, 8)
    feathered = psn_feather_mask(mask, feather_radius=0)
    for r in range(8):
        for c in range(8):
            assert abs(feathered[r][c] - mask[r][c]) < 1e-9


def test_psn_feather_uniform_mask_stays_uniform():
    """A fully white mask should remain fully white after feathering."""
    mask = [[1.0] * 10 for _ in range(10)]
    feathered = psn_feather_mask(mask, feather_radius=4)
    for row in feathered:
        for v in row:
            assert abs(v - 1.0) < 1e-6


def test_psn_feather_bad_input_empty_mask():
    """An empty mask should raise ValueError."""
    with pytest.raises(ValueError):
        psn_feather_mask([], feather_radius=2)


def test_psn_feather_bad_input_ragged_rows():
    """Ragged rows should raise ValueError."""
    mask = [[1.0, 0.0], [1.0]]
    with pytest.raises(ValueError):
        psn_feather_mask(mask, feather_radius=2)


def test_psn_feather_bad_input_negative_radius():
    """A negative radius should raise ValueError."""
    mask = _make_binary_mask(8, 8)
    with pytest.raises(ValueError):
        psn_feather_mask(mask, feather_radius=-1)


def test_psn_gaussian_kernel_normalized():
    """The Gaussian kernel should sum to approximately 1."""
    kernel = _psn_gaussian_kernel(5, 2.0)
    assert len(kernel) == 11
    assert abs(sum(kernel) - 1.0) < 1e-9


def test_psn_mask_from_input_json_string():
    """_psn_mask_from_input should parse a JSON string into a nested list."""
    mask_json = json.dumps([[1.0, 0.0], [0.0, 1.0]])
    grid = _psn_mask_from_input(mask_json)
    assert grid == [[1.0, 0.0], [0.0, 1.0]]


def test_psn_mask_from_input_bad_json():
    """_psn_mask_from_input should raise on invalid JSON."""
    with pytest.raises((json.JSONDecodeError, ValueError)):
        _psn_mask_from_input("not valid json")


def test_psn_node_run_returns_json_and_preview():
    """The node's run method should return a JSON string and a preview string."""
    mask = _make_binary_mask(16, 16)
    mask_json = _psn_mask_to_json(mask)
    node = PSN_MaskFeather()
    result_json, preview = node.run(mask=mask_json, feather_radius=3.0)
    # result_json should be valid JSON encoding a 16x16 grid
    parsed = json.loads(result_json)
    assert len(parsed) == 16
    assert len(parsed[0]) == 16
    assert isinstance(preview, str)
    assert "16x16" in preview


def test_psn_node_run_with_sigma_override():
    """The node should accept an optional sigma override."""
    mask = _make_binary_mask(16, 16)
    mask_json = _psn_mask_to_json(mask)
    node = PSN_MaskFeather()
    result_json, _ = node.run(mask=mask_json, feather_radius=4.0, sigma=1.5)
    parsed = json.loads(result_json)
    assert len(parsed) == 16
    # Values should still be in [0, 1]
    for row in parsed:
        for v in row:
            assert 0.0 <= v <= 1.0
