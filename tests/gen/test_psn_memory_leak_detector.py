"""Tests for PSN_Memory_Leak_Detector."""

import json
import math

from psn_nodes.gen.psn_memory_leak_detector import (
    PSN_Memory_Leak_Detector,
    _detect_leak,
    _to_number,
)


def test_detects_monotonic_increase_as_leak():
    """A steadily increasing VRAM history with no drops should be flagged."""
    history = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0]
    leak, report = _detect_leak(history, min_points=5, min_total_increase=50.0)
    assert leak is True
    data = json.loads(report)
    assert data["leak_detected"] is True
    assert data["total_increase"] == 70.0
    assert data["drops"] == 0


def test_no_leak_when_usage_is_stable():
    """Flat or slightly fluctuating usage should not be flagged."""
    history = [100.0, 101.0, 99.0, 100.0, 102.0, 98.0, 100.0, 101.0]
    leak, report = _detect_leak(history, min_points=5, min_total_increase=50.0)
    assert leak is False
    data = json.loads(report)
    assert data["leak_detected"] is False


def test_no_leak_when_significant_drops_occurred():
    """If there are meaningful drops, it is not a leak even if net increase is positive."""
    # Increases then drops significantly
    history = [100.0, 120.0, 140.0, 160.0, 180.0, 100.0, 110.0, 120.0]
    leak, report = _detect_leak(history, min_points=5, min_total_increase=50.0)
    assert leak is False
    data = json.loads(report)
    assert data["drops"] >= 1


def test_insufficient_points_returns_no_leak():
    """Fewer than min_points should return no leak with an error message."""
    history = [100.0, 200.0, 300.0]
    leak, report = _detect_leak(history, min_points=5, min_total_increase=50.0)
    assert leak is False
    data = json.loads(report)
    assert "error" in data
    assert data["points"] == 3


def test_non_numeric_history_returns_no_leak():
    """A history containing non-numeric values should be rejected gracefully."""
    history = [100.0, "abc", 120.0, 130.0, 140.0]
    leak, report = _detect_leak(history, min_points=5, min_total_increase=50.0)
    assert leak is False
    data = json.loads(report)
    assert "error" in data
    assert "non-numeric" in data["error"]


def test_non_list_input_returns_no_leak():
    """Passing a non-list should return no leak with an error."""
    leak, report = _detect_leak("not a list", min_points=5, min_total_increase=50.0)
    assert leak is False
    data = json.loads(report)
    assert "error" in data


def test_to_number_handles_valid_and_invalid():
    """_to_number should coerce valid values and reject invalid ones."""
    assert _to_number(42) == 42.0
    assert _to_number(3.14) == 3.14
    assert _to_number("5.5") == 5.5
    assert _to_number("  10  ") == 10.0
    assert _to_number("abc") is None
    assert _to_number(None) is None
    assert _to_number([1, 2]) is None
    assert _to_number(float("nan")) is None
    assert _to_number(float("inf")) is None
    assert _to_number(True) is None  # bools are rejected


def test_node_run_returns_correct_types():
    """The node's run method should return (BOOLEAN, STRING)."""
    node = PSN_Memory_Leak_Detector()
    history = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0]
    leak, report = node.run(history_data=history, min_points=5, min_total_increase=50.0)
    assert isinstance(leak, bool)
    assert isinstance(report, str)
    assert leak is True
    data = json.loads(report)
    assert data["leak_detected"] is True


def test_node_run_with_empty_history():
    """Empty history should not crash and should report no leak."""
    node = PSN_Memory_Leak_Detector()
    leak, report = node.run(history_data=[])
    assert leak is False
    data = json.loads(report)
    assert data["points"] == 0
    assert "error" in data


def test_custom_thresholds_affect_detection():
    """Changing min_total_increase should change whether a leak is detected."""
    history = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0]
    # Total increase is 35.0
    # With threshold 50, no leak
    leak1, _ = _detect_leak(history, min_points=5, min_total_increase=50.0)
    assert leak1 is False
    # With threshold 20, leak detected
    leak2, _ = _detect_leak(history, min_points=5, min_total_increase=20.0)
    assert leak2 is True
