"""Tests for PSN_CV_LightingCorrector."""

import json
import math

import pytest

from psn_nodes.gen.psn_cv_lightingcorrector import (
    PSN_CV_LightingCorrector,
    _parse_image_json,
    _estimate_light_from_normals,
    _estimate_light_from_intrinsic,
    _direction_label,
    _estimate_kelvin,
    _white_balance_factors,
    _apply_correction,
)


def _make_image(rows):
    return json.dumps(rows)


def test_parse_image_json_valid():
    img = [[ [1.0, 0.5, 0.0], [0.0, 1.0, 0.5] ],
           [ [0.5, 0.5, 0.5], [0.1, 0.2, 0.3] ]]
    rows, h, w = _parse_image_json(img)
    assert h == 2
    assert w == 2
    assert rows[0][0] == [1.0, 0.5, 0.0]


def test_parse_image_json_invalid():
    with pytest.raises(ValueError):
        _parse_image_json("not json")
    with pytest.raises(ValueError):
        _parse_image_json("[]")
    with pytest.raises(ValueError):
        _parse_image_json("[[1,2,3],[1,2]]")  # ragged rows


def test_estimate_light_from_normals_top_left():
    # Normal map where normals point toward top-left (x negative, y negative).
    # In our encoding, x = r*2-1, y = g*2-1. Top-left light means normals
    # point toward top-left (x negative, y negative).
    # So normal map pixel should have r < 0.5 (x negative) and g < 0.5 (y negative).
    normal = [[ [0.2, 0.2, 1.0], [0.2, 0.2, 1.0] ],
              [ [0.2, 0.2, 1.0], [0.2, 0.2, 1.0] ]]
    rows, h, w = _parse_image_json(normal)
    lx, ly, lz = _estimate_light_from_normals(rows, h, w)
    # Light direction vector should point toward top-left: lx negative, ly negative.
    assert lx < 0
    assert ly < 0
    label = _direction_label(lx, ly, lz)
    assert label == "Top-Left"


def test_estimate_light_from_intrinsic_center():
    # Uniform image: no gradients, light should be center.
    img = [[ [0.5, 0.5, 0.5], [0.5, 0.5, 0.5] ],
           [ [0.5, 0.5, 0.5], [0.5, 0.5, 0.5] ]]
    rows, h, w = _parse_image_json(img)
    lx, ly, lz = _estimate_light_from_intrinsic(rows, h, w)
    label = _direction_label(lx, ly, lz)
    assert label == "Center"


def test_estimate_kelvin_warm_image():
    # Warm image: R > B.
    img = [[ [0.8, 0.6, 0.2], [0.7, 0.5, 0.3] ]]
    rows, h, w = _parse_image_json(img)
    kelvin = _estimate_kelvin(rows, h, w)
    # Warm means lower Kelvin than 5500.
    assert kelvin < 5500


def test_estimate_kelvin_cool_image():
    # Cool image: B > R.
    img = [[ [0.2, 0.5, 0.8], [0.3, 0.6, 0.7] ]]
    rows, h, w = _parse_image_json(img)
    kelvin = _estimate_kelvin(rows, h, w)
    # Cool means higher Kelvin than 5500.
    assert kelvin > 5500


def test_white_balance_factors_neutral():
    r, g, b = _white_balance_factors(5500, 5500)
    assert r == pytest.approx(1.0)
    assert g == pytest.approx(1.0)
    assert b == pytest.approx(1.0)


def test_white_balance_factors_warm_to_neutral():
    # Current is warm (low K), target is neutral (5500). Should boost blue.
    r, g, b = _white_balance_factors(4000, 5500)
    assert r < 1.0  # reduce red
    assert b > 1.0  # boost blue


def test_apply_correction_clamps_values():
    rows = [[ [1.0, 1.0, 1.0] ]]
    corrected = _apply_correction(rows, 2.0, 2.0, 2.0, 0.5, 1.0)
    # Values should be clamped to 1.0.
    assert corrected[0][0] == [1.0, 1.0, 1.0]


def test_run_basic_with_normal_map():
    node = PSN_CV_LightingCorrector()
    # Simple 2x2 image, warm.
    img = _make_image([[ [0.8, 0.6, 0.2], [0.7, 0.5, 0.3] ],
                       [ [0.6, 0.4, 0.1], [0.5, 0.3, 0.2] ]])
    # Normal map pointing top-left.
    normal = _make_image([[ [0.2, 0.2, 1.0], [0.2, 0.2, 1.0] ],
                          [ [0.2, 0.2, 1.0], [0.2, 0.2, 1.0] ]])
    corrected, light_dir, exposure_delta = node.run(img, 0.5, 5500, normal)
    assert light_dir == "Top-Left"
    assert isinstance(corrected, str)
    assert isinstance(exposure_delta, float)
    # Verify corrected image is valid JSON.
    rows = json.loads(corrected)
    assert len(rows) == 2
    assert len(rows[0]) == 2


def test_run_without_normal_map():
    node = PSN_CV_LightingCorrector()
    img = _make_image([[ [0.5, 0.5, 0.5], [0.6, 0.6, 0.6] ],
                       [ [0.4, 0.4, 0.4], [0.5, 0.5, 0.5] ]])
    corrected, light_dir, exposure_delta = node.run(img, 0.5, 5500)
    assert light_dir in ["Top-Left", "Top", "Top-Right", "Left", "Center", "Right", "Bottom-Left", "Bottom", "Bottom-Right"]
    assert isinstance(corrected, str)


def test_run_bad_correction_strength():
    node = PSN_CV_LightingCorrector()
    img = _make_image([[ [0.5, 0.5, 0.5] ]])
    with pytest.raises(ValueError):
        node.run(img, 1.5, 5500)


def test_run_bad_target_kelvin():
    node = PSN_CV_LightingCorrector()
    img = _make_image([[ [0.5, 0.5, 0.5] ]])
    with pytest.raises(ValueError):
        node.run(img, 0.5, 500)


def test_run_normal_map_dimension_mismatch():
    node = PSN_CV_LightingCorrector()
    img = _make_image([[ [0.5, 0.5, 0.5], [0.5, 0.5, 0.5] ]])
    normal = _make_image([[ [0.5, 0.5, 0.5] ]])  # 1x1 vs 1x2
    with pytest.raises(ValueError):
        node.run(img, 0.5, 5500, normal)


def test_run_invalid_image_json():
    node = PSN_CV_LightingCorrector()
    with pytest.raises(ValueError):
        node.run("not valid json", 0.5, 5500)
