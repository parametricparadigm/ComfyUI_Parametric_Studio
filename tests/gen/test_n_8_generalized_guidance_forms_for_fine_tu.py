"""Tests for PSN_GeneralizedGuidance node."""

import json
import pytest
from psn_nodes.gen.n_8_generalized_guidance_forms_for_fine_tu import (
    PSN_GeneralizedGuidance,
    compute_guidance,
    _apply_standard,
    _apply_power_law,
    _apply_cfg_plus_plus,
    _validate_inputs,
)


class TestComputeGuidance:
    """Tests for the pure compute_guidance function."""

    def test_power_law_power_1_matches_standard(self):
        """Power Law with power=1.0 should match Standard CFG exactly."""
        cond = [1.0, 2.0, 3.0, 4.0]
        uncond = [0.5, 1.0, 1.5, 2.0]
        cfg_scale = 7.5

        std_ok, std_res, _ = compute_guidance(cond, uncond, "Standard", 1.0, cfg_scale)
        pl_ok, pl_res, _ = compute_guidance(cond, uncond, "PowerLaw", 1.0, cfg_scale)

        assert std_ok is True
        assert pl_ok is True
        for s, p in zip(std_res, pl_res):
            assert abs(s - p) < 1e-10, f"Standard {s} != PowerLaw {p}"

    def test_power_law_power_2_differs_from_standard(self):
        """Power Law with power=2.0 should differ from Standard CFG."""
        cond = [2.0, 4.0, 6.0]
        uncond = [1.0, 2.0, 3.0]
        cfg_scale = 5.0

        std_ok, std_res, _ = compute_guidance(cond, uncond, "Standard", 1.0, cfg_scale)
        pl_ok, pl_res, _ = compute_guidance(cond, uncond, "PowerLaw", 2.0, cfg_scale)

        assert std_ok and pl_ok
        # They should differ because power=2 changes the magnitude
        differs = any(abs(s - p) > 1e-6 for s, p in zip(std_res, pl_res))
        assert differs, "Power Law with power=2 should differ from Standard"

    def test_cfg_plus_plus_amplifies_large_differences(self):
        """CFG++ should amplify guidance where cond-uncond difference is large."""
        cond = [10.0, 1.0]
        uncond = [0.0, 0.0]
        cfg_scale = 2.0
        power = 1.0

        ok, result, _ = compute_guidance(cond, uncond, "CFG++", power, cfg_scale)
        assert ok

        # For diff=10: u + cfg*diff*(1+power*|diff|) = 0 + 2*10*(1+10) = 220
        # For diff=1:  u + cfg*diff*(1+power*|diff|) = 0 + 2*1*(1+1) = 4
        assert abs(result[0] - 220.0) < 1e-10
        assert abs(result[1] - 4.0) < 1e-10

    def test_negative_differences_power_law(self):
        """Power Law should handle negative differences with sign preservation."""
        cond = [0.0, 0.0]
        uncond = [1.0, 2.0]
        cfg_scale = 3.0
        power = 2.0

        ok, result, _ = compute_guidance(cond, uncond, "PowerLaw", power, cfg_scale)
        assert ok

        # diff = -1: sign(-1)*|−1|^2 = -1, result = 1 + 3*(-1) = -2
        # diff = -2: sign(-2)*|−2|^2 = -4, result = 2 + 3*(-4) = -10
        assert abs(result[0] - (-2.0)) < 1e-10
        assert abs(result[1] - (-10.0)) < 1e-10

    def test_invalid_method_rejected(self):
        """Invalid method should return error."""
        ok, result, reason = compute_guidance([1.0], [0.0], "InvalidMethod", 1.0, 7.5)
        assert ok is False
        assert "method" in reason.lower()

    def test_mismatched_lengths_rejected(self):
        """cond and uncond with different lengths should be rejected."""
        ok, result, reason = compute_guidance([1.0, 2.0], [0.0], "Standard", 1.0, 7.5)
        assert ok is False
        assert "same length" in reason

    def test_empty_vectors_rejected(self):
        """Empty vectors should be rejected."""
        ok, result, reason = compute_guidance([], [], "Standard", 1.0, 7.5)
        assert ok is False
        assert "empty" in reason

    def test_out_of_range_power_rejected(self):
        """Power outside valid range should be rejected."""
        ok, result, reason = compute_guidance([1.0], [0.0], "PowerLaw", 15.0, 7.5)
        assert ok is False
        assert "power" in reason.lower()

    def test_out_of_range_cfg_rejected(self):
        """CFG scale outside valid range should be rejected."""
        ok, result, reason = compute_guidance([1.0], [0.0], "Standard", 1.0, 200.0)
        assert ok is False
        assert "cfg_scale" in reason.lower()

    def test_non_numeric_cond_rejected(self):
        """Non-numeric values in cond should be rejected."""
        ok, result, reason = compute_guidance(["a"], [0.0], "Standard", 1.0, 7.5)
        assert ok is False
        assert "number" in reason.lower()


