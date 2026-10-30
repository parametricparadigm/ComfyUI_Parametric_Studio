"""
Tests for PSN_FreeU_Patch node.
"""

import json
import math
import pytest

from psn_nodes.gen.n_4_freeu_patching_for_efficiency import (
    PSN_FreeU_Patch,
    build_freeu_descriptor,
    _B1_MIN,
    _B1_MAX,
    _B2_MIN,
    _B2_MAX,
    _S1_MIN,
    _S1_MAX,
    _S2_MIN,
    _S2_MAX,
)


class TestPSNFreeUPatch:
    """Tests for the PSN_FreeU_Patch node and its helper functions."""

    def test_default_values_are_valid(self):
        """Default FreeU parameters should produce a valid descriptor."""
        node = PSN_FreeU_Patch()
        valid, descriptor_json, reason = node.run(1.1, 1.2, 0.9, 0.2)
        assert valid is True
        assert "error" not in descriptor_json
        desc = json.loads(descriptor_json)
        assert desc["patch_type"] == "freeu"
        assert desc["b1"] == 1.1
        assert desc["b2"] == 1.2
        assert desc["s1"] == 0.9
        assert desc["s2"] == 0.2
        assert desc["target_architecture"] == "unet"
        assert "safe range" in reason

    def test_boundary_values_are_valid(self):
        """Values exactly at the safe range boundaries should be accepted."""
        ok, desc, reason = build_freeu_descriptor(_B1_MIN, _B2_MIN, _S1_MIN, _S2_MIN)
        assert ok is True
        assert desc["b1"] == _B1_MIN
        assert desc["s2"] == _S2_MIN

        ok, desc, reason = build_freeu_descriptor(_B1_MAX, _B2_MAX, _S1_MAX, _S2_MAX)
        assert ok is True
        assert desc["b1"] == _B1_MAX
        assert desc["s2"] == _S2_MAX

    def test_b1_below_minimum_is_invalid(self):
        """b1 below the safe minimum should be rejected."""
        ok, desc, reason = build_freeu_descriptor(0.1, 1.2, 0.9, 0.2)
        assert ok is False
        assert desc is None
        assert "b1" in reason
        assert "below minimum" in reason

    def test_s2_above_maximum_is_invalid(self):
        """s2 above the safe maximum should be rejected."""
        ok, desc, reason = build_freeu_descriptor(1.1, 1.2, 0.9, 1.5)
        assert ok is False
        assert desc is None
        assert "s2" in reason
        assert "above maximum" in reason

    def test_non_numeric_input_is_invalid(self):
        """Non-numeric inputs should be rejected gracefully."""
        ok, desc, reason = build_freeu_descriptor("1.1", 1.2, 0.9, 0.2)
        assert ok is False
        assert desc is None
        assert "must be a number" in reason

        ok, desc, reason = build_freeu_descriptor(1.1, None, 0.9, 0.2)
        assert ok is False
        assert "b2" in reason

    def test_nan_and_inf_are_invalid(self):
        """NaN and infinity values should be rejected."""
        ok, desc, reason = build_freeu_descriptor(float("nan"), 1.2, 0.9, 0.2)
        assert ok is False
        assert "finite" in reason

        ok, desc, reason = build_freeu_descriptor(1.1, float("inf"), 0.9, 0.2)
        assert ok is False
        assert "finite" in reason

        ok, desc, reason = build_freeu_descriptor(1.1, 1.2, float("-inf"), 0.2)
        assert ok is False
        assert "finite" in reason

    def test_extremely_large_value_is_invalid(self):
        """Values with magnitude exceeding the guard limit should be rejected."""
        ok, desc, reason = build_freeu_descriptor(1e9, 1.2, 0.9, 0.2)
        assert ok is False
        assert "too large" in reason

    def test_multiple_invalid_parameters_report_all(self):
        """When multiple parameters are out of range, all should be reported."""
        ok, desc, reason = build_freeu_descriptor(0.1, 3.0, 0.0, 1.5)
        assert ok is False
        assert "b1" in reason
        assert "b2" in reason
        assert "s1" in reason
        assert "s2" in reason

    def test_descriptor_json_is_well_formed(self):
        """The descriptor JSON should be parseable and contain expected keys."""
        ok, desc, reason = build_freeu_descriptor(1.0, 1.0, 1.0, 0.5)
        assert ok is True
        parsed = json.loads(json.dumps(desc))
        expected_keys = {"patch_type", "b1", "b2", "s1", "s2", "target_architecture", "note"}
        assert expected_keys.issubset(set(parsed.keys()))

    def test_node_returns_string_descriptor_on_error(self):
        """On invalid input, the node should return a JSON error string, not None."""
        node = PSN_FreeU_Patch()
        valid, descriptor_json, reason = node.run(99.0, 1.2, 0.9, 0.2)
        assert valid is False
        parsed = json.loads(descriptor_json)
        assert "error" in parsed
        assert "b1" in parsed["error"]

    def test_integer_inputs_are_accepted(self):
        """Integer values (which are valid numbers) should be accepted."""
        ok, desc, reason = build_freeu_descriptor(1, 1, 1, 0)
        assert ok is True
        assert desc["b1"] == 1.0
        assert desc["s2"] == 0.0

    def test_input_types_structure(self):
        """INPUT_TYPES should define the four required float parameters."""
        it = PSN_FreeU_Patch.INPUT_TYPES()
        assert "required" in it
        req = it["required"]
        assert "b1" in req
        assert "b2" in req
        assert "s1" in req
        assert "s2" in req
        for key in ("b1", "b2", "s1", "s2"):
            assert req[key][0] == "FLOAT"
            assert "default" in req[key][1]
