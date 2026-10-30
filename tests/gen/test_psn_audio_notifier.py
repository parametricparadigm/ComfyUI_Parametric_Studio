"""
Tests for PSN_AudioNotifier node.

Tests cover:
- Valid WAV file with valid volume
- Valid MP3 file with valid volume
- Invalid file extension
- Empty sound_file
- Non-string sound_file
- Volume out of range (too low)
- Volume out of range (too high)
- Volume as boolean (should be rejected)
- Volume as non-numeric type
- Edge case: volume exactly 0.0 and 1.0
- Payload format correctness
"""

import json
import pytest
from psn_nodes.gen.psn_audio_notifier import PSN_AudioNotifier, _validate_sound_file, _validate_volume, _format_payload


class TestPSNAudioNotifier:
    """Test suite for PSN_AudioNotifier."""
    
    def setup_method(self):
        self.node = PSN_AudioNotifier()
    
    def test_valid_wav_file(self):
        """Valid WAV file with valid volume should return played=True."""
        played, payload, reason = self.node.run("notification.wav", 0.8)
        assert played is True
        assert reason == "ok"
        data = json.loads(payload)
        assert data["action"] == "play_audio"
        assert data["sound_file"] == "notification.wav"
        assert data["volume"] == 0.8
        assert data["non_blocking"] is True
    
    def test_valid_mp3_file(self):
        """Valid MP3 file with valid volume should return played=True."""
        played, payload, reason = self.node.run("alert.mp3", 0.5)
        assert played is True
        assert reason == "ok"
        data = json.loads(payload)
        assert data["sound_file"] == "alert.mp3"
        assert data["volume"] == 0.5
    
    def test_invalid_extension(self):
        """File with disallowed extension should return played=False."""
        played, payload, reason = self.node.run("sound.ogg", 0.5)
        assert played is False
        assert payload == ""
        assert "must end with" in reason
    
    def test_empty_sound_file(self):
        """Empty sound_file should return played=False."""
        played, payload, reason = self.node.run("", 0.5)
        assert played is False
        assert payload == ""
        assert "must not be empty" in reason
    
    def test_whitespace_only_sound_file(self):
        """Whitespace-only sound_file should return played=False."""
        played, payload, reason = self.node.run("   ", 0.5)
        assert played is False
        assert payload == ""
        assert "must not be empty" in reason
    
    def test_non_string_sound_file(self):
        """Non-string sound_file should return played=False."""
        played, payload, reason = self.node.run(12345, 0.5)
        assert played is False
        assert payload == ""
        assert "must be a string" in reason
    
    def test_volume_too_low(self):
        """Volume below 0.0 should return played=False."""
        played, payload, reason = self.node.run("alert.wav", -0.1)
        assert played is False
        assert payload == ""
        assert "between 0.0 and 1.0" in reason
    
    def test_volume_too_high(self):
        """Volume above 1.0 should return played=False."""
        played, payload, reason = self.node.run("alert.wav", 1.5)
        assert played is False
        assert payload == ""
        assert "between 0.0 and 1.0" in reason
    
    def test_volume_as_boolean(self):
        """Boolean volume should be rejected."""
        played, payload, reason = self.node.run("alert.wav", True)
        assert played is False
        assert payload == ""
        assert "not a boolean" in reason
    
    def test_volume_as_string(self):
        """String volume should be rejected."""
        played, payload, reason = self.node.run("alert.wav", "0.5")
        assert played is False
        assert payload == ""
        assert "must be a number" in reason
    
    def test_volume_zero(self):
        """Volume exactly 0.0 is valid."""
        played, payload, reason = self.node.run("alert.wav", 0.0)
        assert played is True
        assert reason == "ok"
        data = json.loads(payload)
        assert data["volume"] == 0.0
    
    def test_volume_one(self):
        """Volume exactly 1.0 is valid."""
        played, payload, reason = self.node.run("alert.wav", 1.0)
        assert played is True
        assert reason == "ok"
        data = json.loads(payload)
        assert data["volume"] == 1.0
    
    def test_payload_format(self):
        """Payload should be valid JSON with expected keys."""
        played, payload, reason = self.node.run("test.wav", 0.75)
        assert played is True
        data = json.loads(payload)
        assert set(data.keys()) == {"action", "sound_file", "volume", "non_blocking"}
        assert data["action"] == "play_audio"
        assert data["non_blocking"] is True
    
    def test_uppercase_extension(self):
        """Uppercase extension should be accepted (case-insensitive)."""
        played, payload, reason = self.node.run("ALERT.WAV", 0.5)
        assert played is True
        assert reason == "ok"
        data = json.loads(payload)
        assert data["sound_file"] == "ALERT.WAV"
    
    def test_path_with_directory(self):
        """File path with directory should be accepted if extension is valid."""
        played, payload, reason = self.node.run("/sounds/alerts/notification.mp3", 0.6)
        assert played is True
        assert reason == "ok"
        data = json.loads(payload)
        assert data["sound_file"] == "/sounds/alerts/notification.mp3"
    
    def test_validate_sound_file_helper(self):
        """Direct test of _validate_sound_file helper."""
        ok, reason = _validate_sound_file("test.wav")
        assert ok is True
        assert reason == "ok"
        
        ok, reason = _validate_sound_file("test.xyz")
        assert ok is False
        assert "must end with" in reason
    
    def test_validate_volume_helper(self):
        """Direct test of _validate_volume helper."""
        ok, reason = _validate_volume(0.5)
        assert ok is True
        assert reason == "ok"
        
        ok, reason = _validate_volume(1.5)
        assert ok is False
        assert "between 0.0 and 1.0" in reason
    
    def test_format_payload_helper(self):
        """Direct test of _format_payload helper."""
        payload = _format_payload("test.wav", 0.8)
        data = json.loads(payload)
        assert data["sound_file"] == "test.wav"
        assert data["volume"] == 0.8
