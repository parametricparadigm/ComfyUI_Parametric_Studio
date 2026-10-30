"""Tests for psn_nodes.gen.n_2_video_model_a_b_swipe_comparison."""

import pytest

from psn_nodes.gen.n_2_video_model_a_b_swipe_comparison import (
    PSN_Video_A_B_Loader,
    PSN_Video_Swipe_Preview,
    _psn_validate_video_descriptor,
    _psn_compute_split_column,
)


def _make_video(frame_count=10, width=512, height=512, channels=3, name="V"):
    return {"frame_count": frame_count, "width": width, "height": height, "channels": channels, "name": name}


def test_loader_valid_matching_videos():
    node = PSN_Video_A_B_Loader()
    pair, valid, msg = node.run(_make_video(name="A"), _make_video(name="B"))
    assert valid is True
    assert pair["video_a"]["name"] == "A"
    assert pair["video_b"]["name"] == "B"
    assert pair["frame_count"] == 10
    assert pair["width"] == 512
    assert pair["resized_b"] is False
    assert "no resize" in msg


def test_loader_resizes_when_resolution_differs():
    node = PSN_Video_A_B_Loader()
    pair, valid, msg = node.run(_make_video(width=512, height=512, name="A"), _make_video(width=256, height=256, name="B"))
    assert valid is True
    assert pair["resized_b"] is True
    assert "resized" in msg


def test_loader_rejects_frame_count_mismatch():
    node = PSN_Video_A_B_Loader()
    pair, valid, msg = node.run(_make_video(frame_count=10), _make_video(frame_count=12))
    assert valid is False
    assert "frame_count mismatch" in msg
    assert pair == {}


def test_loader_rejects_bad_descriptor():
    node = PSN_Video_A_B_Loader()
    pair, valid, msg = node.run("not a dict", _make_video())
    assert valid is False
    assert "must be a dict" in msg

    pair2, valid2, msg2 = node.run(_make_video(frame_count=0), _make_video())
    assert valid2 is False
    assert "frame_count" in msg2


def test_preview_valid_split_half():
    loader = PSN_Video_A_B_Loader()
    pair, valid, _ = loader.run(_make_video(name="A"), _make_video(name="B"))
    assert valid
    preview = PSN_Video_Swipe_Preview()
    layout, pvalid, msg = preview.run(pair, 0.5, 0)
    assert pvalid is True
    assert layout["frame_index"] == 0
    assert layout["split_column"] == 256
    assert layout["left_width"] == 256
    assert layout["right_width"] == 256
    assert layout["left_source"] == "A"
    assert layout["right_source"] == "B"
    assert layout["width"] == 512


def test_preview_split_edges():
    loader = PSN_Video_A_B_Loader()
    pair, valid, _ = loader.run(_make_video(), _make_video())
    assert valid
    preview = PSN_Video_Swipe_Preview()

    layout0, v0, _ = preview.run(pair, 0.0, 0)
    assert v0 and layout0["split_column"] == 0 and layout0["left_width"] == 0 and layout0["right_width"] == 512

    layout1, v1, _ = preview.run(pair, 1.0, 0)
    assert v1 and layout1["split_column"] == 512 and layout1["left_width"] == 512 and layout1["right_width"] == 0


def test_preview_rejects_bad_frame_index():
    loader = PSN_Video_A_B_Loader()
    pair, valid, _ = loader.run(_make_video(frame_count=10), _make_video(frame_count=10))
    assert valid
    preview = PSN_Video_Swipe_Preview()
    layout, pvalid, msg = preview.run(pair, 0.5, 10)
    assert pvalid is False
    assert "out of range" in msg

    layout2, pvalid2, _ = preview.run(pair, 0.5, -1)
    assert pvalid2 is False


def test_preview_rejects_bad_split_position():
    loader = PSN_Video_A_B_Loader()
    pair, valid, _ = loader.run(_make_video(), _make_video())
    assert valid
    preview = PSN_Video_Swipe_Preview()
    layout, pvalid, msg = preview.run(pair, 1.5, 0)
    assert pvalid is False
    assert "split_position" in msg

    layout2, pvalid2, _ = preview.run(pair, -0.1, 0)
    assert pvalid2 is False


def test_preview_rejects_empty_pair():
    preview = PSN_Video_Swipe_Preview()
    layout, pvalid, msg = preview.run({}, 0.5, 0)
    assert pvalid is False
    assert "non-empty" in msg

    layout2, pvalid2, _ = preview.run({"video_a": {}}, 0.5, 0)
    assert pvalid2 is False


def test_compute_split_column_clamps():
    assert _psn_compute_split_column(0.0, 100) == 0
    assert _psn_compute_split_column(1.0, 100) == 100
    assert _psn_compute_split_column(0.5, 100) == 50
    assert _psn_compute_split_column(0.5, 101) == 50
    assert _psn_compute_split_column(-0.5, 100) == 0
    assert _psn_compute_split_column(1.5, 100) == 100
    assert _psn_compute_split_column(0.5, 0) == 0


def test_validate_descriptor_bad_channels():
    ok, err, norm = _psn_validate_video_descriptor({"frame_count": 10, "width": 10, "height": 10, "channels": 0}, "v")
    assert not ok
    assert "channels" in err

    ok2, err2, norm2 = _psn_validate_video_descriptor({"frame_count": 10, "width": 10, "height": 10, "channels": True}, "v")
    assert not ok2
