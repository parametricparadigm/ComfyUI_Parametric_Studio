"""
Tests for PSN_ScheduledCFG node.
"""

import json
import math
import pytest

from psn_nodes.gen.n_5_scheduled_cfg_for_complex_prompts import (
    PSN_ScheduledCFG,
    _validate_schedule,
    compute_cfg_at_step,
    _interpolate_linear,
    _interpolate_smoothstep,
    _interpolate_cosine,
)


class TestValidateSchedule:
    """Tests for schedule validation."""

    def test_valid_schedule(self):
        schedule_json = "[[0.0, 7.5], [0.5, 5.0], [1.0, 2.5]]"
        schedule, error = _validate_schedule(schedule_json)
        assert error is None
        assert schedule == [(0.0, 7.5), (0.5, 5.0), (1.0, 2.5)]

    def test_invalid_json(self):
        schedule_json = "not valid json"
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "Invalid JSON" in error

    def test_not_a_list(self):
        schedule_json = '{"a": 1}'
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "must be a JSON array" in error

    def test_too_few_points(self):
        schedule_json = "[[0.0, 7.5]]"
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "at least 2 points" in error

    def test_invalid_point_structure(self):
        schedule_json = "[[0.0, 7.5], [0.5]]"
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "must be a [step_percent, cfg_value] pair" in error

    def test_step_percent_out_of_range(self):
        schedule_json = "[[0.0, 7.5], [1.5, 5.0]]"
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "step_percent must be between" in error

    def test_cfg_value_out_of_range(self):
        schedule_json = "[[0.0, 7.5], [0.5, 200.0]]"
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "cfg_value must be between" in error

    def test_duplicate_step_percent(self):
        schedule_json = "[[0.5, 7.5], [0.5, 5.0]]"
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "Duplicate step_percent" in error

    def test_non_numeric_values(self):
        # Use a valid JSON structure with a string value to test type checking
        schedule_json = "[[0.0, 7.5], [\"a\", 5.0]]"
        schedule, error = _validate_schedule(schedule_json)
        assert schedule is None
        assert "step_percent must be a number" in error

    def test_non_string_input(self):
        schedule, error = _validate_schedule(123)
        assert schedule is None
        assert "must be a JSON string" in error


class TestInterpolationFunctions:
    """Tests for individual interpolation functions."""

    def test_linear_endpoints(self):
        assert _interpolate_linear(0.0) == 0.0
        assert _interpolate_linear(1.0) == 1.0

    def test_linear_midpoint(self):
        assert _interpolate_linear(0.5) == 0.5

    def test_smoothstep_endpoints(self):
        assert _interpolate_smoothstep(0.0) == 0.0
        assert _interpolate_smoothstep(1.0) == 1.0

    def test_smoothstep_midpoint(self):
        # 3*(0.5)^2 - 2*(0.5)^3 = 0.75 - 0.25 = 0.5
        assert _interpolate_smoothstep(0.5) == 0.5

    def test_cosine_endpoints(self):
        assert _interpolate_cosine(0.0) == 0.0
        assert _interpolate_cosine(1.0) == 1.0

    def test_cosine_midpoint(self):
        # (1 - cos(pi/2)) / 2 = (1 - 0) / 2 = 0.5
        assert abs(_interpolate_cosine(0.5) - 0.5) < 1e-9


class TestComputeCfgAtStep:
    """Tests for the main CFG computation function."""

    def test_at_first_point(self):
        schedule = [(0.0, 7.5), (0.5, 5.0), (1.0, 2.5)]
        cfg = compute_cfg_at_step(schedule, 0.0, "Linear")
        assert cfg == 7.5

    def test_at_last_point(self):
        schedule = [(0.0, 7.5), (0.5, 5.0), (1.0, 2.5)]
        cfg = compute_cfg_at_step(schedule, 1.0, "Linear")
        assert cfg == 2.5

    def test_linear_midpoint(self):
        schedule = [(0.0, 7.5), (1.0, 2.5)]
        cfg = compute_cfg_at_step(schedule, 0.5, "Linear")
        # Linear interpolation: 7.5 + (2.5 - 7.5) * 0.5 = 7.5 - 2.5 = 5.0
        assert abs(cfg - 5.0) < 1e-9

    def test_smoothstep_midpoint(self):
        schedule = [(0.0, 7.5), (1.0, 2.5)]
        cfg = compute_cfg_at_step(schedule, 0.5, "Smoothstep")
        # Smoothstep at t=0.5 is 0.5, so same as linear for symmetric endpoints
        assert abs(cfg - 5.0) < 1e-9

    def test_cosine_midpoint(self):
        schedule = [(0.0, 7.5), (1.0, 2.5)]
        cfg = compute_cfg_at_step(schedule, 0.5, "Cosine")
        # Cosine at t=0.5 is 0.5, so same as linear for symmetric endpoints
        assert abs(cfg - 5.0) < 1e-9

    def test_step_before_first_point(self):
        schedule = [(0.2, 7.5), (1.0, 2.5)]
        cfg = compute_cfg_at_step(schedule, 0.0, "Linear")
        assert cfg == 7.5

    def test_step_after_last_point(self):
        schedule = [(0.0, 7.5), (0.8, 2.5)]
        cfg = compute_cfg_at_step(schedule, 1.0, "Linear")
        assert cfg == 2.5

    def test_multiple_segments(self):
        schedule = [(0.0, 10.0), (0.5, 5.0), (1.0, 0.0)]
        # At step 0.25, between (0.0, 10.0) and (0.5, 5.0)
        cfg = compute_cfg_at_step(schedule, 0.25, "Linear")
        # t = (0.25 - 0.0) / (0.5 - 0.0) = 0.5
        # cfg = 10.0 + (5.0 - 10.0) * 0.5 = 10.0 - 2.5 = 7.5
        assert abs(cfg - 7.5) < 1e-9

        # At step 0.75, between (0.5, 5.0) and (1.0, 0.0)
        cfg = compute_cfg_at_step(schedule, 0.75, "Linear")
        # t = (0.75 - 0.5) / (1.0 - 0.5) = 0.5
        # cfg = 5.0 + (0.0 - 5.0) * 0.5 = 5.0 - 2.5 = 2.5
        assert abs(cfg - 2.5) < 1e-9

    def test_empty_schedule_raises(self):
        with pytest.raises(ValueError):
            compute_cfg_at_step([], 0.5, "Linear")

    def test_invalid_mode_raises(self):
        schedule = [(0.0, 7.5), (1.0, 2.5)]
        with pytest.raises(ValueError):
            compute_cfg_at_step(schedule, 0.5, "InvalidMode")


