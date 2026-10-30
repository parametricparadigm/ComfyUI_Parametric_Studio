"""Tests for psn_nodes.gen.psn_cfg_steering_vector."""

import json
import math
import pytest

from psn_nodes.gen.psn_cfg_steering_vector import (
    PSN_CFG_Steering_Vector,
    compute_cfg_with_steering,
    _parse_vector,
    _validate_strength,
    _validate_cond_uncond,
)


class TestParseVector:
    def test_scalar_float(self):
        assert _parse_vector(3.0) == [3.0]

    def test_scalar_int(self):
        assert _parse_vector(2) == [2.0]

    def test_json_list_string(self):
        assert _parse_vector("[1.0, 2.0, 3.0]") == [1.0, 2.0, 3.0]

    def test_json_scalar_string(self):
        assert _parse_vector("4.5") == [4.5]

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _parse_vector("")

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_vector("not json")

    def test_non_numeric_element_raises(self):
        with pytest.raises(ValueError, match="not a number"):
            _parse_vector("[1.0, \"a\", 3.0]")

    def test_nan_element_raises(self):
        with pytest.raises(ValueError, match="NaN or Inf"):
            _parse_vector("[1.0, NaN]")

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _parse_vector("[]")

    def test_wrong_type_raises(self):
        with pytest.raises(ValueError, match="must be a number or a JSON string"):
            _parse_vector([1.0, 2.0])


class TestValidateStrength:
    def test_valid_float(self):
        assert _validate_strength(1.5) == 1.5

    def test_valid_int(self):
        assert _validate_strength(2) == 2.0

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="finite"):
            _validate_strength(float("nan"))

    def test_inf_raises(self):
        with pytest.raises(ValueError, match="finite"):
            _validate_strength(float("inf"))

    def test_string_raises(self):
        with pytest.raises(ValueError, match="must be a number"):
            _validate_strength("1.0")


class TestValidateCondUncond:
    def test_matching_scalars(self):
        c, u = _validate_cond_uncond(1.0, 2.0)
        assert c == [1.0]
        assert u == [2.0]

    def test_matching_lists(self):
        c, u = _validate_cond_uncond("[1,2]", "[3,4]")
        assert c == [1.0, 2.0]
        assert u == [3.0, 4.0]

    def test_mismatched_dims_raises(self):
        with pytest.raises(ValueError, match="same dimensionality"):
            _validate_cond_uncond("[1,2]", "[3,4,5]")

    def test_nan_in_cond_raises(self):
        with pytest.raises(ValueError, match="finite"):
            _validate_cond_uncond("NaN", 1.0)


class TestComputeCFGWithSteering:
    def test_basic_scalar(self):
        # cond=10, uncond=2, strength=1.0, s=1.0
        # out = 1.0*10 + 0.0*2 + 1.0*1.0 = 11.0
        result = compute_cfg_with_steering(10.0, 2.0, 1.0, "1.0")
        assert result == [11.0]

    def test_strength_zero(self):
        # strength=0: out = 0*cond + 1*uncond + 0*s = uncond
        result = compute_cfg_with_steering(10.0, 2.0, 0.0, "5.0")
        assert result == [2.0]

    def test_steering_zero(self):
        # s=0: out = strength*cond + (1-strength)*uncond
        result = compute_cfg_with_steering(10.0, 2.0, 0.5, "0.0")
        assert result == [6.0]

    def test_multi_dim_broadcast(self):
        # cond=[1,2], uncond=[3,4], strength=1.0, s=1.0 (broadcast)
        # out[0] = 1*1 + 0*3 + 1*1 = 2
        # out[1] = 1*2 + 0*4 + 1*1 = 3
        result = compute_cfg_with_steering("[1,2]", "[3,4]", 1.0, "1.0")
        assert result == [2.0, 3.0]

    def test_multi_dim_full_vector(self):
        # cond=[1,2], uncond=[3,4], strength=0.5, s=[10,20]
        # out[0] = 0.5*1 + 0.5*3 + 0.5*10 = 0.5+1.5+5 = 7.0
        # out[1] = 0.5*2 + 0.5*4 + 0.5*20 = 1+2+10 = 13.0
        result = compute_cfg_with_steering("[1,2]", "[3,4]", 0.5, "[10,20]")
        assert result == [7.0, 13.0]

    def test_negative_strength(self):
        # cond=10, uncond=2, strength=-1.0, s=1.0
        # out = -1*10 + 2*2 + (-1)*1 = -10+4-1 = -7
        result = compute_cfg_with_steering(10.0, 2.0, -1.0, "1.0")
        assert result == [-7.0]

    def test_dim_mismatch_raises(self):
        with pytest.raises(ValueError, match="dimension"):
            compute_cfg_with_steering("[1,2]", "[3,4]", 1.0, "[1,2,3]")

    def test_bad_steering_raises(self):
        with pytest.raises(ValueError):
            compute_cfg_with_steering(1.0, 2.0, 1.0, "not json")


class TestNodeRun:
    def test_scalar_run(self):
        node = PSN_CFG_Steering_Vector()
        out_json, out_scalar = node.run(
            cond=10.0, uncond=2.0, strength=1.0, steering_vector="1.0"
        )
        assert json.loads(out_json) == [11.0]
        assert out_scalar == 11.0

    def test_json_override(self):
        node = PSN_CFG_Steering_Vector()
        out_json, out_scalar = node.run(
            cond=0.0,
            uncond=0.0,
            strength=1.0,
            steering_vector="1.0",
            cond_json="[5,6]",
            uncond_json="[1,2]",
        )
        # out[0] = 1*5 + 0*1 + 1*1 = 6
        # out[1] = 1*6 + 0*2 + 1*1 = 7
        assert json.loads(out_json) == [6.0, 7.0]
        assert out_scalar == 6.0

    def test_bad_steering_raises(self):
        node = PSN_CFG_Steering_Vector()
        with pytest.raises(ValueError):
            node.run(cond=1.0, uncond=2.0, strength=1.0, steering_vector="bad")

    def test_bad_strength_raises(self):
        node = PSN_CFG_Steering_Vector()
        with pytest.raises(ValueError):
            node.run(cond=1.0, uncond=2.0, strength=float("nan"), steering_vector="1.0")

    def test_empty_cond_json_falls_back_to_scalar(self):
        node = PSN_CFG_Steering_Vector()
        out_json, out_scalar = node.run(
            cond=4.0,
            uncond=1.0,
            strength=1.0,
            steering_vector="0.0",
            cond_json="",
            uncond_json="",
        )
        # out = 1*4 + 0*1 + 0 = 4
        assert json.loads(out_json) == [4.0]
        assert out_scalar == 4.0
