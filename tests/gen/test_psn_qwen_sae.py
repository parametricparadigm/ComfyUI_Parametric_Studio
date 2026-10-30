import json
import pytest
from psn_nodes.gen.psn_qwen_sae import PSN_SAE_ConfigValidator, PSN_SAE_TopFeatureAnalyzer

class TestPSN_SAE_ConfigValidator:
    def setup_method(self):
        self.node = PSN_SAE_ConfigValidator()
    
    def test_valid_config(self):
        valid, reason, safe_path = self.node.run(
            sae_path="/models/sae/qwen.safetensors",
            layer=10,
            max_layer=32,
            allowed_dirs="/models/sae"
        )
        assert valid is True
        assert reason == "Configuration valid"
        assert safe_path == "/models/sae/qwen.safetensors"
    
    def test_invalid_layer_exceeds_max(self):
        valid, reason, safe_path = self.node.run(
            sae_path="/models/sae/qwen.safetensors",
            layer=33,
            max_layer=32,
            allowed_dirs="/models/sae"
        )
        assert valid is False
        assert "exceeds max layer" in reason
        assert safe_path == ""
    
    def test_path_traversal(self):
        valid, reason, safe_path = self.node.run(
            sae_path="/models/sae/../etc/passwd",
            layer=10,
            max_layer=32,
            allowed_dirs="/models/sae"
        )
        assert valid is False
        assert "Path traversal" in reason
    
    def test_path_not_in_allowed_dirs(self):
        valid, reason, safe_path = self.node.run(
            sae_path="/other/dir/qwen.safetensors",
            layer=10,
            max_layer=32,
            allowed_dirs="/models/sae"
        )
        assert valid is False
        assert "not in allowed directories" in reason
    
    def test_invalid_extension(self):
        valid, reason, safe_path = self.node.run(
            sae_path="/models/sae/qwen.txt",
            layer=10,
            max_layer=32,
            allowed_dirs="/models/sae"
        )
        assert valid is False
        assert "Invalid file extension" in reason
    
    def test_empty_path(self):
        valid, reason, safe_path = self.node.run(
            sae_path="",
            layer=10,
            max_layer=32,
            allowed_dirs="/models/sae"
        )
        assert valid is False
        assert "SAE path is empty" in reason

class TestPSN_SAE_TopFeatureAnalyzer:
    def setup_method(self):
        self.node = PSN_SAE_TopFeatureAnalyzer()
    
    def test_basic_top_k(self):
        activations = json.dumps([0.1, 0.9, 0.5, 0.8, 0.2])
        top_features, count, max_val = self.node.run(
            activations=activations,
            top_k=2,
            threshold=0.0
        )
        result = json.loads(top_features)
        assert len(result) == 2
        assert result[0]["index"] == 1
        assert result[0]["value"] == 0.9
        assert result[1]["index"] == 3
        assert result[1]["value"] == 0.8
        assert count == 5
        assert max_val == 0.9
    
    def test_threshold_filtering(self):
        activations = json.dumps([0.1, 0.9, 0.5, 0.8, 0.2])
        top_features, count, max_val = self.node.run(
            activations=activations,
            top_k=5,
            threshold=0.7
        )
        result = json.loads(top_features)
        assert len(result) == 2
        assert count == 2
        assert max_val == 0.9
    
    def test_empty_activations(self):
        top_features, count, max_val = self.node.run(
            activations="[]",
            top_k=5,
            threshold=0.0
        )
        assert top_features == "[]"
        assert count == 0
        assert max_val == 0.0
    
    def test_invalid_json(self):
        top_features, count, max_val = self.node.run(
            activations="not json",
            top_k=5,
            threshold=0.0
        )
        assert top_features == "[]"
        assert count == 0
        assert max_val == 0.0
    
    def test_non_numeric_values(self):
        top_features, count, max_val = self.node.run(
            activations='["a", "b"]',
            top_k=5,
            threshold=0.0
        )
        assert top_features == "[]"
        assert count == 0
        assert max_val == 0.0
    
    def test_top_k_larger_than_count(self):
        activations = json.dumps([0.1, 0.2])
        top_features, count, max_val = self.node.run(
            activations=activations,
            top_k=10,
            threshold=0.0
        )
        result = json.loads(top_features)
        assert len(result) == 2
        assert count == 2