class TestPSNScheduledCFGNode:
    """Tests for the PSN_ScheduledCFG node class."""

    def test_node_run_valid(self):
        node = PSN_ScheduledCFG()
        cfg_value, parsed_schedule, status = node.run(
            schedule='[[0.0, 7.5], [0.5, 5.0], [1.0, 2.5]]',
            interpolation="Linear",
            step_percent=0.0
        )
        assert cfg_value == 7.5
        assert "CFG=7.5000" in status
        parsed = json.loads(parsed_schedule)
        assert parsed == [[0.0, 7.5], [0.5, 5.0], [1.0, 2.5]]

    def test_node_run_midpoint(self):
        node = PSN_ScheduledCFG()
        cfg_value, parsed_schedule, status = node.run(
            schedule='[[0.0, 7.5], [1.0, 2.5]]',
            interpolation="Linear",
            step_percent=0.5
        )
        assert abs(cfg_value - 5.0) < 1e-9

    def test_node_run_invalid_schedule(self):
        node = PSN_ScheduledCFG()
        cfg_value, parsed_schedule, status = node.run(
            schedule='invalid json',
            interpolation="Linear",
            step_percent=0.5
        )
        assert cfg_value == 0.0
        assert "Error" in status

    def test_node_run_invalid_interpolation(self):
        node = PSN_ScheduledCFG()
        cfg_value, parsed_schedule, status = node.run(
            schedule='[[0.0, 7.5], [1.0, 2.5]]',
            interpolation="InvalidMode",
            step_percent=0.5
        )
        assert cfg_value == 0.0
        assert "Unknown interpolation mode" in status

    def test_node_run_smoothstep(self):
        node = PSN_ScheduledCFG()
        cfg_value, parsed_schedule, status = node.run(
            schedule='[[0.0, 10.0], [1.0, 0.0]]',
            interpolation="Smoothstep",
            step_percent=0.5
        )
        # Smoothstep at t=0.5 is 0.5, so cfg = 10.0 + (0.0 - 10.0) * 0.5 = 5.0
        assert abs(cfg_value - 5.0) < 1e-9

    def test_node_run_cosine(self):
        node = PSN_ScheduledCFG()
        cfg_value, parsed_schedule, status = node.run(
            schedule='[[0.0, 10.0], [1.0, 0.0]]',
            interpolation="Cosine",
            step_percent=0.5
        )
        # Cosine at t=0.5 is 0.5, so cfg = 10.0 + (0.0 - 10.0) * 0.5 = 5.0
        assert abs(cfg_value - 5.0) < 1e-9

    def test_node_run_step_clamped(self):
        node = PSN_ScheduledCFG()
        # Step percent > 1.0 should be clamped to 1.0
        cfg_value, parsed_schedule, status = node.run(
            schedule='[[0.0, 7.5], [1.0, 2.5]]',
            interpolation="Linear",
            step_percent=1.5
        )
        assert cfg_value == 2.5

    def test_node_run_step_negative_clamped(self):
        node = PSN_ScheduledCFG()
        # Step percent < 0.0 should be clamped to 0.0
        cfg_value, parsed_schedule, status = node.run(
            schedule='[[0.0, 7.5], [1.0, 2.5]]',
            interpolation="Linear",
            step_percent=-0.5
        )
        assert cfg_value == 7.5

    def test_node_return_types(self):
        assert PSN_ScheduledCFG.RETURN_TYPES == ("FLOAT", "STRING", "STRING")
        assert PSN_ScheduledCFG.RETURN_NAMES == ("cfg_value", "parsed_schedule", "status")
        assert PSN_ScheduledCFG.FUNCTION == "run"
        assert PSN_ScheduledCFG.CATEGORY == "ParametricStudio/ScheduledCFG"

    def test_node_input_types(self):
        input_types = PSN_ScheduledCFG.INPUT_TYPES()
        assert "schedule" in input_types["required"]
        assert "interpolation" in input_types["required"]
        assert "step_percent" in input_types["required"]
        # The interpolation input is a tuple containing the list of modes
        assert input_types["required"]["interpolation"] == (["Linear", "Smoothstep", "Cosine"],)
