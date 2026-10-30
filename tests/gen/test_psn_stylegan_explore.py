"""
Tests for PSN StyleGAN Explore nodes.
"""

import json
import math
import pytest

from psn_nodes.gen.psn_stylegan_explore import (
    PSN_StyleGAN_Load,
    PSN_StyleGAN_Slerp,
    PSN_StyleGAN_Generate,
    _validate_model_path,
    _slerp_single,
    _slerp_sequence,
)


class TestPSN_StyleGAN_Load:
    def test_valid_model_path(self):
        node = PSN_StyleGAN_Load()
        result = node.run("stylegan2.pt")
        assert len(result) == 1
        model_data = json.loads(result[0])
        assert model_data["type"] == "stylegan2"
        assert model_data["path"] == "stylegan2.pt"
        assert model_data["status"] == "validated"

    def test_invalid_extension(self):
        node = PSN_StyleGAN_Load()
        with pytest.raises(ValueError, match="Invalid model path"):
            node.run("stylegan2.txt")

    def test_empty_path(self):
        node = PSN_StyleGAN_Load()
        with pytest.raises(ValueError, match="Invalid model path"):
            node.run("")

    def test_non_string_path(self):
        node = PSN_StyleGAN_Load()
        with pytest.raises(ValueError, match="Invalid model path"):
            node.run(12345)


class TestPSN_StyleGAN_Slerp:
    def test_basic_slerp(self):
        node = PSN_StyleGAN_Slerp()
        latent_a = json.dumps([1.0, 0.0, 0.0])
        latent_b = json.dumps([0.0, 1.0, 0.0])
        result = node.run(latent_a, latent_b, 3, 0.0, 1.0)
        frames = json.loads(result[0])
        assert len(frames) == 3
        # First frame should be close to latent_a
        assert abs(frames[0][0] - 1.0) < 0.01
        assert abs(frames[0][1] - 0.0) < 0.01
        # Last frame should be close to latent_b
        assert abs(frames[-1][0] - 0.0) < 0.01
        assert abs(frames[-1][1] - 1.0) < 0.01

    def test_slerp_single_frame(self):
        node = PSN_StyleGAN_Slerp()
        latent_a = json.dumps([1.0, 0.0])
        latent_b = json.dumps([0.0, 1.0])
        result = node.run(latent_a, latent_b, 1, 0.0, 1.0)
        frames = json.loads(result[0])
        assert len(frames) == 1
        # With num_frames=1, t should be t_start=0.0, so result should be close to latent_a
        assert abs(frames[0][0] - 1.0) < 0.01
        assert abs(frames[0][1] - 0.0) < 0.01

    def test_mismatched_vector_lengths(self):
        node = PSN_StyleGAN_Slerp()
        latent_a = json.dumps([1.0, 0.0])
        latent_b = json.dumps([0.0, 1.0, 0.0])
        with pytest.raises(ValueError, match="same length"):
            node.run(latent_a, latent_b, 5, 0.0, 1.0)

    def test_invalid_json_input(self):
        node = PSN_StyleGAN_Slerp()
        with pytest.raises(ValueError, match="valid JSON"):
            node.run("not json", "[0.0, 1.0]", 5, 0.0, 1.0)

    def test_empty_vector(self):
        node = PSN_StyleGAN_Slerp()
        latent_a = json.dumps([])
        latent_b = json.dumps([])
        with pytest.raises(ValueError, match="must not be empty"):
            node.run(latent_a, latent_b, 5, 0.0, 1.0)

    def test_invalid_t_range(self):
        node = PSN_StyleGAN_Slerp()
        latent_a = json.dumps([1.0, 0.0])
        latent_b = json.dumps([0.0, 1.0])
        with pytest.raises(ValueError, match="t_start must be between"):
            node.run(latent_a, latent_b, 5, -0.1, 1.0)

    def test_zero_vector_fallback(self):
        """When one vector is near zero, slerp should fall back to linear interpolation."""
        node = PSN_StyleGAN_Slerp()
        latent_a = json.dumps([0.0, 0.0])
        latent_b = json.dumps([1.0, 1.0])
        result = node.run(latent_a, latent_b, 3, 0.0, 1.0)
        frames = json.loads(result[0])
        assert len(frames) == 3
        # Linear interpolation: at t=0, should be [0,0]; at t=1, should be [1,1]
        assert abs(frames[0][0] - 0.0) < 0.01
        assert abs(frames[0][1] - 0.0) < 0.01
        assert abs(frames[-1][0] - 1.0) < 0.01
        assert abs(frames[-1][1] - 1.0) < 0.01


class TestPSN_StyleGAN_Generate:
    def test_valid_generate(self):
        node = PSN_StyleGAN_Generate()
        model = json.dumps({"type": "stylegan2", "path": "test.pt"})
        latents = json.dumps([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
        result = node.run(model, latents)
        image_data = json.loads(result[0])
        assert image_data["type"] == "stylegan2_output"
        assert image_data["num_frames"] == 3
        assert image_data["latent_dim"] == 2

    def test_invalid_model_json(self):
        node = PSN_StyleGAN_Generate()
        with pytest.raises(ValueError, match="valid JSON"):
            node.run("not json", "[[1.0, 0.0]]")

    def test_empty_latents(self):
        node = PSN_StyleGAN_Generate()
        model = json.dumps({"type": "stylegan2"})
        with pytest.raises(ValueError, match="at least one frame"):
            node.run(model, "[]")

    def test_invalid_frame_content(self):
        node = PSN_StyleGAN_Generate()
        model = json.dumps({"type": "stylegan2"})
        latents = json.dumps([["not a number", 0.0]])
        with pytest.raises(ValueError, match="only numbers"):
            node.run(model, latents)


class TestSlerpMath:
    def test_slerp_parallel_vectors(self):
        """When vectors are parallel, slerp should fall back to linear interpolation."""
        v1 = [1.0, 0.0]
        v2 = [2.0, 0.0]
        result = _slerp_single(v1, v2, 0.5)
        assert abs(result[0] - 1.5) < 0.01
        assert abs(result[1] - 0.0) < 0.01

    def test_slerp_orthogonal_vectors(self):
        """Slerp between orthogonal vectors at t=0.5 should give a normalized midpoint."""
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        result = _slerp_single(v1, v2, 0.5)
        # The result should be a unit vector at 45 degrees
        norm = math.sqrt(result[0] ** 2 + result[1] ** 2)
        assert abs(norm - 1.0) < 0.01
        assert abs(result[0] - result[1]) < 0.01

    def test_slerp_endpoints(self):
        """At t=0, result should be v1; at t=1, result should be v2."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        result_start = _slerp_single(v1, v2, 0.0)
        result_end = _slerp_single(v1, v2, 1.0)
        assert abs(result_start[0] - 1.0) < 0.01
        assert abs(result_start[1] - 0.0) < 0.01
        assert abs(result_end[0] - 0.0) < 0.01
        assert abs(result_end[1] - 1.0) < 0.01
