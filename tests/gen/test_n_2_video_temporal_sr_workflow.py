"""Tests for psn_nodes.gen.n_2_video_temporal_sr_workflow."""

import json

from psn_nodes.gen.n_2_video_temporal_sr_workflow import (
    PSN_Video_Temporal_SR,
    _validate_model,
    _validate_scale,
    _validate_window,
    _build_plan,
)


def test_valid_basic_plan():
    """A valid 16-frame 256x256 clip at 2x scale, window 5 produces correct plan."""
    node = PSN_Video_Temporal_SR()
    plan_json, status, out_w, out_h, num_windows, vram = node.run(
        num_frames=16,
        in_width=256,
        in_height=256,
        MODEL_PATH="iseebetter_basicvsr_plus",
        SCALE=2,
        TEMPORAL_WINDOW=5,
    )
    assert status == "OK"
    assert out_w == 512
    assert out_h == 512
    # ceil(16 / 5) = 4 windows
    assert num_windows == 4
    plan = json.loads(plan_json)
    assert plan["num_frames"] == 16
    assert plan["scale"] == 2
    assert plan["window"] == 5
    assert plan["out_w"] == 512
    assert plan["out_h"] == 512
    assert plan["num_windows"] == 4
    assert plan["frames_per_window"] == 5


def test_batch_size_preserved_in_plan():
    """The plan must record the exact input frame count."""
    node = PSN_Video_Temporal_SR()
    plan_json, status, *_ = node.run(
        num_frames=33,
        in_width=128,
        in_height=96,
        MODEL_PATH="basicvsr_plus_x2",
        SCALE=2,
        TEMPORAL_WINDOW=8,
    )
    assert status == "OK"
    plan = json.loads(plan_json)
    assert plan["num_frames"] == 33
    # ceil(33 / 8) = 5
    assert plan["num_windows"] == 5


def test_output_resolution_is_scale_times_input():
    """Output dimensions must equal input * SCALE for all supported scales."""
    node = PSN_Video_Temporal_SR()
    for scale in (1, 2, 3, 4):
        plan_json, status, out_w, out_h, _, _ = node.run(
            num_frames=4,
            in_width=100,
            in_height=80,
            MODEL_PATH="iseebetter_basicvsr_plus",
            SCALE=scale,
            TEMPORAL_WINDOW=4,
        )
        assert status == "OK"
        assert out_w == 100 * scale
        assert out_h == 80 * scale


def test_empty_frame_batch():
    """Zero frames should still produce a valid plan with a warning."""
    node = PSN_Video_Temporal_SR()
    plan_json, status, out_w, out_h, num_windows, _ = node.run(
        num_frames=0,
        in_width=256,
        in_height=256,
        MODEL_PATH="iseebetter_basicvsr_plus",
        SCALE=2,
        TEMPORAL_WINDOW=5,
    )
    assert "warnings" in status
    plan = json.loads(plan_json)
    assert plan["num_frames"] == 0
    assert plan["num_windows"] == 0
    assert any("Empty frame batch" in w for w in plan["warnings"])


def test_invalid_model_path_rejected():
    """A model not in the allow-list must be rejected."""
    node = PSN_Video_Temporal_SR()
    plan_json, status, out_w, out_h, num_windows, _ = node.run(
        num_frames=8,
        in_width=256,
        in_height=256,
        MODEL_PATH="totally_unknown_model",
        SCALE=2,
        TEMPORAL_WINDOW=5,
    )
    assert status.startswith("ERROR")
    assert "allow-list" in status
    assert out_w == 0
    assert out_h == 0
    assert num_windows == 0
    assert plan_json == "{}"


def test_invalid_scale_rejected():
    """A scale not in the supported set must be rejected."""
    node = PSN_Video_Temporal_SR()
    plan_json, status, *_ = node.run(
        num_frames=8,
        in_width=256,
        in_height=256,
        MODEL_PATH="iseebetter_basicvsr_plus",
        SCALE=5,  # not in (1,2,3,4)
        TEMPORAL_WINDOW=5,
    )
    assert status.startswith("ERROR")
    assert "SCALE" in status
    assert plan_json == "{}"


def test_invalid_temporal_window_rejected():
    """A temporal window outside [1, 32] must be rejected."""
    node = PSN_Video_Temporal_SR()
    # Too large
    plan_json, status, *_ = node.run(
        num_frames=8,
        in_width=256,
        in_height=256,
        MODEL_PATH="iseebetter_basicvsr_plus",
        SCALE=2,
        TEMPORAL_WINDOW=64,
    )
    assert status.startswith("ERROR")
    assert "TEMPORAL_WINDOW" in status

    # Too small (0)
    plan_json, status, *_ = node.run(
        num_frames=8,
        in_width=256,
        in_height=256,
        MODEL_PATH="iseebetter_basicvsr_plus",
        SCALE=2,
        TEMPORAL_WINDOW=0,
    )
    assert status.startswith("ERROR")
    assert "TEMPORAL_WINDOW" in status


def test_vram_warning_for_large_window():
    """A large temporal window at high resolution should trigger a VRAM warning."""
    node = PSN_Video_Temporal_SR()
    plan_json, status, *_ = node.run(
        num_frames=32,
        in_width=1024,
        in_height=1024,
        MODEL_PATH="iseebetter_basicvsr_plus",
        SCALE=4,
        TEMPORAL_WINDOW=32,
    )
    assert "warnings" in status
    plan = json.loads(plan_json)
    assert any("VRAM" in w for w in plan["warnings"])


def test_validate_model_helper():
    """Unit-test the model validator directly."""
    ok, why = _validate_model("iseebetter_basicvsr_plus")
    assert ok is True
    ok, why = _validate_model("")
    assert ok is False
    ok, why = _validate_model(123)
    assert ok is False
    ok, why = _validate_model("not_a_model")
    assert ok is False


def test_validate_scale_helper():
    """Unit-test the scale validator directly."""
    ok, _ = _validate_scale(2)
    assert ok is True
    ok, _ = _validate_scale(0)
    assert ok is False
    ok, _ = _validate_scale(5)
    assert ok is False
    ok, _ = _validate_scale(True)  # bool is subclass of int; must reject
    assert ok is False


def test_validate_window_helper():
    """Unit-test the window validator directly."""
    ok, _ = _validate_window(5)
    assert ok is True
    ok, _ = _validate_window(0)
    assert ok is False
    ok, _ = _validate_window(33)
    assert ok is False
    ok, _ = _validate_window(-1)
    assert ok is False


def test_build_plan_exact_window_division():
    """When num_frames is exactly divisible by window, no partial window."""
    plan = _build_plan(10, 256, 256, 2, 5, "iseebetter_basicvsr_plus")
    assert plan["num_windows"] == 2
    assert plan["frames_per_window"] == 5
    assert plan["out_w"] == 512
    assert plan["out_h"] == 512
