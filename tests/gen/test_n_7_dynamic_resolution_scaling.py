"""Tests for PSN_Resolution_Scaler (pure-logic dynamic resolution scaling)."""

import math

from psn_nodes.gen.n_7_dynamic_resolution_scaling import (
    PSN_Resolution_Scaler,
    _compute_resolution,
    _validate_inputs,
)


def _run(aspect, mp, mw, mh, mult):
    node = PSN_Resolution_Scaler()
    return node.run(aspect, mp, mw, mh, mult)


def test_basic_16x9_preserves_ratio_and_multiple():
    width, height = _run(16.0 / 9.0, 1.0, 4096, 4096, 8)
    assert width % 8 == 0
    assert height % 8 == 0
    # Aspect ratio should be close to 16/9.
    assert abs((width / height) - (16.0 / 9.0)) < 0.05
    # Megapixels should be close to 1.0.
    assert abs((width * height) / 1e6 - 1.0) < 0.1


def test_clamping_to_max_width():
    # Very large target that would exceed max_width.
    width, height = _run(1.0, 100.0, 512, 512, 8)
    assert width <= 512
    assert height <= 512
    assert width % 8 == 0
    assert height % 8 == 0


def test_clamping_to_max_height():
    # Tall aspect ratio that would exceed max_height.
    width, height = _run(0.5, 100.0, 4096, 256, 8)
    assert height <= 256
    assert width <= 4096
    assert width % 8 == 0
    assert height % 8 == 0


def test_multiple_of_one():
    width, height = _run(2.0, 1.0, 4096, 4096, 1)
    assert width >= 1
    assert height >= 1
    assert abs((width / height) - 2.0) < 0.05


def test_bad_input_non_numeric_returns_safe_ints():
    width, height = _run("not_a_number", 1.0, 512, 512, 8)
    assert isinstance(width, int)
    assert isinstance(height, int)
    assert width >= 1
    assert height >= 1


def test_bad_input_negative_aspect_returns_safe_ints():
    width, height = _run(-1.0, 1.0, 512, 512, 8)
    assert isinstance(width, int)
    assert isinstance(height, int)
    assert width >= 1
    assert height >= 1


def test_bad_input_zero_megapixels_returns_safe_ints():
    width, height = _run(1.0, 0.0, 512, 512, 8)
    assert isinstance(width, int)
    assert isinstance(height, int)
    assert width >= 1
    assert height >= 1


def test_validate_inputs_rejects_non_finite():
    ok, reason, norm = _validate_inputs(float("inf"), 1.0, 512, 512, 8)
    assert ok is False
    assert norm is None


def test_validate_inputs_accepts_valid():
    ok, reason, norm = _validate_inputs(1.5, 2.0, 1024, 1024, 8)
    assert ok is True
    assert norm is not None
    aspect, mp, mw, mh, mult = norm
    assert aspect == 1.5
    assert mp == 2.0
    assert mw == 1024
    assert mh == 1024
    assert mult == 8


def test_compute_resolution_exact_square():
    width, height = _compute_resolution(1.0, 1.0, 4096, 4096, 8)
    assert width == height
    assert width % 8 == 0
    # 1 MP square is 1000x1000, rounded to multiple of 8 -> 1000.
    assert width == 1000
