"""Tests for psn_nodes.gen.n_3_fast_sampling_with_res4lyf."""

import json
import pytest

from psn_nodes.gen.n_3_fast_sampling_with_res4lyf import (
    PSN_RES4LYF_Sampler,
    psn_validate_solver,
    psn_validate_scheduler,
    psn_validate_steps,
    psn_build_schedule,
    psn_quality_estimate,
)


class TestPsnValidateSolver:
    def test_valid_solver(self):
        ok, reason = psn_validate_solver("RES4LYF")
        assert ok is True
        assert reason == "ok"

    def test_valid_solver_bongmath(self):
        ok, reason = psn_validate_solver("BongMath")
        assert ok is True

    def test_invalid_solver(self):
        ok, reason = psn_validate_solver("UniPC")
        assert ok is False
        assert "not in allow-list" in reason

    def test_non_string_solver(self):
        ok, reason = psn_validate_solver(42)
        assert ok is False
        assert "must be a string" in reason


class TestPsnValidateScheduler:
    def test_valid_scheduler_linear(self):
        ok, _ = psn_validate_scheduler("Linear")
        assert ok is True

    def test_valid_scheduler_karras(self):
        ok, _ = psn_validate_scheduler("Karras")
        assert ok is True

    def test_invalid_scheduler(self):
        ok, reason = psn_validate_scheduler("Exponential")
        assert ok is False
        assert "not in allow-list" in reason

    def test_non_string_scheduler(self):
        ok, reason = psn_validate_scheduler(None)
        assert ok is False


class TestPsnValidateSteps:
    def test_valid_steps(self):
        ok, _ = psn_validate_steps(15)
        assert ok is True

    def test_steps_below_min(self):
        ok, reason = psn_validate_steps(0)
        assert ok is False
        assert "must be in" in reason

    def test_steps_above_max(self):
        ok, reason = psn_validate_steps(101)
        assert ok is False

    def test_non_integer_steps(self):
        ok, reason = psn_validate_steps(15.5)
        assert ok is False
        assert "must be an integer" in reason

    def test_bool_rejected(self):
        ok, reason = psn_validate_steps(True)
        assert ok is False


class TestPsnBuildSchedule:
    def test_linear_schedule_length(self):
        sched = psn_build_schedule(10, "Linear")
        assert len(sched) == 10

    def test_linear_schedule_values(self):
        sched = psn_build_schedule(4, "Linear")
        assert sched[0] == pytest.approx(1.0)
        assert sched[-1] == pytest.approx(0.25)
        for v in sched:
            assert 0.0 < v <= 1.0

    def test_karras_schedule_length(self):
        sched = psn_build_schedule(10, "Karras")
        assert len(sched) == 10

    def test_karras_schedule_bounds(self):
        sched = psn_build_schedule(20, "Karras")
        for v in sched:
            assert 0.0 < v <= 1.0
        # Karras should start near 1.0 and end near sigma_min
        assert sched[0] == pytest.approx(1.0, abs=0.01)
        assert sched[-1] < 0.01

    def test_single_step_linear(self):
        sched = psn_build_schedule(1, "Linear")
        assert sched == [1.0]

    def test_single_step_karras(self):
        sched = psn_build_schedule(1, "Karras")
        assert len(sched) == 1
        assert sched[0] == pytest.approx(1.0)

    def test_unknown_scheduler_raises(self):
        with pytest.raises(ValueError, match="unknown scheduler"):
            psn_build_schedule(10, "Exponential")


class TestPsnQualityEstimate:
    def test_res4lyf_in_band(self):
        in_band, reason = psn_quality_estimate(15, "RES4LYF")
        assert in_band is True
        assert "within recommended" in reason

    def test_res4lyf_below_band(self):
        in_band, reason = psn_quality_estimate(5, "RES4LYF")
        assert in_band is False
        assert "below recommended" in reason

    def test_res4lyf_above_band(self):
        in_band, reason = psn_quality_estimate(30, "RES4LYF")
        assert in_band is False
        assert "above recommended" in reason

    def test_bongmath_wider_band(self):
        in_band, _ = psn_quality_estimate(8, "BongMath")
        assert in_band is True
        in_band2, _ = psn_quality_estimate(24, "BongMath")
        assert in_band2 is True

    def test_unknown_solver(self):
        in_band, reason = psn_quality_estimate(15, "Unknown")
        assert in_band is False
        assert "unknown solver" in reason


class TestPsnRes4lyfSamplerNode:
    def test_valid_config(self):
        node = PSN_RES4LYF_Sampler()
        valid, schedule_json, in_band, reason = node.run(15, "RES4LYF", "Linear")
        assert valid is True
        assert in_band == "yes"
        # schedule_json should be parseable
        sched = json.loads(schedule_json)
        assert len(sched) == 15
        for v in sched:
            assert 0.0 < v <= 1.0

    def test_invalid_solver(self):
        node = PSN_RES4LYF_Sampler()
        valid, schedule_json, in_band, reason = node.run(15, "UniPC", "Linear")
        assert valid is False
        assert schedule_json == ""
        assert in_band == "no"
        assert "not in allow-list" in reason

    def test_invalid_scheduler(self):
        node = PSN_RES4LYF_Sampler()
        valid, _, _, reason = node.run(15, "RES4LYF", "Exponential")
        assert valid is False
        assert "not in allow-list" in reason

    def test_invalid_steps(self):
        node = PSN_RES4LYF_Sampler()
        valid, _, _, reason = node.run(0, "RES4LYF", "Linear")
        assert valid is False
        assert "must be in" in reason

    def test_karras_schedule_output(self):
        node = PSN_RES4LYF_Sampler()
        valid, schedule_json, in_band, reason = node.run(10, "RES4LYF", "Karras")
        assert valid is True
        sched = json.loads(schedule_json)
        assert len(sched) == 10
        assert sched[0] == pytest.approx(1.0, abs=0.01)

    def test_steps_out_of_band(self):
        node = PSN_RES4LYF_Sampler()
        valid, _, in_band, reason = node.run(50, "RES4LYF", "Linear")
        assert valid is True
        assert in_band == "no"
        assert "above recommended" in reason

    def test_input_types_structure(self):
        it = PSN_RES4LYF_Sampler.INPUT_TYPES()
        assert "required" in it
        assert "steps" in it["required"]
        assert "solver" in it["required"]
        assert "scheduler" in it["required"]
        # solver and scheduler should be COMBO (list) types
        assert isinstance(it["required"]["solver"][0], list)
        assert isinstance(it["required"]["scheduler"][0], list)

    def test_return_types(self):
        assert PSN_RES4LYF_Sampler.RETURN_TYPES == ("BOOLEAN", "STRING", "STRING", "STRING")
        assert PSN_RES4LYF_Sampler.RETURN_NAMES == ("valid", "schedule_json", "quality_in_band", "reason")
        assert PSN_RES4LYF_Sampler.FUNCTION == "run"
