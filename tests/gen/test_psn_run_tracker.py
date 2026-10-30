"""Tests for PSN_RunTracker node."""

import pytest
from psn_nodes.gen.psn_run_tracker import PSN_RunTracker


def test_basic_progress_midpoint():
    node = PSN_RunTracker()
    progress, log_entry = node.run("test_run", 10, 5, "mid")
    assert progress == pytest.approx(0.5)
    assert "test_run" in log_entry
    assert "0.5000" in log_entry
    assert "5/10" in log_entry
    assert "mid" in log_entry


def test_progress_first_item():
    node = PSN_RunTracker()
    progress, log_entry = node.run("r1", 100, 1, "")
    assert progress == pytest.approx(0.01)
    assert "1/100" in log_entry


def test_progress_last_item():
    node = PSN_RunTracker()
    progress, log_entry = node.run("r2", 10, 10, "done")
    assert progress == pytest.approx(1.0)
    assert "10/10" in log_entry


def test_current_item_exceeds_total_clamped():
    node = PSN_RunTracker()
    progress, log_entry = node.run("r3", 5, 100, "overflow")
    assert progress == pytest.approx(1.0)
    assert "5/5" in log_entry


def test_current_item_below_one_clamped():
    node = PSN_RunTracker()
    progress, log_entry = node.run("r4", 10, 0, "underflow")
    assert progress == pytest.approx(0.1)
    assert "1/10" in log_entry


def test_total_items_zero_clamped_to_one():
    node = PSN_RunTracker()
    progress, log_entry = node.run("r5", 0, 1, "zero_total")
    assert progress == pytest.approx(1.0)
    assert "1/1" in log_entry


def test_metadata_truncated():
    node = PSN_RunTracker()
    long_meta = "x" * 1000
    progress, log_entry = node.run("r6", 10, 1, long_meta)
    assert "..." in log_entry
    # The metadata portion should be truncated
    assert "x" * 512 in log_entry
    assert "x" * 513 not in log_entry


def test_metadata_control_chars_stripped():
    node = PSN_RunTracker()
    meta_with_ctrl = "hello\x00world\x01test"
    progress, log_entry = node.run("r7", 10, 1, meta_with_ctrl)
    assert "\x00" not in log_entry
    assert "\x01" not in log_entry
    assert "helloworldtest" in log_entry


def test_single_item_grid():
    node = PSN_RunTracker()
    progress, log_entry = node.run("r8", 1, 1, "single")
    assert progress == pytest.approx(1.0)
    assert "1/1" in log_entry


def test_log_entry_format_structure():
    node = PSN_RunTracker()
    progress, log_entry = node.run("abc123", 20, 7, "meta_data")
    # Should start with a timestamp in brackets
    assert log_entry.startswith("[")
    assert "]" in log_entry
    assert "run_id=abc123" in log_entry
    assert "progress=0.3500" in log_entry
    assert "item=7/20" in log_entry
    assert "metadata=meta_data" in log_entry
