"""Tests for PSN_Stereo_Converter (pure-logic stereo conversion planner)."""

import json

from psn_nodes.gen.n_8_stereo_3d_video_conversion import (
    PSN_Stereo_Converter,
    compute_output_shape,
    _parse_tensor_desc,
    _validate_depth_range,
)


def _run(video, depth, parallax=0.0, fmt="side_by_side", dmin=0.0, dmax=1.0):
    return PSN_Stereo_Converter().run(
        video_desc=video, depth_desc=depth, parallax=parallax,
        format=fmt, depth_min=dmin, depth_max=dmax,
    )


def test_side_by_side_doubles_width():
    valid, shape, reason, plan = _run("[10, 4, 6, 3]", "[10, 4, 6, 1]", fmt="side_by_side")
    assert valid is True
    assert shape == "(10, 4, 12, 3)"
    assert json.loads(plan)["output_shape"] == [10, 4, 12, 3]


def test_top_bottom_doubles_height():
    valid, shape, _, _ = _run("[3, 5, 7, 3]", "[3, 5, 7, 1]", fmt="top_bottom")
    assert valid is True
    assert shape == "(3, 10, 7, 3)"


def test_anaglyph_keeps_shape():
    valid, shape, _, _ = _run("[2, 8, 8, 3]", "[2, 8, 8, 1]", fmt="anaglyph")
    assert valid is True
    assert shape == "(2, 8, 8, 3)"


def test_depth_mismatch_rejected():
    valid, _, reason, _ = _run("[4, 4, 4, 3]", "[4, 4, 5, 1]")
    assert valid is False
    assert "match" in reason


def test_bad_format_rejected():
    valid, _, reason, _ = _run("[1, 2, 2, 3]", "[1, 2, 2, 1]", fmt="red_blue")
    assert valid is False
    assert "allow-list" in reason


def test_depth_out_of_range_rejected():
    valid, _, reason, _ = _run("[1, 2, 2, 3]", "[1, 2, 2, 1]", dmin=0.0, dmax=1.5)
    assert valid is False
    assert "[0,1]" in reason


def test_invalid_json_rejected():
    valid, _, reason, _ = _run("not json", "[1, 2, 2, 1]")
    assert valid is False
    assert "JSON" in reason


def test_wrong_channel_count_rejected():
    valid, _, reason, _ = _run("[1, 2, 2, 5]", "[1, 2, 2, 1]")
    assert valid is False
    assert "C in [1,4]" in reason


def test_non_integer_dim_rejected():
    valid, _, reason, _ = _run("[1.5, 2, 2, 3]", "[1, 2, 2, 1]")
    assert valid is False
    assert "integer" in reason


def test_compute_output_shape_unknown_raises():
    try:
        compute_output_shape(1, 2, 2, "bogus")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_parse_desc_object_form():
    dims, why = _parse_tensor_desc('{"T": 2, "H": 3, "W": 4, "C": 3}', "VIDEO")
    assert why is None
    assert dims == (2, 3, 4, 3)


def test_depth_range_min_gt_max_rejected():
    ok, why = _validate_depth_range(0.5, 0.2)
    assert ok is False
    assert "min exceeds max" in why
