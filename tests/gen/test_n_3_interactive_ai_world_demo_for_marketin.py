"""
Tests for PSN Matrix-Game Interactive World Demo (Pure Logic)
"""

import json
import pytest

from psn_nodes.gen.n_3_interactive_ai_world_demo_for_marketin import (
    PSN_MatrixGame_Load,
    PSN_MatrixGame_Generate,
    _validate_model_path,
    _validate_device,
    _validate_prompt,
    _validate_fps,
    _validate_mouse_icon,
    _compute_state_hash,
    _build_state_metadata,
    _build_video_metadata,
    ALLOWED_DEVICES,
    ALLOWED_MOUSE_ICONS,
    MIN_FPS,
    MAX_FPS,
    MAX_PROMPT_LENGTH,
)


class TestPSN_MatrixGame_Load:
    """Tests for PSN_MatrixGame_Load node."""

    def test_valid_load(self):
        """Test valid model path and device."""
        node = PSN_MatrixGame_Load()
        model, status = node.run("models/matrix_game_17b.safetensors", "cuda")
        assert model["loaded"] is True
        assert model["device"] == "cuda"
        assert model["param_count"] == 17_000_000_000
        assert status.startswith("OK")

    def test_invalid_device(self):
        """Test invalid device string."""
        node = PSN_MatrixGame_Load()
        model, status = node.run("models/matrix_game_17b.safetensors", "gpu")
        assert model["loaded"] is False
        assert "FAIL" in status
        assert "device" in status.lower()

    def test_empty_model_path(self):
        """Test empty model path."""
        node = PSN_MatrixGame_Load()
        model, status = node.run("", "cpu")
        assert model["loaded"] is False
        assert "FAIL" in status

    def test_path_traversal(self):
        """Test path traversal detection."""
        node = PSN_MatrixGame_Load()
        model, status = node.run("../etc/passwd", "cpu")
        assert model["loaded"] is False
        assert "traversal" in status.lower()

    def test_non_string_model_path(self):
        """Test non-string model path."""
        node = PSN_MatrixGame_Load()
        model, status = node.run(12345, "cpu")
        assert model["loaded"] is False
        assert "FAIL" in status


class TestPSN_MatrixGame_Generate:
    """Tests for PSN_MatrixGame_Generate node."""

    def _make_valid_model(self):
        return {
            "model_path": "models/matrix_game_17b.safetensors",
            "device": "cuda",
            "loaded": True,
            "param_count": 17_000_000_000,
            "status": "ready",
        }

    def test_valid_generation(self):
        """Test valid generation parameters."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        video, state = node.run(model, "A cyberpunk city at night", "crosshair", 30)
        assert video["generated"] is True
        assert video["fps"] == 30
        assert video["total_frames"] == 150  # 30 fps * 5 seconds
        state_data = json.loads(state)
        assert state_data["status"] == "generated"
        assert state_data["prompt"] == "A cyberpunk city at night"
        assert state_data["fps"] == 30
        assert state_data["mouse_icon"] == "crosshair"
        assert "state_hash" in state_data

    def test_invalid_model_not_loaded(self):
        """Test model not loaded."""
        node = PSN_MatrixGame_Generate()
        model = {"loaded": False}
        video, state = node.run(model, "test prompt", "default", 30)
        assert video["generated"] is False
        assert "FAIL" in state

    def test_invalid_model_type(self):
        """Test non-dict model."""
        node = PSN_MatrixGame_Generate()
        video, state = node.run("not a dict", "test prompt", "default", 30)
        assert video["generated"] is False
        assert "FAIL" in state

    def test_empty_prompt(self):
        """Test empty prompt."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        video, state = node.run(model, "", "default", 30)
        assert video["generated"] is False
        assert "FAIL" in state

    def test_prompt_too_long(self):
        """Test prompt exceeding max length."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        long_prompt = "a" * (MAX_PROMPT_LENGTH + 1)
        video, state = node.run(model, long_prompt, "default", 30)
        assert video["generated"] is False
        assert "FAIL" in state

    def test_invalid_fps_too_low(self):
        """Test fps below minimum."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        video, state = node.run(model, "test prompt", "default", 0)
        assert video["generated"] is False
        assert "FAIL" in state

    def test_invalid_fps_too_high(self):
        """Test fps above maximum."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        video, state = node.run(model, "test prompt", "default", MAX_FPS + 1)
        assert video["generated"] is False
        assert "FAIL" in state

    def test_invalid_mouse_icon(self):
        """Test invalid mouse icon."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        video, state = node.run(model, "test prompt", "invalid_icon", 30)
        assert video["generated"] is False
        assert "FAIL" in state

    def test_deterministic_state_hash(self):
        """Test that state hash is deterministic for same inputs."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        _, state1 = node.run(model, "test prompt", "default", 30)
        _, state2 = node.run(model, "test prompt", "default", 30)
        assert state1 == state2

    def test_different_inputs_different_hash(self):
        """Test that different inputs produce different hashes."""
        node = PSN_MatrixGame_Generate()
        model = self._make_valid_model()
        _, state1 = node.run(model, "prompt A", "default", 30)
        _, state2 = node.run(model, "prompt B", "default", 30)
        assert state1 != state2


class TestValidationHelpers:
    """Tests for validation helper functions."""

    def test_validate_model_path_valid(self):
        ok, reason = _validate_model_path("models/test.safetensors")
        assert ok is True
        assert reason == "ok"

    def test_validate_model_path_null_byte(self):
        ok, reason = _validate_model_path("models/test\x00.safetensors")
        assert ok is False
        assert "null" in reason.lower()

    def test_validate_device_valid(self):
        for dev in ALLOWED_DEVICES:
            ok, reason = _validate_device(dev)
            assert ok is True

    def test_validate_device_invalid(self):
        ok, reason = _validate_device("tpu")
        assert ok is False

    def test_validate_fps_boundary(self):
        ok, _ = _validate_fps(MIN_FPS)
        assert ok is True
        ok, _ = _validate_fps(MAX_FPS)
        assert ok is True
        ok, _ = _validate_fps(MIN_FPS - 1)
        assert ok is False
        ok, _ = _validate_fps(MAX_FPS + 1)
        assert ok is False

    def test_validate_fps_bool_rejected(self):
        """Test that bool is rejected even though it's a subclass of int."""
        ok, reason = _validate_fps(True)
        assert ok is False
        ok, reason = _validate_fps(False)
        assert ok is False

    def test_compute_state_hash_deterministic(self):
        h1 = _compute_state_hash("prompt", 30, "default")
        h2 = _compute_state_hash("prompt", 30, "default")
        assert h1 == h2
        assert len(h1) == 16

    def test_build_video_metadata(self):
        meta = _build_video_metadata(60)
        assert meta["fps"] == 60
        assert meta["total_frames"] == 300  # 60 * 5
        assert meta["width"] == 1280
        assert meta["height"] == 720
