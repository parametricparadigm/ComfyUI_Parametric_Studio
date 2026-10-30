"""Tests for PSN_AspectRatioEnforcer (pure-logic aspect-ratio planning)."""

import json

import pytest

from psn_nodes.gen.psn_aspect_ratio_enforcer import (
    PSN_AspectRatioEnforcer,
    _psn_compute_plan,
    _psn_validate_positive_int,
    _psn_validate_ratio,
)


def test_psn_crop_wide_to_square():
    # Input 1024x512 (ratio 2.0), target 1.0, crop -> should crop width to 512
    plan = _psn_compute_plan(1024, 512, 1.0, "crop")
    assert plan["out_width"] == 512
    assert plan["out_height"] == 512
    assert plan["crop_w"] == 512
    assert plan["crop_h"] == 512
    assert plan["crop_x"] == (1024 - 512) // 2
    assert plan["crop_y"] == 0


def test_psn_pad_tall_to_wide():
    # Input 512x1024 (ratio 0.5), target 2.0, pad -> should pad width
    plan = _psn_compute_plan(512, 1024, 2.0, "pad")
    assert plan["out_height"] == 1024
    assert plan["out_width"] == 2048
    assert plan["pad_top"] == 0
    assert plan["pad_bottom"] == 0
    assert plan["pad_left"] + plan["pad_right"] == 2048 - 512


def test_psn_resize_keeps_dims():
    # Resize mode keeps input dims (distortion applied by host)
    plan = _psn_compute_plan(800, 600, 16.0 / 9.0, "resize")
    assert plan["out_width"] == 800
    assert plan["out_height"] == 600
    assert plan["resize_from_w"] == 800
    assert plan["resize_from_h"] == 600


def test_psn_node_run_returns_json_plan():
    node = PSN_AspectRatioEnforcer()
    out_w, out_h, plan_json = node.run(width=1000, height=500, target_ratio=1.0, mode="crop")
    assert out_w == 500
    assert out_h == 500
    plan = json.loads(plan_json)
    assert plan["mode"] == "crop"
    assert plan["out_width"] == 500
    assert plan["out_height"] == 500


def test_psn_invalid_mode_raises():
    with pytest.raises(ValueError):
        _psn_compute_plan(512, 512, 1.0, "stretch")


def test_psn_invalid_ratio_zero_raises():
    with pytest.raises(ValueError):
        _psn_compute_plan(512, 512, 0.0, "crop")


def test_psn_invalid_ratio_negative_raises():
    with pytest.raises(ValueError):
        _psn_validate_ratio(-1.5)


def test_psn_invalid_width_zero_raises():
    with pytest.raises(ValueError):
        _psn_validate_positive_int(0, "width")


def test_psn_invalid_width_bool_raises():
    with pytest.raises(ValueError):
        _psn_validate_positive_int(True, "width")


def test_psn_crop_already_matching_ratio():
    # Input 512x512, target 1.0, crop -> no change
    plan = _psn_compute_plan(512, 512, 1.0, "crop")
    assert plan["out_width"] == 512
    assert plan["out_height"] == 512
    assert plan["crop_x"] == 0
    assert plan["crop_y"] == 0


def test_psn_pad_already_matching_ratio():
    # Input 512x512, target 1.0, pad -> no padding
    plan = _psn_compute_plan(512, 512, 1.0, "pad")
    assert plan["pad_left"] == 0
    assert plan["pad_right"] == 0
    assert plan["pad_top"] == 0
    assert plan["pad_bottom"] == 0


def test_psn_float_width_integer_valued_ok():
    # Integer-valued float should be accepted
    plan = _psn_compute_plan(512.0, 512.0, 1.0, "crop")
    assert plan["out_width"] == 512
    assert plan["out_height"] == 512


def test_psn_float_width_non_integer_raises():
    with pytest.raises(ValueError):
        _psn_validate_positive_int(512.5, "width")


def test_psn_ratio_infinity_raises():
    with pytest.raises(ValueError):
        _psn_validate_ratio(float("inf"))


def test_psn_ratio_nan_raises():
    with pytest.raises(ValueError):
        _psn_validate_ratio(float("nan"))
