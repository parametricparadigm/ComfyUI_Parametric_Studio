"""Tests for PSN_CV_RunTracker node."""

import json
import re

from psn_nodes.gen.psn_cv_runtracker import (
    PSN_CV_RunTracker,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _compute_hash,
    _format_log_entry,
)


def test_node_class_mappings_registered():
    """Verify the node is registered in the class mappings."""
    assert "PSN_CV_RunTracker" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_CV_RunTracker"] is PSN_CV_RunTracker
    assert "PSN_CV_RunTracker" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_structure():
    """Verify INPUT_TYPES has required and optional fields with correct types."""
    input_types = PSN_CV_RunTracker.INPUT_TYPES()
    assert "required" in input_types
    assert "optional" in input_types
    assert "node_id" in input_types["required"]
    assert "input_hash" in input_types["optional"]
    assert input_types["required"]["node_id"][0] == "STRING"
    assert input_types["optional"]["input_hash"][0] == "STRING"


def test_run_returns_valid_jsonl_entry():
    """Verify run() returns a valid JSONL log entry with expected fields."""
    node = PSN_CV_RunTracker()
    result = node.run(node_id="test_node", input_hash="abc123")
    assert len(result) == 1
    log_entry = result[0]
    assert isinstance(log_entry, str)
    # Parse as JSON
    parsed = json.loads(log_entry)
    assert parsed["node_id"] == "test_node"
    assert parsed["input_hash"] == "abc123"
    assert "timestamp" in parsed
    assert "duration" in parsed
    assert isinstance(parsed["timestamp"], float)
    assert isinstance(parsed["duration"], float)
    assert parsed["duration"] >= 0.0


def test_run_with_empty_input_hash_computes_default():
    """Verify that an empty input_hash results in a computed SHA-256 of empty string."""
    node = PSN_CV_RunTracker()
    result = node.run(node_id="hash_test", input_hash="")
    log_entry = result[0]
    parsed = json.loads(log_entry)
    # SHA-256 of empty string
    expected_hash = _compute_hash("")
    assert parsed["input_hash"] == expected_hash
    assert len(parsed["input_hash"]) == 64  # SHA-256 hex digest length


def test_run_with_none_input_hash():
    """Verify that None input_hash is handled gracefully."""
    node = PSN_CV_RunTracker()
    result = node.run(node_id="none_hash_test", input_hash=None)
    log_entry = result[0]
    parsed = json.loads(log_entry)
    expected_hash = _compute_hash("")
    assert parsed["input_hash"] == expected_hash


def test_run_with_non_string_node_id():
    """Verify that non-string node_id is coerced to string."""
    node = PSN_CV_RunTracker()
    result = node.run(node_id=12345, input_hash="somehash")
    log_entry = result[0]
    parsed = json.loads(log_entry)
    assert parsed["node_id"] == "12345"


def test_run_with_empty_node_id():
    """Verify that an empty node_id defaults to 'unnamed_node'."""
    node = PSN_CV_RunTracker()
    result = node.run(node_id="", input_hash="somehash")
    log_entry = result[0]
    parsed = json.loads(log_entry)
    assert parsed["node_id"] == "unnamed_node"


def test_compute_hash_deterministic():
    """Verify _compute_hash is deterministic for the same input."""
    hash1 = _compute_hash("hello")
    hash2 = _compute_hash("hello")
    assert hash1 == hash2
    assert len(hash1) == 64
    # Different input should produce different hash
    hash3 = _compute_hash("world")
    assert hash1 != hash3


def test_compute_hash_with_none():
    """Verify _compute_hash handles None input."""
    hash_none = _compute_hash(None)
    hash_empty = _compute_hash("")
    assert hash_none == hash_empty


def test_format_log_entry_structure():
    """Verify _format_log_entry produces valid compact JSON."""
    entry = _format_log_entry("my_node", "deadbeef", 1234567890.123, 0.0045)
    parsed = json.loads(entry)
    assert parsed["node_id"] == "my_node"
    assert parsed["input_hash"] == "deadbeef"
    assert parsed["timestamp"] == 1234567890.123
    assert parsed["duration"] == 0.0045
    # Verify it's compact (no spaces after separators)
    assert ": " not in entry
    assert ", " not in entry


def test_run_duration_is_non_negative():
    """Verify duration is always non-negative."""
    node = PSN_CV_RunTracker()
    for _ in range(10):
        result = node.run(node_id="timing_test", input_hash="hash")
        parsed = json.loads(result[0])
        assert parsed["duration"] >= 0.0


def test_run_with_unicode_node_id():
    """Verify Unicode node_id is handled correctly."""
    node = PSN_CV_RunTracker()
    result = node.run(node_id="node_日本語", input_hash="unicode_hash")
    log_entry = result[0]
    parsed = json.loads(log_entry)
    assert parsed["node_id"] == "node_日本語"


def test_return_types_and_names():
    """Verify RETURN_TYPES and RETURN_NAMES are correctly defined."""
    assert PSN_CV_RunTracker.RETURN_TYPES == ("STRING",)
    assert PSN_CV_RunTracker.RETURN_NAMES == ("log_entry",)
    assert PSN_CV_RunTracker.FUNCTION == "run"
    assert PSN_CV_RunTracker.CATEGORY == "ParametricStudio/CV"
