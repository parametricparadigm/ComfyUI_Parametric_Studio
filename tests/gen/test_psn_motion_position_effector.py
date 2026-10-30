"""
Tests for PSN_Motion_Position_Effector
"""

import pytest
from psn_nodes.gen.psn_motion_position_effector import (
    PSN_Motion_Position_Effector,
    validate_motion_config,
    compute_frame_offsets,
    compute_trajectory,
    _ease_linear,
    _ease_in,
    _ease_out,
    _ease_in_out,
)


class TestEasingFunctions:
    def test_linear_easing(self):
        assert _ease_linear(0.0) == 0.0
        assert _ease_linear(0.5) == 0.5
        assert _ease_linear(1.0) == 1.0

    def test_ease_in(self):
        assert _ease_in(0.0) == 0.0
        assert _ease_in(1.0) == 1.0
        assert _ease_in(0.5) == 0.25

    def test_ease_out(self):
        assert _ease_out(0.0) == 0.0
        assert _ease_out(1.0) == 1.0
        assert _ease_out(0.5) == 0.75

    def test_ease_in_out(self):
        assert _ease_in_out(0.0) == 0.0
        assert _ease_in_out(1.0) == 1.0
        assert _ease_in_out(0.5) == 0.5


class TestValidateMotionConfig:
    def test_valid_config(self):
        is_valid, msg = validate_motion_config((0, 0), (100, 50), 30, "linear")
        assert is_valid is True
        assert msg == ""

    def test_invalid_start_pos_not_tuple(self):
        is_valid, msg = validate_motion_config(0, (100, 50), 30, "linear")
        assert is_valid is False
        assert "start_pos" in msg

    def test_invalid_start_pos_wrong_length(self):
        is_valid, msg = validate_motion_config((0,), (100, 50), 30, "linear")
        assert is_valid is False
        assert "start_pos" in msg

    def test_invalid_start_pos_non_int(self):
        is_valid, msg = validate_motion_config((0.5, 0), (100, 50), 30, "linear")
        assert is_valid is False
        assert "start_pos" in msg

    def test_invalid_end_pos_not_tuple(self):
        is_valid, msg = validate_motion_config((0, 0), 100, 30, "linear")
        assert is_valid is False
        assert "end_pos" in msg

    def test_invalid_duration_zero(self):
        is_valid, msg = validate_motion_config((0, 0), (100, 50), 0, "linear")
        assert is_valid is False
        assert "duration" in msg

    def test_invalid_duration_negative(self):
        is_valid, msg = validate_motion_config((0, 0), (100, 50), -5, "linear")
        assert is_valid is False
        assert "duration" in msg

    def test_invalid_duration_too_large(self):
        is_valid, msg = validate_motion_config((0, 0), (100, 50), 10001, "linear")
        assert is_valid is False
        assert "duration" in msg

    def test_invalid_easing(self):
        is_valid, msg = validate_motion_config((0, 0), (100, 50), 30, "bounce")
        assert is_valid is False
        assert "easing" in msg

    def test_invalid_easing_not_string(self):
        is_valid, msg = validate_motion_config((0, 0), (100, 50), 30, 123)
        assert is_valid is False
        assert "easing" in msg


class TestComputeFrameOffsets:
    def test_linear_offsets(self):
        offsets = compute_frame_offsets((0, 0), (100, 50), 11, "linear")
        assert len(offsets) == 11
        assert offsets[0] == (0, 0)
        assert offsets[10] == (100, 50)
        assert offsets[5] == (50, 25)

    def test_single_frame(self):
        offsets = compute_frame_offsets((10, 20), (30, 40), 1, "linear")
        assert len(offsets) == 1
        assert offsets[0] == (20, 20)

    def test_ease_in_offsets(self):
        offsets = compute_frame_offsets((0, 0), (100, 0), 3, "ease_in")
        assert len(offsets) == 3
        assert offsets[0] == (0, 0)
        assert offsets[2] == (100, 0)
        # ease_in: t=0.5 -> 0.25, so dx = 25
        assert offsets[1] == (25, 0)

    def test_ease_out_offsets(self):
        offsets = compute_frame_offsets((0, 0), (100, 0), 3, "ease_out")
        assert len(offsets) == 3
        assert offsets[0] == (0, 0)
        assert offsets[2] == (100, 0)
        # ease_out: t=0.5 -> 0.75, so dx = 75
        assert offsets[1] == (75, 0)

    def test_negative_direction(self):
        offsets = compute_frame_offsets((100, 100), (0, 0), 11, "linear")
        assert offsets[0] == (0, 0)
        assert offsets[10] == (-100, -100)
        assert offsets[5] == (-50, -50)


class TestComputeTrajectory:
    def test_linear_trajectory(self):
        traj = compute_trajectory((0, 0), (100, 50), 11, "linear")
        assert len(traj) == 11
        assert traj[0] == (0, 0)
        assert traj[10] == (100, 50)
        assert traj[5] == (50, 25)

    def test_trajectory_with_offset_start(self):
        traj = compute_trajectory((10, 20), (110, 70), 11, "linear")
        assert traj[0] == (10, 20)
        assert traj[10] == (110, 70)
        assert traj[5] == (60, 45)

    def test_single_frame_trajectory(self):
        traj = compute_trajectory((5, 5), (15, 15), 1, "linear")
        assert len(traj) == 1
        assert traj[0] == (15, 15)


class TestNodeRun:
    def test_run_success(self):
        node = PSN_Motion_Position_Effector()
        offsets_str, traj_str, status = node.run(0, 0, 100, 50, 11, "linear")
        assert status == "success"
        assert "0, 0" in offsets_str
        assert "100, 50" in offsets_str

    def test_run_invalid_duration(self):
        node = PSN_Motion_Position_Effector()
        offsets_str, traj_str, status = node.run(0, 0, 100, 50, 0, "linear")
        assert status.startswith("Error:")
        assert offsets_str == ""
        assert traj_str == ""

    def test_run_invalid_easing(self):
        node = PSN_Motion_Position_Effector()
        offsets_str, traj_str, status = node.run(0, 0, 100, 50, 30, "bounce")
        assert status.startswith("Error:")
        assert "easing" in status

    def test_run_ease_in_out(self):
        node = PSN_Motion_Position_Effector()
        offsets_str, traj_str, status = node.run(0, 0, 100, 0, 3, "ease_in_out")
        assert status == "success"
        # ease_in_out at t=0.5 -> 0.5, so dx=50
        assert "(50, 0)" in offsets_str

    def test_input_types_structure(self):
        input_types = PSN_Motion_Position_Effector.INPUT_TYPES()
        assert "required" in input_types
        assert "start_pos_x" in input_types["required"]
        assert "end_pos_x" in input_types["required"]
        assert "duration" in input_types["required"]
        assert "easing" in input_types["required"]
        assert "optional" in input_types

    def test_return_types(self):
        assert PSN_Motion_Position_Effector.RETURN_TYPES == ("STRING", "STRING", "STRING")
        assert PSN_Motion_Position_Effector.RETURN_NAMES == ("animated_offsets", "trajectory", "status")
        assert PSN_Motion_Position_Effector.FUNCTION == "run"
        assert PSN_Motion_Position_Effector.CATEGORY == "ParametricStudio/Motion"
