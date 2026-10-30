"""Tests for PSN_ClipMerger pure-logic planning."""

import json
import pytest

from psn_nodes.gen.psn_clipmerger import (
    PSN_ClipMerger,
    plan_merge,
    _validate_clips,
    _validate_transition,
)


def test_merge_two_clips_cut():
    """Two 10-frame clips with cut transition should produce 20 frames."""
    plan = plan_merge([10, 10], "cut", 0)
    assert plan["ok"] is True
    assert plan["total_frames"] == 20
    assert len(plan["blend_map"]) == 20
    # All entries should have None for the second source
    for out_idx, src_a, src_b in plan["blend_map"]:
        assert src_b is None


def test_merge_two_clips_crossfade_2_frames():
    """Two 10-frame clips with 2-frame crossfade should produce 18 frames."""
    plan = plan_merge([10, 10], "crossfade", 2)
    assert plan["ok"] is True
    assert plan["total_frames"] == 18
    assert len(plan["blend_map"]) == 18
    # The last 2 frames of clip 0 and first 2 frames of clip 1 are blended
    # Single-source: clip0 frames 0-7 (8 frames), clip1 frames 2-9 (8 frames)
    # Blend: 2 frames
    # Total: 8 + 2 + 8 = 18
    blend_entries = [e for e in plan["blend_map"] if e[2] is not None]
    assert len(blend_entries) == 2
    # Verify blend pairs
    for out_idx, src_a, src_b in blend_entries:
        assert src_a[0] == 0  # from clip 0
        assert src_b[0] == 1  # from clip 1


def test_merge_three_clips_crossfade():
    """Three clips with crossfade should produce correct total frame count."""
    # Clips: 10, 10, 10 with 2-frame crossfade at each boundary
    # Boundary 0: min(2, 10, 10) = 2
    # Boundary 1: min(2, 10, 10) = 2
    # Total = 10 + 10 + 10 - 2 - 2 = 26
    plan = plan_merge([10, 10, 10], "crossfade", 2)
    assert plan["ok"] is True
    assert plan["total_frames"] == 26
    assert len(plan["blend_map"]) == 26


def test_crossfade_clamped_to_clip_length():
    """Crossfade frames should be clamped to the shorter adjacent clip."""
    # Clip 0 has 3 frames, clip 1 has 10 frames, crossfade 5
    # Effective crossfade = min(5, 3, 10) = 3
    # Total = 3 + 10 - 3 = 10
    plan = plan_merge([3, 10], "crossfade", 5)
    assert plan["ok"] is True
    assert plan["total_frames"] == 10
    blend_entries = [e for e in plan["blend_map"] if e[2] is not None]
    assert len(blend_entries) == 3


def test_single_clip():
    """A single clip should just pass through all frames."""
    plan = plan_merge([15], "cut", 0)
    assert plan["ok"] is True
    assert plan["total_frames"] == 15
    assert len(plan["blend_map"]) == 15
    for out_idx, src_a, src_b in plan["blend_map"]:
        assert src_a[0] == 0
        assert src_b is None


def test_invalid_empty_clips():
    """Empty clips list should return an error."""
    plan = plan_merge([], "cut", 0)
    assert plan["ok"] is False
    assert "at least one clip" in plan["error"]


def test_invalid_negative_frame_count():
    """Negative frame count should return an error."""
    plan = plan_merge([10, -5], "cut", 0)
    assert plan["ok"] is False
    assert "positive" in plan["error"]


def test_invalid_transition_type():
    """Invalid transition type should return an error."""
    plan = plan_merge([10, 10], "dissolve", 2)
    assert plan["ok"] is False
    assert "transition must be one of" in plan["error"]


def test_invalid_transition_frames_negative():
    """Negative transition_frames should return an error."""
    plan = plan_merge([10, 10], "crossfade", -1)
    assert plan["ok"] is False
    assert "non-negative" in plan["error"]


def test_node_run_basic():
    """The node's run method should work with default inputs."""
    node = PSN_ClipMerger()
    total, plan_json, error = node.run(2, "cut", 0, "10,10")
    assert error == ""
    assert total == 20
    data = json.loads(plan_json)
    assert data["total_frames"] == 20


def test_node_run_crossfade():
    """The node's run method with crossfade should compute correct total."""
    node = PSN_ClipMerger()
    total, plan_json, error = node.run(2, "crossfade", 2, "10,10")
    assert error == ""
    assert total == 18
    data = json.loads(plan_json)
    assert data["total_frames"] == 18
    assert data["transition"] == "crossfade"


def test_node_run_invalid_frame_count_string():
    """The node should handle invalid frame count strings gracefully."""
    node = PSN_ClipMerger()
    total, plan_json, error = node.run(2, "cut", 0, "10,abc")
    assert total == 0
    assert "invalid frame count" in error


def test_validate_clips_non_integer():
    """Non-integer frame counts should be rejected."""
    counts, err = _validate_clips([10, 5.5])
    assert counts is None
    assert "integer" in err


def test_validate_transition_invalid():
    """Invalid transition should be rejected."""
    t, f, err = _validate_transition("fade", 2)
    assert t is None
    assert "transition must be one of" in err
