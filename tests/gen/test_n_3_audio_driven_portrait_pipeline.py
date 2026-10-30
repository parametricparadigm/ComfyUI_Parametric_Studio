"""Tests for the pure-logic Audio-Driven Portrait Pipeline nodes."""

import json
import math

import pytest

from psn_nodes.gen.n_3_audio_driven_portrait_pipeline import (
    PSN_AudioToMouthTrack,
    PSN_MouthComposite,
    _parse_waveform,
    _mouth_openness,
    _frame_count,
)


def _node_track():
    return PSN_AudioToMouthTrack()


def _node_comp():
    return PSN_MouthComposite()


def test_mouth_track_peak_amplitude_yields_widest_mouth():
    """A frame containing the waveform peak must have the largest openness."""
    node = _node_track()
    # 24 fps, 24 samples -> 1 sample per frame.  Peak at index 12.
    amps = [0.1] * 12 + [1.0] + [0.1] * 11
    audio = json.dumps(amps)
    mouth_track, timing = node.run(audio, "neutral", 24)
    openness = json.loads(mouth_track)
    assert len(openness) == 24
    assert len(timing) == 24
    # The peak frame (index 12) must be the maximum and clearly larger.
    assert openness[12] == max(openness)
    assert openness[12] > openness[0]
    # Timing is monotonically increasing by 1/fps.
    assert math.isclose(timing[1] - timing[0], 1.0 / 24.0, abs_tol=1e-6)


def test_mouth_track_empty_audio_raises():
    node = _node_track()
    with pytest.raises(ValueError):
        node.run("[]", "neutral", 24)


def test_mouth_track_malformed_json_raises():
    node = _node_track()
    with pytest.raises(ValueError):
        node.run("[0.1, 0.2", "neutral", 24)  # unterminated array


def test_mouth_track_non_numeric_sample_raises():
    node = _node_track()
    with pytest.raises(ValueError):
        node.run("[0.1, 'oops', 0.2]", "neutral", 24)


def test_mouth_track_bad_fps_raises():
    node = _node_track()
    with pytest.raises(ValueError):
        node.run("[0.1, 0.2]", "neutral", 0)  # fps below min


def test_mouth_track_bad_sample_rate_raises():
    node = _node_track()
    with pytest.raises(ValueError):
        node.run("[0.1, 0.2]", "neutral", 24, sample_rate=12345)


def test_mouth_track_missing_face_raises():
    node = _node_track()
    with pytest.raises(ValueError):
        node.run("[0.1, 0.2]", "", 24)


def test_composite_matching_frames_returns_weights():
    node = _node_comp()
    base = json.dumps(["f0", "f1", "f2"])
    track = json.dumps([0.2, 0.5, 0.8])
    mask = json.dumps([1.0, 0.5, 0.0])
    video, weights = node.run(base, track, mask)
    assert weights == [1.0, 0.5, 0.0]
    assert json.loads(video) == [1.0, 0.5, 0.0]


def test_composite_frame_count_mismatch_raises():
    node = _node_comp()
    base = json.dumps(["f0", "f1"])
    track = json.dumps([0.2, 0.5, 0.8])  # 3 frames vs 2
    mask = json.dumps([1.0, 0.5])
    with pytest.raises(ValueError):
        node.run(base, track, mask)


def test_composite_mask_mismatch_raises():
    node = _node_comp()
    base = json.dumps(["f0", "f1"])
    track = json.dumps([0.2, 0.5])
    mask = json.dumps([1.0])  # 1 frame vs 2
    with pytest.raises(ValueError):
        node.run(base, track, mask)


def test_composite_bad_blend_mode_raises():
    node = _node_comp()
    base = json.dumps(["f0"])
    track = json.dumps([0.2])
    mask = json.dumps([1.0])
    with pytest.raises(ValueError):
        node.run(base, track, mask, blend_mode="screen")


def test_composite_mask_clamped_to_unit_range():
    node = _node_comp()
    base = json.dumps(["f0", "f1"])
    track = json.dumps([0.2, 0.5])
    mask = json.dumps([1.5, -0.5])  # out of range -> clamped
    _, weights = node.run(base, track, mask)
    assert weights == [1.0, 0.0]


def test_composite_empty_base_raises():
    node = _node_comp()
    with pytest.raises(ValueError):
        node.run("[]", "[]", "[]")


def test_parse_waveform_comma_string():
    amps = _parse_waveform("0.1, -0.2, 0.3")
    assert amps == [0.1, -0.2, 0.3]


def test_parse_waveform_clamps_amplitude():
    amps = _parse_waveform("[5.0, -5.0]")
    assert amps == [1.0, -1.0]


def test_mouth_openness_empty_returns_empty():
    assert _mouth_openness([], 24) == []


def test_frame_count_json_string():
    assert _frame_count("[1, 2, 3]") == 3


def test_frame_count_bad_json_raises():
    with pytest.raises(ValueError):
        _frame_count("[1, 2")
