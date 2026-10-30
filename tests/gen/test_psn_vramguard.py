"""Tests for PSN_VRAMGuard."""

import pytest

from psn_nodes.gen.psn_vramguard import (
    PSN_VRAMGuard,
    _check_vram,
    _validate_inputs,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_psn_vramguard_safe_small_request():
    """Small request on a 24GB GPU with low allocation should be safe."""
    node = PSN_VRAMGuard()
    safe, msg = node.run(
        required_gb=1.0,
        current_batch_size=1,
        allocated_bytes=2e9,
        reserved_bytes=3e9,
        total_bytes=24e9,
    )
    assert safe is True
    assert "Safe" in msg


def test_psn_vramguard_unsafe_large_request():
    """Absurdly large request should be flagged as OOM risk."""
    node = PSN_VRAMGuard()
    safe, msg = node.run(
        required_gb=200.0,
        current_batch_size=1,
        allocated_bytes=2e9,
        reserved_bytes=3e9,
        total_bytes=24e9,
    )
    assert safe is False
    assert "OOM risk" in msg


def test_psn_vramguard_boundary_at_90_percent():
    """Request that lands exactly at 90% of total should be safe (not >)."""
    total = 24e9
    limit = total * 0.9
    allocated = 1e9
    required_gb = (limit - allocated) / 1e9
    node = PSN_VRAMGuard()
    safe, msg = node.run(
        required_gb=required_gb,
        current_batch_size=1,
        allocated_bytes=allocated,
        reserved_bytes=0.0,
        total_bytes=total,
    )
    assert safe is True


def test_psn_vramguard_just_over_90_percent():
    """Request slightly over 90% should be unsafe."""
    total = 24e9
    limit = total * 0.9
    allocated = 1e9
    required_gb = (limit - allocated) / 1e9 + 0.001
    node = PSN_VRAMGuard()
    safe, msg = node.run(
        required_gb=required_gb,
        current_batch_size=1,
        allocated_bytes=allocated,
        reserved_bytes=0.0,
        total_bytes=total,
    )
    assert safe is False
    assert "OOM risk" in msg


def test_psn_vramguard_invalid_negative_required_gb():
    """Negative required_gb should be rejected."""
    safe, msg = _check_vram(
        required_gb=-1.0,
        current_batch_size=1,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vramguard_invalid_zero_batch_size():
    """Batch size of 0 should be rejected."""
    safe, msg = _check_vram(
        required_gb=1.0,
        current_batch_size=0,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vramguard_invalid_zero_total_bytes():
    """Total bytes of 0 should be rejected."""
    safe, msg = _check_vram(
        required_gb=1.0,
        current_batch_size=1,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=0.0,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vramguard_allocated_exceeds_total():
    """Allocated bytes greater than total should be rejected."""
    safe, msg = _check_vram(
        required_gb=1.0,
        current_batch_size=1,
        allocated_bytes=30e9,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vramguard_non_numeric_input():
    """Non-numeric required_gb should be rejected."""
    safe, msg = _check_vram(
        required_gb="1.0",
        current_batch_size=1,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vramguard_node_mappings():
    """Node class and display name mappings should be present."""
    assert "PSN_VRAMGuard" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VRAMGuard"] is PSN_VRAMGuard
    assert "PSN_VRAMGuard" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_VRAMGuard"] == "VRAM Guard (Pre-flight Check)"


def test_psn_vramguard_input_types_structure():
    """INPUT_TYPES should have the expected required fields."""
    it = PSN_VRAMGuard.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "required_gb" in req
    assert "current_batch_size" in req
    assert "allocated_bytes" in req
    assert "reserved_bytes" in req
    assert "total_bytes" in req
    assert PSN_VRAMGuard.RETURN_TYPES == ("BOOLEAN", "STRING")
    assert PSN_VRAMGuard.RETURN_NAMES == ("safe", "message")
    assert PSN_VRAMGuard.FUNCTION == "run"
