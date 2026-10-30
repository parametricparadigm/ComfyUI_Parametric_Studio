import pytest
from psn_nodes.gen.psn_latentinterpolator import PSN_LatentInterpolator

class TestPSN_LatentInterpolator:
    def setup_method(self):
        self.node = PSN_LatentInterpolator()

    def test_lerp_basic(self):
        # Test basic lerp between two scalars
        result, valid, reason = self.node.run(0.0, 1.0, 0.5, "lerp")
        assert valid is True
        assert reason == "Success"
        assert abs(result - 0.5) < 1e-6

    def test_lerp_vectors(self):
        # Test lerp between two vectors
        vec_a = "[1.0, 2.0, 3.0]"
        vec_b = "[4.0, 5.0, 6.0]"
        result, valid, reason = self.node.run(0.0, 0.0, 0.5, "lerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # First element should be (1+4)/2 = 2.5
        assert abs(result - 2.5) < 1e-6

    def test_slerp_basic(self):
        # Test slerp between two orthogonal unit vectors
        vec_a = "[1.0, 0.0]"
        vec_b = "[0.0, 1.0]"
        result, valid, reason = self.node.run(0.0, 0.0, 0.5, "slerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # Slerp of orthogonal vectors at t=0.5 should be [1/sqrt(2), 1/sqrt(2)]
        expected = 1.0 / math.sqrt(2)
        assert abs(result - expected) < 1e-6

    def test_slerp_parallel_vectors(self):
        # Test slerp with parallel vectors (should fall back to lerp)
        vec_a = "[1.0, 0.0]"
        vec_b = "[2.0, 0.0]"
        result, valid, reason = self.node.run(0.0, 0.0, 0.5, "slerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # Should be lerp: (1+2)/2 = 1.5
        assert abs(result - 1.5) < 1e-6

    def test_invalid_vector_lengths(self):
        # Test with mismatched vector lengths
        vec_a = "[1.0, 2.0]"
        vec_b = "[1.0, 2.0, 3.0]"
        result, valid, reason = self.node.run(0.0, 0.0, 0.5, "lerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is False
        assert "Vector lengths must match" in reason

    def test_invalid_t_value(self):
        # Test with t out of range
        result, valid, reason = self.node.run(0.0, 1.0, 1.5, "lerp")
        assert valid is False
        assert "t must be between 0 and 1" in reason

    def test_invalid_method(self):
        # Test with unknown method
        result, valid, reason = self.node.run(0.0, 1.0, 0.5, "invalid_method")
        assert valid is False
        assert "Unknown method" in reason

    def test_zero_vector_slerp(self):
        # Test slerp with zero vector (should fall back to lerp)
        vec_a = "[0.0, 0.0]"
        vec_b = "[1.0, 0.0]"
        result, valid, reason = self.node.run(0.0, 0.0, 0.5, "slerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # Should be lerp: (0+1)/2 = 0.5
        assert abs(result - 0.5) < 1e-6

import math
