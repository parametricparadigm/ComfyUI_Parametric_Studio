"""Tests for PSN_VRAM_Guard (pure logic, no I/O)."""

import math

import pytest

from psn_nodes.gen.psn_vram_guard import (
    PSN_VRAM_Guard,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _guard():
    return PSN_VRAM_Guard()


def test_psn_vram_guard_safe_when_usage_below_threshold():
    node = _guard()
    is_safe, warning = node.run(threshold=8.0, current_usage=4.0)
    assert is_safe is True
    assert warning == ""


def test_psn_vram_guard_safe_when_usage_equals_threshold():
    node = _guard()
    is_safe, warning = node.run(threshold=8.0, current_usage=8.0)
    assert is_safe is True
    assert warning == ""


def test_psn_vram_guard_unsafe_when_usage_exceeds_threshold():
    node = _guard()
    is_safe, warning = node.run(threshold=8.0, current_usage=9.5)
    assert is_safe is False
    assert "exceeds threshold" in warning
    assert "9.500" in warning
    assert "8.000" in warning


def test_psn_vram_guard_rejects_nan_usage():
    node = _guard()
    is_safe, warning = node.run(threshold=8.0, current_usage=float("nan"))
    assert is_safe is False
    assert "finite" in warning


def test_psn_vram_guard_rejects_infinite_threshold():
    node = _guard()
    is_safe, warning = node.run(threshold=float("inf"), current_usage=1.0)
    assert is_safe is False
    assert "finite" in warning


def test_psn_vram_guard_rejects_negative_usage():
    node = _guard()
    is_safe, warning = node.run(threshold=8.0, current_usage=-1.0)
    assert is_safe is False
    assert "must be >= 0" in warning


def test_psn_vram_guard_rejects_negative_threshold():
    node = _guard()
    is_safe, warning = node.run(threshold=-2.0, current_usage=1.0)
    assert is_safe is False
    assert "threshold must be >= 0" in warning


def test_psn_vram_guard_rejects_bool_input():
    node = _guard()
    is_safe, warning = node.run(threshold=True, current_usage=1.0)
    assert is_safe is False
    assert "must be a number" in warning


def test_psn_vram_guard_rejects_non_numeric_string():
    node = _guard()
    is_safe, warning = node.run(threshold=8.0, current_usage="not-a-number")
    assert is_safe is False
    assert "could not be parsed" in warning


def test_psn_vram_guard_accepts_numeric_string():
    node = _guard()
    is_safe, warning = node.run(threshold="8.0", current_usage="7.5")
    assert is_safe is True
    assert warning == ""


def test_psn_vram_guard_zero_threshold_with_zero_usage_is_safe():
    node = _guard()
    is_safe, warning = node.run(threshold=0.0, current_usage=0.0)
    assert is_safe is True
    assert warning == ""


def test_psn_vram_guard_zero_threshold_with_positive_usage_is_unsafe():
    node = _guard()
    is_safe, warning = node.run(threshold=0.0, current_usage=0.1)
    assert is_safe is False
    assert "exceeds threshold" in warning


def test_psn_vram_guard_node_mappings_present():
    assert "PSN_VRAM_Guard" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VRAM_Guard"] is PSN_VRAM_Guard
    assert "PSN_VRAM_Guard" in NODE_DISPLAY_NAME_MAPPINGS


def test_psn_vram_guard_input_types_shape():
    spec = PSN_VRAM_Guard.INPUT_TYPES()
    assert "required" in spec
    assert "threshold" in spec["required"]
    assert "current_usage" in spec["required"]
    assert PSN_VRAM_Guard.RETURN_TYPES == ("BOOLEAN", "STRING")
    assert PSN_VRAM_Guard.RETURN_NAMES == ("is_safe", "warning")
    assert PSN_VRAM_Guard.FUNCTION == "run"
