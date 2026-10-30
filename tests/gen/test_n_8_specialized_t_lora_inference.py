"""
Tests for psn_nodes.gen.n_8_specialized_t_lora_inference.

Covers:
  * linear mask ramp
  * step (hard) mask
  * custom mask parsing and application
  * degenerate / invalid windows (start > end, out of range, total_steps <= 0)
  * custom mask with missing entries
  * bad custom_mask string input
  * edge: single-step window
"""

import pytest

from psn_nodes.gen.n_8_specialized_t_lora_inference import (
    PSN_TLora_Timestep_Mask,
    compute_strength_vector,
)


def test_linear_mask_ramp():
    """Linear mask: 0 before start, ramps to 1 at end, 0 after end."""
    strengths, ok, reason = compute_strength_vector(
        start_step=2, end_step=6, total_steps=10, mask_type="linear"
    )
    assert ok is True
    assert reason == "ok"
    assert len(strengths) == 10
    # Steps 0,1 -> 0.0
    assert strengths[0] == 0.0
    assert strengths[1] == 0.0
    # Step 2 -> 0.0 (start of ramp)
    assert strengths[2] == 0.0
    # Step 3 -> 0.25
    assert strengths[3] == pytest.approx(0.25)
    # Step 4 -> 0.5
    assert strengths[4] == pytest.approx(0.5)
    # Step 5 -> 0.75
    assert strengths[5] == pytest.approx(0.75)
    # Step 6 -> 1.0 (end of ramp)
    assert strengths[6] == 1.0
    # Steps 7-9 -> 0.0
    assert strengths[7] == 0.0
    assert strengths[8] == 0.0
    assert strengths[9] == 0.0


def test_step_mask_hard():
    """Step mask: 1.0 inside [start, end], 0.0 outside."""
    strengths, ok, reason = compute_strength_vector(
        start_step=3, end_step=5, total_steps=10, mask_type="step"
    )
    assert ok is True
    assert len(strengths) == 10
    expected = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    assert strengths == expected


def test_custom_mask_applied():
    """Custom mask: user-supplied per-step values are used directly."""
    # Note: For custom mask, start/end are ignored, so we can use any valid values
    # that pass basic validation or are ignored. The function now relaxes validation
    # for custom masks to only check total_steps.
    strengths, ok, reason = compute_strength_vector(
        start_step=0, end_step=9, total_steps=5, mask_type="custom",
        custom_mask=[0.0, 0.5, 1.0, 0.5, 0.0],
    )
    assert ok is True
    assert strengths == [0.0, 0.5, 1.0, 0.5, 0.0]


def test_custom_mask_shorter_than_total():
    """Custom mask shorter than total_steps: missing entries default to 0.0."""
    strengths, ok, reason = compute_strength_vector(
        start_step=0, end_step=9, total_steps=5, mask_type="custom",
        custom_mask=[1.0, 0.5],
    )
    assert ok is True
    assert strengths == [1.0, 0.5, 0.0, 0.0, 0.0]


def test_invalid_start_greater_than_end():
    """start_step > end_step should be rejected for non-custom masks."""
    strengths, ok, reason = compute_strength_vector(
        start_step=5, end_step=2, total_steps=10, mask_type="linear"
    )
    assert ok is False
    assert strengths == []
    assert "start_step must be <= end_step" in reason


def test_invalid_total_steps_zero():
    """total_steps <= 0 should be rejected."""
    strengths, ok, reason = compute_strength_vector(
        start_step=0, end_step=5, total_steps=0, mask_type="linear"
    )
    assert ok is False
    assert strengths == []
    assert "total_steps must be a positive integer" in reason


def test_invalid_start_beyond_total():
    """start_step >= total_steps should be rejected for non-custom masks."""
    strengths, ok, reason = compute_strength_vector(
        start_step=10, end_step=15, total_steps=10, mask_type="linear"
    )
    assert ok is False
    assert strengths == []
    assert "start_step is beyond total_steps" in reason


def test_single_step_window_linear():
    """Single-step window (start == end) should be fully active at that step."""
    strengths, ok, reason = compute_strength_vector(
        start_step=4, end_step=4, total_steps=10, mask_type="linear"
    )
    assert ok is True
    assert strengths[4] == 1.0
    # All other steps should be 0.0
    for i in range(10):
        if i != 4:
            assert strengths[i] == 0.0


def test_node_run_linear():
    """Node run() with linear mask returns correct strengths."""
    node = PSN_TLora_Timestep_Mask()
    strengths, ok, reason = node.run(
        start_step=0, end_step=5, total_steps=10, mask_type="linear"
    )
    assert ok is True
    assert len(strengths) == 10
    # First 6 steps ramp 0->1, last 4 are 0.0
    assert strengths[0] == 0.0
    assert strengths[5] == 1.0
    assert strengths[9] == 0.0


def test_node_run_custom_mask_string():
    """Node run() parses custom_mask string correctly."""
    node = PSN_TLora_Timestep_Mask()
    strengths, ok, reason = node.run(
        start_step=0, end_step=9, total_steps=4, mask_type="custom",
        custom_mask="[0.0, 1.0, 0.5, 0.0]",
    )
    assert ok is True
    assert strengths == [0.0, 1.0, 0.5, 0.0]


def test_node_run_custom_mask_bad_string():
    """Node run() rejects malformed custom_mask string."""
    node = PSN_TLora_Timestep_Mask()
    strengths, ok, reason = node.run(
        start_step=0, end_step=9, total_steps=4, mask_type="custom",
        custom_mask="not a list",
    )
    assert ok is False
    assert strengths == []
    assert "custom_mask" in reason.lower()


def test_node_run_custom_mask_empty():
    """Node run() rejects empty custom_mask when mask_type is custom."""
    node = PSN_TLora_Timestep_Mask()
    strengths, ok, reason = node.run(
        start_step=0, end_step=9, total_steps=4, mask_type="custom",
        custom_mask="",
    )
    assert ok is False
    assert strengths == []
    assert "custom_mask" in reason.lower()


def test_node_run_invalid_window():
    """Node run() propagates validation failure for bad window."""
    node = PSN_TLora_Timestep_Mask()
    strengths, ok, reason = node.run(
        start_step=8, end_step=3, total_steps=10, mask_type="step"
    )
    assert ok is False
    assert strengths == []
    assert "start_step must be <= end_step" in reason
