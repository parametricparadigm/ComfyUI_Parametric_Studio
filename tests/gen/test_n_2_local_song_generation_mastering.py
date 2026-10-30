"""Tests for psn_nodes.gen.n_2_local_song_generation_mastering."""

import math

from psn_nodes.gen.n_2_local_song_generation_mastering import (
    PSN_Music_Generate,
    PSN_Music_Master,
    _linear_to_db,
    _db_to_linear,
    _compute_peak_db,
    _list_to_frames,
)


def _sine_frames(freq=440.0, duration=1.0, sample_rate=44100, amplitude=0.5):
    """Build a deterministic stereo sine wave as list-of-[left, right]."""
    frames = []
    n = int(duration * sample_rate)
    for i in range(n):
        t = i / sample_rate
        v = amplitude * math.sin(2.0 * math.pi * freq * t)
        frames.append([v, v])
    return frames


def test_generate_valid_returns_plan():
    node = PSN_Music_Generate()
    raw, plan, valid = node.run("a calm piano piece", 30, 12345, "yue2")
    assert valid is True
    assert raw == plan
    assert "yue2" in plan
    assert "a calm piano piece" in plan
    assert "12345" in plan


def test_generate_rejects_bad_model():
    node = PSN_Music_Generate()
    raw, plan, valid = node.run("test", 30, 0, "not_a_real_model")
    assert valid is False
    assert raw == ""
    assert plan == ""


def test_generate_rejects_empty_prompt():
    node = PSN_Music_Generate()
    raw, plan, valid = node.run("", 30, 0, "yue2")
    assert valid is False


def test_generate_rejects_bad_duration():
    node = PSN_Music_Generate()
    raw, plan, valid = node.run("test", 0, 0, "yue2")
    assert valid is False
    raw, plan, valid = node.run("test", 99999, 0, "yue2")
    assert valid is False


def test_master_sine_peak_below_zero():
    """Master a known sine wave; peak must be below 0 dB."""
    frames = _sine_frames(freq=440.0, duration=1.0, amplitude=0.5)
    node = PSN_Music_Master()
    mastered, peak_db = node.run(frames, -14.0, "flat")
    assert isinstance(mastered, list)
    assert len(mastered) == len(frames)
    # Peak must be below 0 dB (limiting guarantees this).
    assert peak_db < 0.0
    # For a sine wave normalized to -14 dB RMS, peak is ~ -14 + 3.01 = -11 dB.
    # It should be well below the limiter ceiling (-0.5 dB).
    assert peak_db < -1.0


def test_master_loudness_near_target():
    """RMS-based loudness estimate should be near the target after mastering."""
    frames = _sine_frames(freq=440.0, duration=1.0, amplitude=0.5)
    node = PSN_Music_Master()
    mastered, peak_db = node.run(frames, -14.0, "flat")
    # Compute RMS of the mastered output.
    total = 0.0
    count = 0
    for l, r in mastered:
        total += l * l + r * r
        count += 2
    rms = math.sqrt(total / count)
    rms_db = _linear_to_db(rms)
    # For a sine wave, RMS = amplitude / sqrt(2).  After normalization to
    # -14 dB RMS, the measured RMS should be close to -14 dB.
    assert abs(rms_db - (-14.0)) < 1.0


def test_master_bad_audio_input():
    """Bad audio payload returns empty audio and floor peak."""
    node = PSN_Music_Master()
    mastered, peak_db = node.run("not a list", -14.0, "flat")
    assert mastered == []
    assert peak_db == -120.0


def test_master_bad_frame_shape():
    """A frame with wrong length is rejected."""
    node = PSN_Music_Master()
    bad = [[0.1, 0.2, 0.3]]  # 3 elements instead of 2
    mastered, peak_db = node.run(bad, -14.0, "flat")
    assert mastered == []
    assert peak_db == -120.0


def test_master_bad_eq_preset():
    """An unknown EQ preset is rejected."""
    frames = _sine_frames(duration=0.1, amplitude=0.3)
    node = PSN_Music_Master()
    mastered, peak_db = node.run(frames, -14.0, "nonexistent_preset")
    assert mastered == []
    assert peak_db == -120.0


def test_master_empty_audio():
    """Empty audio list returns empty output and floor peak."""
    node = PSN_Music_Master()
    mastered, peak_db = node.run([], -14.0, "flat")
    assert mastered == []
    assert peak_db == -120.0


def test_db_roundtrip():
    """dB <-> linear conversion round-trips."""
    for db in (-60.0, -20.0, -10.0, -3.0, 0.0):
        lin = _db_to_linear(db)
        back = _linear_to_db(lin)
        assert abs(back - db) < 1e-6


def test_compute_peak_db_known():
    """Peak dB of a known frame set is correct."""
    frames = [(0.5, -0.5), (0.25, 0.25)]
    peak = _compute_peak_db(frames)
    expected = _linear_to_db(0.5)
    assert abs(peak - expected) < 1e-6


def test_list_to_frames_rejects_bool():
    """Booleans are not accepted as sample values."""
    frames, ok, reason = _list_to_frames([[True, 0.5]])
    assert ok is False
    assert "booleans" in reason
