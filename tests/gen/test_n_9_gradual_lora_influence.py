"""
Tests for psn_nodes.gen.n_9_gradual_lora_influence
"""

import json
import pytest

from psn_nodes.gen.n_9_gradual_lora_influence import (
    PSN_Gradual_LoRA_Apply,
    _evaluate_linear,
    _evaluate_keyframes,
    _parse_curve,
    _build_schedule,
    _clamp,
)


# ---------------------------------------------------------------------------
# Helper: run the node and parse output
# ---------------------------------------------------------------------------

def _run_node(lora_model="", strength_curve=None, start_frame=0, end_frame=99):
    if strength_curve is None:
        strength_curve = '{"type":"linear","start_strength":0.0,"end_strength":1.0}'
    node = PSN_Gradual_LoRA_Apply()
    scheduled, status = node.run(lora_model, strength_curve, start_frame, end_frame)
    return scheduled, status


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_linear_curve_full_range():
    """Linear curve from 0 to 1 over frames 0-99: check endpoints and midpoint."""
    scheduled, status = _run_node(
        lora_model="test_lora",
        strength_curve='{"type":"linear","start_strength":0.0,"end_strength":1.0}',
        start_frame=0,
        end_frame=99,
    )
    assert status == "ok"
    data = json.loads(scheduled)
    assert data["lora_model"] == "test_lora"
    assert data["start_frame"] == 0
    assert data["end_frame"] == 99
    assert data["curve_type"] == "linear"
    schedule = data["schedule"]
    assert len(schedule) == 100
    # First frame strength ~ 0
    assert abs(schedule[0][1] - 0.0) < 1e-4
    # Last frame strength ~ 1
    assert abs(schedule[99][1] - 1.0) < 1e-4
    # Midpoint frame 49 or 50 should be ~0.5
    mid = schedule[49][1]
    assert abs(mid - 0.5) < 0.02


def test_keyframe_curve_interpolation():
    """Keyframed curve: verify interpolation between keyframes."""
    curve = '{"type":"keyframes","points":[[0,0.0],[50,1.0],[100,0.5]]}'
    scheduled, status = _run_node(
        lora_model="kf_lora",
        strength_curve=curve,
        start_frame=0,
        end_frame=100,
    )
    assert status == "ok"
    data = json.loads(scheduled)
    schedule = data["schedule"]
    assert len(schedule) == 101
    # Frame 0 -> 0.0
    assert abs(schedule[0][1] - 0.0) < 1e-4
    # Frame 50 -> 1.0
    assert abs(schedule[50][1] - 1.0) < 1e-4
    # Frame 100 -> 0.5
    assert abs(schedule[100][1] - 0.5) < 1e-4
    # Frame 25 -> 0.5 (midpoint of 0-50)
    assert abs(schedule[25][1] - 0.5) < 1e-4
    # Frame 75 -> 0.75 (midpoint of 50-100: 1.0 to 0.5)
    assert abs(schedule[75][1] - 0.75) < 1e-4


def test_start_frame_greater_than_end_frame_returns_error():
    """Bad input: start_frame > end_frame should produce an error status."""
    scheduled, status = _run_node(
        lora_model="bad",
        strength_curve='{"type":"linear","start_strength":0.0,"end_strength":1.0}',
        start_frame=100,
        end_frame=50,
    )
    assert status.startswith("error:")
    assert "start_frame must be <= end_frame" in status
    assert scheduled == ""


def test_invalid_curve_json_returns_error():
    """Bad input: malformed JSON in strength_curve should produce an error."""
    scheduled, status = _run_node(
        lora_model="bad",
        strength_curve="not valid json {{{",
        start_frame=0,
        end_frame=10,
    )
    assert status.startswith("error:")
    assert "not valid JSON" in status
    assert scheduled == ""


