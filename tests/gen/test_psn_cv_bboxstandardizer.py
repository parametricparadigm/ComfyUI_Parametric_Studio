"""Tests for PSN_CV_BBoxStandardizer."""

import json

import pytest

from psn_nodes.gen.psn_cv_bboxstandardizer import PSN_CV_BBoxStandardizer


def _node():
    return PSN_CV_BBoxStandardizer()


def test_xywh_to_xyxy_roundtrip():
    node = _node()
    bboxes = [[10, 20, 100, 50]]
    out, meta = node.run(bboxes, "xywh", "xyxy", 1000, 1000)
    assert out == [[10.0, 20.0, 110.0, 70.0]]
    # Convert back to xywh
    out2, _ = node.run(out, "xyxy", "xywh", 1000, 1000)
    assert out2 == [[10.0, 20.0, 100.0, 50.0]]


def test_center_to_xyxy_and_metadata():
    node = _node()
    # center (100, 100), w=50, h=20 -> x1=75, y1=90, x2=125, y2=110
    bboxes = [[100, 100, 50, 20]]
    out, meta = node.run(bboxes, "center", "xyxy", 1000, 1000)
    assert out == [[75.0, 90.0, 125.0, 110.0]]
    parsed = json.loads(meta)
    assert len(parsed) == 1
    assert parsed[0]["area"] == pytest.approx(50.0 * 20.0)
    assert parsed[0]["aspect_ratio"] == pytest.approx(50.0 / 20.0)
    assert parsed[0]["centroid"] == pytest.approx([100.0, 100.0])


def test_clamping_to_image_bounds():
    node = _node()
    # Box extends beyond image; should be clamped.
    bboxes = [[-10, -10, 50, 50]]  # xywh -> x1=-10, y1=-10, x2=40, y2=40
    out, _ = node.run(bboxes, "xywh", "xyxy", 100, 100)
    assert out == [[0.0, 0.0, 40.0, 40.0]]


def test_zero_height_aspect_ratio():
    node = _node()
    # Degenerate box with zero height.
    bboxes = [[10, 10, 20, 0]]  # xywh -> x1=10, y1=10, x2=30, y2=10
    out, meta = node.run(bboxes, "xywh", "xyxy", 100, 100)
    parsed = json.loads(meta)
    assert parsed[0]["area"] == pytest.approx(0.0)
    assert parsed[0]["aspect_ratio"] == 0.0


def test_empty_bboxes_list():
    node = _node()
    out, meta = node.run([], "xywh", "xyxy", 100, 100)
    assert out == []
    assert json.loads(meta) == []


def test_invalid_bbox_length_raises():
    node = _node()
    with pytest.raises(ValueError):
        node.run([[10, 20, 30]], "xywh", "xyxy", 100, 100)


def test_non_numeric_coordinate_raises():
    node = _node()
    with pytest.raises(ValueError):
        node.run([[10, "a", 30, 40]], "xywh", "xyxy", 100, 100)


def test_invalid_input_format_raises():
    node = _node()
    with pytest.raises(ValueError):
        node.run([[10, 20, 30, 40]], "bogus", "xyxy", 100, 100)


def test_invalid_output_format_raises():
    node = _node()
    with pytest.raises(ValueError):
        node.run([[10, 20, 30, 40]], "xywh", "bogus", 100, 100)


def test_non_positive_image_size_raises():
    node = _node()
    with pytest.raises(ValueError):
        node.run([[10, 20, 30, 40]], "xywh", "xyxy", 0, 100)


def test_bboxes_not_a_list_raises():
    node = _node()
    with pytest.raises(ValueError):
        node.run("not a list", "xywh", "xyxy", 100, 100)


def test_multiple_boxes_metadata_count():
    node = _node()
    bboxes = [[0, 0, 10, 10], [50, 50, 20, 20]]
    out, meta = node.run(bboxes, "xywh", "xyxy", 100, 100)
    assert len(out) == 2
    parsed = json.loads(meta)
    assert len(parsed) == 2
    assert parsed[0]["area"] == pytest.approx(100.0)
    assert parsed[1]["area"] == pytest.approx(400.0)