class TestPSN_GeneralizedGuidanceNode:
    """Tests for the ComfyUI node wrapper."""

    def test_node_standard_scalar(self):
        """Node with scalar inputs should work for Standard method."""
        node = PSN_GeneralizedGuidance()
        ok, result_json, reason = node.run(
            cond=2.0, uncond=1.0, method="Standard", power=1.0, cfg_scale=7.5
        )
        assert ok is True
        result = json.loads(result_json)
        # 1.0 + 7.5*(2.0-1.0) = 8.5
        assert abs(result[0] - 8.5) < 1e-10

    def test_node_power_law_vector_json(self):
        """Node with JSON vector inputs should work for PowerLaw."""
        node = PSN_GeneralizedGuidance()
        cond_vec = json.dumps([1.0, 2.0, 3.0])
        uncond_vec = json.dumps([0.0, 0.0, 0.0])
        ok, result_json, reason = node.run(
            cond=0.0, uncond=0.0, method="PowerLaw", power=2.0, cfg_scale=3.0,
            cond_vector=cond_vec, uncond_vector=uncond_vec
        )
        assert ok is True
        result = json.loads(result_json)
        # [0+3*1^2, 0+3*2^2, 0+3*3^2] = [3, 12, 27]
        assert abs(result[0] - 3.0) < 1e-10
        assert abs(result[1] - 12.0) < 1e-10
        assert abs(result[2] - 27.0) < 1e-10

    def test_node_invalid_json_vector(self):
        """Node with invalid JSON vector should return error."""
        node = PSN_GeneralizedGuidance()
        ok, result_json, reason = node.run(
            cond=0.0, uncond=0.0, method="Standard", power=1.0, cfg_scale=7.5,
            cond_vector="not valid json", uncond_vector="[]"
        )
        assert ok is False
        assert "parse" in reason.lower() or "json" in reason.lower()

    def test_node_cfg_plus_plus(self):
        """Node with CFG++ method should compute correctly."""
        node = PSN_GeneralizedGuidance()
        cond_vec = json.dumps([5.0])
        uncond_vec = json.dumps([0.0])
        ok, result_json, reason = node.run(
            cond=0.0, uncond=0.0, method="CFG++", power=0.5, cfg_scale=2.0,
            cond_vector=cond_vec, uncond_vector=uncond_vec
        )
        assert ok is True
        result = json.loads(result_json)
        # diff=5, factor=1+0.5*5=3.5, result=0+2*5*3.5=35
        assert abs(result[0] - 35.0) < 1e-10

    def test_node_bad_method(self):
        """Node with invalid method should return error."""
        node = PSN_GeneralizedGuidance()
        ok, result_json, reason = node.run(
            cond=1.0, uncond=0.0, method="BadMethod", power=1.0, cfg_scale=7.5
        )
        assert ok is False
        assert "method" in reason.lower()

    def test_node_mismatched_vector_lengths(self):
        """Node with mismatched vector lengths should return error."""
        node = PSN_GeneralizedGuidance()
        ok, result_json, reason = node.run(
            cond=0.0, uncond=0.0, method="Standard", power=1.0, cfg_scale=7.5,
            cond_vector="[1.0, 2.0]", uncond_vector="[0.0]"
        )
        assert ok is False
        assert "same length" in reason
