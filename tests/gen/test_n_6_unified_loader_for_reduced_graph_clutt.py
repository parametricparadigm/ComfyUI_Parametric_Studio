"""
Tests for PSN_Unified_Model_VAE_Loader.
"""

import json
import pytest
from psn_nodes.gen.n_6_unified_loader_for_reduced_graph_clutt import (
    PSN_Unified_Model_VAE_Loader,
    _normalize_dtype,
    _validate_path,
)


class TestPSNUnifiedModelVAELoader:
    """Tests for the unified model/VAE loader validation node."""

    def setup_method(self):
        self.node = PSN_Unified_Model_VAE_Loader()

    def test_valid_paths_and_dtype(self):
        """Test with valid model and VAE paths and valid dtype."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/unet.safetensors",
            vae_path="/models/vae.safetensors",
            dtype="fp16",
        )
        assert valid is True
        assert reason == "ok"
        payload = json.loads(payload_str)
        assert payload["model_path"] == "/models/unet.safetensors"
        assert payload["vae_path"] == "/models/vae.safetensors"
        assert payload["dtype"] == "fp16"
        assert payload["node_type"] == "PSN_Unified_Model_VAE_Loader"

    def test_invalid_dtype(self):
        """Test with an invalid dtype string."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/unet.safetensors",
            vae_path="/models/vae.safetensors",
            dtype="fp64",  # Not in allowed list
        )
        assert valid is False
        assert "Invalid dtype" in reason

    def test_dtype_alias_normalization(self):
        """Test that dtype aliases are normalized correctly."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/unet.safetensors",
            vae_path="/models/vae.safetensors",
            dtype="float16",
        )
        assert valid is True
        payload = json.loads(payload_str)
        assert payload["dtype"] == "fp16"

    def test_path_traversal_rejected(self):
        """Test that path traversal attempts are rejected."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/../etc/passwd",
            vae_path="/models/vae.safetensors",
            dtype="fp16",
        )
        assert valid is False
        assert "path traversal" in reason.lower()

    def test_disallowed_extension(self):
        """Test that disallowed file extensions are rejected."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/unet.exe",
            vae_path="/models/vae.safetensors",
            dtype="fp16",
        )
        assert valid is False
        assert "Extension not allowed" in reason

    def test_allowed_dirs_restriction(self):
        """Test that paths outside allowed directories are rejected."""
        payload_str, valid, reason = self.node.run(
            model_path="/other/unet.safetensors",
            vae_path="/models/vae.safetensors",
            dtype="fp16",
            allowed_dirs="/models",
        )
        assert valid is False
        assert "not in allowed directories" in reason.lower()

    def test_empty_model_path(self):
        """Test that empty model path is rejected."""
        payload_str, valid, reason = self.node.run(
            model_path="",
            vae_path="/models/vae.safetensors",
            dtype="fp16",
        )
        assert valid is False
        assert "non-empty string" in reason

    def test_empty_vae_path(self):
        """Test that empty VAE path is rejected."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/unet.safetensors",
            vae_path="",
            dtype="fp16",
        )
        assert valid is False
        assert "non-empty string" in reason

    def test_custom_allowed_extensions(self):
        """Test with custom allowed extensions."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/unet.ckpt",
            vae_path="/models/vae.ckpt",
            dtype="fp32",
            allowed_extensions=".ckpt",
        )
        assert valid is True
        payload = json.loads(payload_str)
        assert payload["dtype"] == "fp32"

    def test_bf16_dtype(self):
        """Test that bf16 dtype is accepted and normalized."""
        payload_str, valid, reason = self.node.run(
            model_path="/models/unet.safetensors",
            vae_path="/models/vae.safetensors",
            dtype="bf16",
        )
        assert valid is True
        payload = json.loads(payload_str)
        assert payload["dtype"] == "bf16"

    def test_whitespace_in_paths(self):
        """Test that whitespace in paths is stripped."""
        payload_str, valid, reason = self.node.run(
            model_path="  /models/unet.safetensors  ",
            vae_path="  /models/vae.safetensors  ",
            dtype="fp16",
        )
        assert valid is True
        payload = json.loads(payload_str)
        assert payload["model_path"] == "/models/unet.safetensors"
        assert payload["vae_path"] == "/models/vae.safetensors"

    def test_multiple_allowed_dirs(self):
        """Test with multiple allowed directories."""
        payload_str, valid, reason = self.node.run(
            model_path="/dir1/unet.safetensors",
            vae_path="/dir2/vae.safetensors",
            dtype="fp16",
            allowed_dirs="/dir1,/dir2",
        )
        assert valid is True
        assert reason == "ok"

    def test_non_string_path(self):
        """Test that non-string path inputs are handled gracefully."""
        # The node expects strings, but let's verify the validation logic
        valid, reason = _validate_path(123, [], [])
        assert valid is False
        assert "non-empty string" in reason

    def test_normalize_dtype_none(self):
        """Test that None dtype returns None."""
        assert _normalize_dtype(None) is None

    def test_normalize_dtype_invalid(self):
        """Test that invalid dtype strings return None."""
        assert _normalize_dtype("fp64") is None
        assert _normalize_dtype("invalid") is None
        assert _normalize_dtype("") is None
