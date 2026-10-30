"""
Tests for PSN Temporal Slicing for Long Videos (pure-logic core).
"""

import json
import pytest

from psn_nodes.gen.n_9_temporal_slicing_for_long_videos import (
    PSN_Temporal_Slice_Plan,
    PSN_Temporal_Slice_Blend,
    _compute_slice_plan,
    _validate_slice_params,
)


def test_slice_plan_basic_100_frames_10_slice_2_overlap():
    """100 frames, slice_size=10, overlap=2 -> verify plan structure and coverage."""
    plan = _compute_slice_plan(100, 10, 2)
    # First slice: 0..10
    assert plan[0]["start"] == 0
    assert plan[0]["end"] == 10
    # Each subsequent slice starts at prev_end - overlap
    for i in range(1, len(plan)):
        assert plan[i]["start"] == plan[i - 1]["end"] - 2
    # Last slice must end at 100
    assert plan[-1]["end"] == 100
    # All frames covered: union of [start, end) should be [0, 100)
    covered = set()
    for s in plan:
        covered.update(range(s["start"], s["end"]))
    assert covered == set(range(100))


def test_slice_plan_no_overlap():
    """No overlap: slices should be contiguous with no gaps or overlaps."""
    plan = _compute_slice_plan(20, 5, 0)
    assert len(plan) == 4
    for i, s in enumerate(plan):
        assert s["start"] == i * 5
        assert s["end"] == (i + 1) * 5
        assert s["blend_start"] is None
        assert s["blend_end"] is None


def test_slice_plan_single_slice():
    """total_frames == slice_size: only one slice, no blend."""
    plan = _compute_slice_plan(10, 10, 2)
    assert len(plan) == 1
    assert plan[0]["start"] == 0
    assert plan[0]["end"] == 10
    assert plan[0]["blend_start"] is None


def test_validate_bad_inputs():
    """Invalid parameters should return error messages."""
    assert _validate_slice_params(0, 10, 2) != ""
    assert _validate_slice_params(100, 0, 2) != ""
    assert _validate_slice_params(100, 10, -1) != ""
    assert _validate_slice_params(100, 10, 10) != ""  # overlap >= slice_size
    assert _validate_slice_params(5, 10, 2) != ""  # slice_size > total_frames
    assert _validate_slice_params(100, 10, 2) == ""  # valid


def test_blend_uniform_values_no_seams():
    """
    If every slice decodes to the same constant value, the blended output
    should be that constant everywhere (no seams).
    """
    total = 100
    slice_size = 10
    overlap = 2
    plan = _compute_slice_plan(total, slice_size, overlap)
    # Each slice decodes to constant 5.0
    slices = [[5.0] * (s["end"] - s["start"]) for s in plan]
    node = PSN_Temporal_Slice_Blend()
    out_json, err = node.run(json.dumps(slices), total, slice_size, overlap)
    assert err == ""
    out = json.loads(out_json)
    assert len(out) == total
    for v in out:
        assert abs(v - 5.0) < 1e-9


def test_blend_linear_ramp_continuity():
    """
    Each slice decodes to a linear ramp starting at its own start index.
    In the overlap region, the blend should produce a smooth transition.
    Verify that the output is continuous (no jumps) at slice boundaries.
    """
    total = 30
    slice_size = 10
    overlap = 4
    plan = _compute_slice_plan(total, slice_size, overlap)
    # Slice i decodes frame j to value (start + j) * 1.0
    slices = []
    for s in plan:
        slices.append([(s["start"] + j) * 1.0 for j in range(s["end"] - s["start"])])
    node = PSN_Temporal_Slice_Blend()
    out_json, err = node.run(json.dumps(slices), total, slice_size, overlap)
    assert err == ""
    out = json.loads(out_json)
    assert len(out) == total
    # Check continuity: max difference between consecutive frames should be small
    max_diff = 0.0
    for i in range(1, total):
        diff = abs(out[i] - out[i - 1])
        max_diff = max(max_diff, diff)
    # With linear ramps and cross-fade, the output should be smooth.
    # The max diff should be bounded (not a large jump).
    assert max_diff < 5.0, f"Discontinuity detected: max_diff={max_diff}"


def test_blend_bad_json_input():
    """Invalid JSON in slice_frames should return an error."""
    node = PSN_Temporal_Slice_Blend()
    out_json, err = node.run("not valid json", 10, 5, 1)
    assert err != ""
    assert out_json == "[]"


def test_blend_wrong_slice_count():
    """If the number of slices doesn't match the plan, return an error."""
    node = PSN_Temporal_Slice_Blend()
    # Plan for 10 frames, slice_size=5, overlap=1 -> 3 slices
    # But we provide only 2 slices
    slices = [[1.0] * 5, [2.0] * 5]
    out_json, err = node.run(json.dumps(slices), 10, 5, 1)
    assert err != ""
    assert "expected" in err


def test_plan_node_run_valid():
    """PSN_Temporal_Slice_Plan.run should return valid JSON plan."""
    node = PSN_Temporal_Slice_Plan()
    plan_json, num_slices, err = node.run(100, 10, 2)
    assert err == ""
    assert num_slices > 0
    plan = json.loads(plan_json)
    assert isinstance(plan, list)
    assert len(plan) == num_slices


def test_plan_node_run_invalid():
    """PSN_Temporal_Slice_Plan.run with invalid params should return error."""
    node = PSN_Temporal_Slice_Plan()
    plan_json, num_slices, err = node.run(100, 10, 10)  # overlap >= slice_size
    assert err != ""
    assert num_slices == 0
    assert plan_json == "[]"
