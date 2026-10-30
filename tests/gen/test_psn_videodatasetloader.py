"""Tests for PSN_VideoDatasetLoader pure-logic planning and validation."""

import pytest

from psn_nodes.gen.psn_videodatasetloader import (
    PSN_VideoDatasetLoader,
    VideoInfo,
    _validate_range,
    _build_chunk_plan,
    _redact_path,
    _compute_duration,
    RESIZE_MODES,
)


def test_basic_valid_range_single_chunk():
    node = PSN_VideoDatasetLoader()
    info, chunk_str, reason = node.run(
        file_path="/videos/test.mp4",
        start_frame=0,
        end_frame=9,
        resize_mode="none",
        target_width=512,
        target_height=512,
        fps=30.0,
        total_frames=10,
        codec="h264",
    )
    assert reason == "ok"
    assert isinstance(info, VideoInfo)
    assert info.fps == 30.0
    assert info.total_frames == 10
    assert info.codec == "h264"
    assert chunk_str == "[[0,9]]"


def test_chunked_plan_for_long_range():
    node = PSN_VideoDatasetLoader()
    info, chunk_str, reason = node.run(
        file_path="video.avi",
        start_frame=0,
        end_frame=250,
        resize_mode="pad",
        target_width=640,
        target_height=480,
        fps=24.0,
        total_frames=300,
        codec="mpeg4",
    )
    assert reason == "ok"
    # 251 frames -> chunks of 100: [0,99],[100,199],[200,250]
    assert chunk_str == "[[0,99],[100,199],[200,250]]"
    assert info.duration == pytest.approx(300 / 24.0)


def test_end_frame_clamped_to_total_frames():
    node = PSN_VideoDatasetLoader()
    info, chunk_str, reason = node.run(
        file_path="clip.mov",
        start_frame=0,
        end_frame=999,
        resize_mode="center_crop",
        target_width=256,
        target_height=256,
        fps=15.0,
        total_frames=50,
        codec="prores",
    )
    assert reason == "ok"
    # end clamped to 49
    assert chunk_str == "[[0,49]]"


def test_start_beyond_total_frames():
    node = PSN_VideoDatasetLoader()
    info, chunk_str, reason = node.run(
        file_path="short.mp4",
        start_frame=100,
        end_frame=200,
        resize_mode="none",
        target_width=128,
        target_height=128,
        fps=10.0,
        total_frames=50,
        codec="h264",
    )
    assert reason == "start_frame beyond total_frames"
    assert chunk_str == "[]"


def test_invalid_resize_mode():
    node = PSN_VideoDatasetLoader()
    info, chunk_str, reason = node.run(
        file_path="x.mp4",
        start_frame=0,
        end_frame=10,
        resize_mode="invalid_mode",
        target_width=100,
        target_height=100,
        fps=30.0,
        total_frames=20,
        codec="h264",
    )
    assert "invalid resize_mode" in reason
    assert chunk_str == "[]"


def test_end_less_than_start():
    node = PSN_VideoDatasetLoader()
    info, chunk_str, reason = node.run(
        file_path="y.mp4",
        start_frame=10,
        end_frame=5,
        resize_mode="none",
        target_width=100,
        target_height=100,
        fps=30.0,
        total_frames=100,
        codec="h264",
    )
    assert "end_frame must be >= start_frame" in reason
    assert chunk_str == "[]"


def test_redact_path_keeps_basename():
    assert _redact_path("/home/user/videos/clip.mp4") == "clip.mp4"
    assert _redact_path("C:\\Users\\me\\vid.avi") == "vid.avi"
    assert _redact_path("") == ""
    assert _redact_path(None) == ""


def test_compute_duration_edge_cases():
    assert _compute_duration(0.0, 100) == 0.0
    assert _compute_duration(30.0, 0) == 0.0
    assert _compute_duration(30.0, 60) == pytest.approx(2.0)


def test_validate_range_negative_start_clamped():
    start, end, reason = _validate_range(-5, 10, 100)
    assert start == 0
    assert end == 10
    assert reason == "ok"


def test_chunk_plan_empty_when_end_less_than_start():
    assert _build_chunk_plan(10, 5) == []


def test_chunk_plan_exact_threshold():
    # Exactly 100 frames -> single chunk
    chunks = _build_chunk_plan(0, 99)
    assert chunks == [(0, 99)]


def test_chunk_plan_just_over_threshold():
    # 101 frames -> two chunks
    chunks = _build_chunk_plan(0, 100)
    assert chunks == [(0, 99), (100, 100)]
