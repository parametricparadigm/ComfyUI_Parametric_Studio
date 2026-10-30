"""
Tests for PSN_Aesthetic_Bias_Patch node.
"""

import json
import pytest
from psn_nodes.gen.psn_aesthetic_bias_patch import PSN_Aesthetic_Bias_Patch, _validate_vector, _scale_vector, _generate_patch_id


class TestPSNAestheticBiasPatch:
    """Test suite for PSN_Aesthetic_Bias_Patch node."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.node = PSN_Aesthetic_Bias_Patch()
    
    def test_valid_single_vector(self):
        """Test with a valid single float vector."""
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.5,
            strength=2.0,
            vector_list=""
        )
        assert patched is True
        bias_vector = json.loads(bias_vector_json)
        assert bias_vector == [1.0]  # 0.5 * 2.0
        assert patch_id is not None
        assert len(patch_id) == 16
    
    def test_valid_vector_list(self):
        """Test with a valid vector list."""
        vector = [0.1, 0.2, 0.3]
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=1.5,
            vector_list=vector_json
        )
        assert patched is True
        bias_vector = json.loads(bias_vector_json)
        expected = [0.15, 0.3, 0.45]
        for i in range(len(expected)):
            assert abs(bias_vector[i] - expected[i]) < 1e-9
        assert patch_id is not None
    
    def test_negative_strength(self):
        """Test with negative strength."""
        vector = [1.0, -1.0, 0.5]
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=-2.0,
            vector_list=vector_json
        )
        assert patched is True
        bias_vector = json.loads(bias_vector_json)
        expected = [-2.0, 2.0, -1.0]
        for i in range(len(expected)):
            assert abs(bias_vector[i] - expected[i]) < 1e-9
    
    def test_invalid_json_vector(self):
        """Test with invalid JSON in vector_list."""
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.5,
            strength=1.0,
            vector_list="not valid json"
        )
        assert patched is False
        assert bias_vector_json == "[]"
        assert "invalid_json" in patch_id
    
    def test_empty_vector_list(self):
        """Test with empty vector list."""
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.5,
            strength=1.0,
            vector_list="[]"
        )
        assert patched is False
        assert bias_vector_json == "[]"
        assert "invalid_vector" in patch_id
    
    def test_vector_with_nan(self):
        """Test with NaN in vector."""
        vector = [0.1, float('nan'), 0.3]
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        assert patched is False
        assert bias_vector_json == "[]"
        assert "invalid_vector" in patch_id
    
    def test_vector_with_infinity(self):
        """Test with infinity in vector."""
        vector = [0.1, float('inf'), 0.3]
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        assert patched is False
        assert bias_vector_json == "[]"
        assert "invalid_vector" in patch_id
    
    def test_vector_with_non_numeric(self):
        """Test with non-numeric values in vector."""
        vector = [0.1, "string", 0.3]
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        assert patched is False
        assert bias_vector_json == "[]"
        assert "invalid_vector" in patch_id
    
    def test_deterministic_patch_id(self):
        """Test that patch ID is deterministic for same inputs."""
        vector = [0.1, 0.2, 0.3]
        vector_json = json.dumps(vector)
        
        _, _, patch_id1 = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        
        _, _, patch_id2 = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        
        assert patch_id1 == patch_id2
    
    def test_different_strength_different_patch_id(self):
        """Test that different strength produces different patch ID."""
        vector = [0.1, 0.2, 0.3]
        vector_json = json.dumps(vector)
        
        _, _, patch_id1 = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        
        _, _, patch_id2 = self.node.run(
            aesthetic_vector=0.0,
            strength=2.0,
            vector_list=vector_json
        )
        
        assert patch_id1 != patch_id2
    
    def test_zero_strength(self):
        """Test with zero strength."""
        vector = [1.0, 2.0, 3.0]
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=0.0,
            vector_list=vector_json
        )
        assert patched is True
        bias_vector = json.loads(bias_vector_json)
        assert bias_vector == [0.0, 0.0, 0.0]
    
    def test_large_vector(self):
        """Test with a large vector (within limits)."""
        vector = [0.1] * 100
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        assert patched is True
        bias_vector = json.loads(bias_vector_json)
        assert len(bias_vector) == 100
        assert all(abs(v - 0.1) < 1e-9 for v in bias_vector)
    
    def test_vector_too_large(self):
        """Test with a vector that exceeds max dimension."""
        vector = [0.1] * 2000  # Exceeds max_dim of 1024
        vector_json = json.dumps(vector)
        patched, bias_vector_json, patch_id = self.node.run(
            aesthetic_vector=0.0,
            strength=1.0,
            vector_list=vector_json
        )
        assert patched is False
        assert bias_vector_json == "[]"
        assert "invalid_vector" in patch_id
    
    def test_validate_vector_helper(self):
        """Test the _validate_vector helper function directly."""
        # Valid vector
        is_valid, msg = _validate_vector([1.0, 2.0, 3.0])
        assert is_valid is True
        assert msg == ""
        
        # Empty vector
        is_valid, msg = _validate_vector([])
        assert is_valid is False
        assert "must not be empty" in msg
        
        # Non-list input
        is_valid, msg = _validate_vector("not a list")
        assert is_valid is False
        assert "must be a list" in msg
        
        # Vector with string
        is_valid, msg = _validate_vector([1.0, "two", 3.0])
        assert is_valid is False
        assert "not a number" in msg
    
    def test_scale_vector_helper(self):
        """Test the _scale_vector helper function directly."""
        vector = [1.0, 2.0, 3.0]
        scaled = _scale_vector(vector, 2.0)
        assert scaled == [2.0, 4.0, 6.0]
        
        scaled = _scale_vector(vector, -1.0)
        assert scaled == [-1.0, -2.0, -3.0]
        
        scaled = _scale_vector(vector, 0.0)
        assert scaled == [0.0, 0.0, 0.0]
    
    def test_generate_patch_id_helper(self):
        """Test the _generate_patch_id helper function directly."""
        vector = [1.0, 2.0, 3.0]
        strength = 1.5
        patch_id = _generate_patch_id(vector, strength)
        assert len(patch_id) == 16
        assert all(c in '0123456789abcdef' for c in patch_id)
        
        # Same inputs should give same ID
        patch_id2 = _generate_patch_id(vector, strength)
        assert patch_id == patch_id2
        
        # Different inputs should give different ID
        patch_id3 = _generate_patch_id(vector, 2.0)
        assert patch_id != patch_id3
