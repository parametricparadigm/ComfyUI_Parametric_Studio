"""
Tests for PSN_Audio_Loader node.
"""

import json
import pytest
from psn_nodes.gen.psn_audio_loader import (
    PSN_Audio_Loader,
    _validate_file_path,
    _validate_sample_rate,
    _validate_channels,
    compute_duration,
)


class TestValidateFilePath:
    def test_valid_wav_path(self):
        ok, reason = _validate_file_path("/home/user/audio/test.wav")
        assert ok is True
        assert reason == "ok"

    def test_valid_mp3_path(self):
        ok, reason = _validate_file_path("C:\\Users\\test\\song.mp3")
        assert ok is True
        assert reason == "ok"

    def test_invalid_extension(self):
        ok, reason = _validate_file_path("/home/user/audio/test.txt")
        assert ok is False
        assert "not in allow-list" in reason

    def test_empty_path(self):
        ok, reason = _validate_file_path("")
        assert ok is False
        assert "must not be empty" in reason

    def test_non_string_path(self):
        ok, reason = _validate_file_path(12345)
        assert ok is False
        assert "must be a string" in reason

    def test_no_extension(self):
        ok, reason = _validate_file_path("/home/user/audio/testfile")
        assert ok is False
        assert "must have a file extension" in reason


class TestValidateSampleRate:
    def test_valid_sample_rate(self):
        ok, reason = _validate_sample_rate(44100)
        assert ok is True
        assert reason == "ok"

    def test_invalid_sample_rate(self):
        ok, reason = _validate_sample_rate(12345)
        assert ok is False
        assert "not in allowed set" in reason

    def test_zero_sample_rate(self):
        ok, reason = _validate_sample_rate(0)
        assert ok is False
        assert "must be positive" in reason

    def test_non_integer_sample_rate(self):
        ok, reason = _validate_sample_rate(44100.5)
        assert ok is False
        assert "must be an integer" in reason

    def test_bool_sample_rate(self):
        ok, reason = _validate_sample_rate(True)
        assert ok is False
        assert "must be an integer" in reason


class TestValidateChannels:
    def test_mono(self):
        ok, reason = _validate_channels(1)
        assert ok is True
        assert reason == "ok"

    def test_stereo(self):
        ok, reason = _validate_channels(2)
        assert ok is True
        assert reason == "ok"

    def test_invalid_channels(self):
        ok, reason = _validate_channels(3)
        assert ok is False
        assert "must be 1 (mono) or 2 (stereo)" in reason

    def test_zero_channels(self):
        ok, reason = _validate_channels(0)
        assert ok is False
        assert "must be 1 (mono) or 2 (stereo)" in reason

    def test_non_integer_channels(self):
        ok, reason = _validate_channels(1.5)
        assert ok is False
        assert "must be an integer" in reason


class TestComputeDuration:
    def test_basic_duration(self):
        # 1 second of 44100 Hz, mono, 16-bit: 44100 * 2 = 88200 bytes
        duration = compute_duration(88200, 44100, 1, 16)
        assert abs(duration - 1.0) < 1e-9

    def test_stereo_duration(self):
        # 1 second of 44100 Hz, stereo, 16-bit: 44100 * 2 * 2 = 176400 bytes
        duration = compute_duration(176400, 44100, 2, 16)
        assert abs(duration - 1.0) < 1e-9

    def test_zero_byte_count(self):
        duration = compute_duration(0, 44100, 1, 16)
        assert duration == 0.0

    def test_negative_byte_count(self):
        with pytest.raises(ValueError, match="byte_count must be non-negative"):
            compute_duration(-1, 44100, 1, 16)

    def test_invalid_bits_per_sample(self):
        with pytest.raises(ValueError, match="bits_per_sample must be 8, 16, 24, or 32"):
            compute_duration(88200, 44100, 1, 12)


class TestPSNAudioLoaderNode:
    def setup_method(self):
        self.node = PSN_Audio_Loader()

    def test_valid_inputs(self):
        payload, duration, valid, reason = self.node.run(
            file_path="/home/user/audio/test.wav",
            sample_rate=44100,
            channels=1,
            byte_count=88200,
            bits_per_sample=16,
        )
        assert valid is True
        assert reason == "ok"
        assert abs(duration - 1.0) < 1e-9
        data = json.loads(payload)
        assert data["file_path"] == "/home/user/audio/test.wav"
        assert data["sample_rate"] == 44100
        assert data["channels"] == 1
        assert data["format"] == "float32"
        assert data["normalized"] is True

    def test_invalid_file_extension(self):
        payload, duration, valid, reason = self.node.run(
            file_path="/home/user/audio/test.txt",
            sample_rate=44100,
            channels=1,
        )
        assert valid is False
        assert "not in allow-list" in reason
        assert payload == ""
        assert duration == 0.0

    def test_invalid_sample_rate(self):
        payload, duration, valid, reason = self.node.run(
            file_path="/home/user/audio/test.wav",
            sample_rate=12345,
            channels=1,
        )
        assert valid is False
        assert "not in allowed set" in reason

    def test_invalid_channels(self):
        payload, duration, valid, reason = self.node.run(
            file_path="/home/user/audio/test.wav",
            sample_rate=44100,
            channels=3,
        )
        assert valid is False
        assert "must be 1 (mono) or 2 (stereo)" in reason

    def test_no_byte_count(self):
        payload, duration, valid, reason = self.node.run(
            file_path="/home/user/audio/test.wav",
            sample_rate=44100,
            channels=2,
        )
        assert valid is True
        assert duration == 0.0
        data = json.loads(payload)
        assert data["estimated_duration"] == 0.0

    def test_stereo_with_byte_count(self):
        payload, duration, valid, reason = self.node.run(
            file_path="/home/user/audio/test.wav",
            sample_rate=48000,
            channels=2,
            byte_count=192000,  # 1 second: 48000 * 2 * 2
            bits_per_sample=16,
        )
        assert valid is True
        assert abs(duration - 1.0) < 1e-9