def test_unknown_curve_type_returns_error():
    """Bad input: unknown curve type should produce an error."""
    scheduled, status = _run_node(
        lora_model="bad",
        strength_curve='{"type":"parabolic","start_strength":0.0,"end_strength":1.0}',
        start_frame=0,
        end_frame=10,
    )
    assert status.startswith("error:")
    assert "type must be" in status
    assert scheduled == ""


def test_single_frame_window():
    """Edge case: start_frame == end_frame produces a single-entry schedule."""
    scheduled, status = _run_node(
        lora_model="single",
        strength_curve='{"type":"linear","start_strength":0.3,"end_strength":0.7}',
        start_frame=42,
        end_frame=42,
    )
    assert status == "ok"
    data = json.loads(scheduled)
    schedule = data["schedule"]
    assert len(schedule) == 1
    assert schedule[0][0] == 42
    # When start==end, linear returns start_strength
    assert abs(schedule[0][1] - 0.3) < 1e-4


def test_keyframe_clamping_outside_range():
    """Keyframed curve: frames outside keyframe range clamp to nearest endpoint."""
    curve = '{"type":"keyframes","points":[[10,0.2],[20,0.8]]}'
    scheduled, status = _run_node(
        lora_model="clamp",
        strength_curve=curve,
        start_frame=0,
        end_frame=30,
    )
    assert status == "ok"
    data = json.loads(scheduled)
    schedule = data["schedule"]
    # Frame 0 is before first keyframe (10) -> clamp to 0.2
    assert abs(schedule[0][1] - 0.2) < 1e-4
    # Frame 30 is after last keyframe (20) -> clamp to 0.8
    assert abs(schedule[30][1] - 0.8) < 1e-4


def test_negative_frame_returns_error():
    """Bad input: negative start_frame should produce an error."""
    scheduled, status = _run_node(
        lora_model="neg",
        strength_curve='{"type":"linear","start_strength":0.0,"end_strength":1.0}',
        start_frame=-1,
        end_frame=10,
    )
    assert status.startswith("error:")
    assert "start_frame must be >= 0" in status


def test_parse_curve_rejects_non_string():
    """_parse_curve should raise ValueError for non-string input."""
    with pytest.raises(ValueError):
        _parse_curve(12345)


def test_evaluate_linear_clamps_outside_range():
    """_evaluate_linear should clamp t to [0,1] for frames outside the window."""
    # Frame before start
    val = _evaluate_linear(-10, 0, 100, 0.0, 1.0)
    assert abs(val - 0.0) < 1e-6
    # Frame after end
    val = _evaluate_linear(200, 0, 100, 0.0, 1.0)
    assert abs(val - 1.0) < 1e-6


def test_evaluate_keyframes_empty_points():
    """_evaluate_keyframes with empty points list returns 0.0."""
    assert _evaluate_keyframes(5, []) == 0.0


def test_evaluate_keyframes_single_point():
    """_evaluate_keyframes with a single point returns that strength always."""
    assert abs(_evaluate_keyframes(0, [[10, 0.42]]) - 0.42) < 1e-6
    assert abs(_evaluate_keyframes(100, [[10, 0.42]]) - 0.42) < 1e-6


def test_build_schedule_empty_range():
    """_build_schedule with start > end returns empty list (defensive)."""
    schedule = _build_schedule(10, 5, "linear", {"start_strength": 0.0, "end_strength": 1.0})
    assert schedule == []


def test_node_input_types_structure():
    """Verify the node exposes the expected INPUT_TYPES structure."""
    it = PSN_Gradual_LoRA_Apply.INPUT_TYPES()
    assert "required" in it
    assert "lora_model" in it["required"]
    assert "strength_curve" in it["required"]
    assert "start_frame" in it["required"]
    assert "end_frame" in it["required"]
    assert PSN_Gradual_LoRA_Apply.RETURN_TYPES == ("STRING", "STRING")
    assert PSN_Gradual_LoRA_Apply.RETURN_NAMES == ("scheduled_lora", "status")
    assert PSN_Gradual_LoRA_Apply.FUNCTION == "run"
