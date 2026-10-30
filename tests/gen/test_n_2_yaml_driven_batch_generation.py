"""
Tests for PSN_YAML_Batch_Definer node.
"""

import json
import pytest
from psn_nodes.gen.n_2_yaml_driven_batch_generation import (
    PSN_YAML_Batch_Definer,
    _parse_yaml_simple,
    _inject_parameters,
)


class TestParseYamlSimple:
    """Tests for the simple YAML parser."""
    
    def test_basic_key_value(self):
        yaml_str = "count: 3\nseed_offset: 10"
        result = _parse_yaml_simple(yaml_str)
        assert result == {"count": 3, "seed_offset": 10}
    
    def test_list_parsing(self):
        yaml_str = "prompt_list:\n  - hello\n  - world\n  - foo"
        result = _parse_yaml_simple(yaml_str)
        assert result == {"prompt_list": ["hello", "world", "foo"]}
    
    def test_nested_dict(self):
        yaml_str = "outer:\n  inner: 42\n  other: true"
        result = _parse_yaml_simple(yaml_str)
        assert result == {"outer": {"inner": 42, "other": True}}
    
    def test_empty_yaml(self):
        result = _parse_yaml_simple("")
        assert result == {}
    
    def test_none_input(self):
        result = _parse_yaml_simple(None)
        assert result == {}
    
    def test_comments_ignored(self):
        yaml_str = "# comment\ncount: 5\n# another comment\nseed_offset: 2"
        result = _parse_yaml_simple(yaml_str)
        assert result == {"count": 5, "seed_offset": 2}


class TestInjectParameters:
    """Tests for parameter injection into graph dicts."""
    
    def test_seed_injection(self):
        graph = {"3": {"inputs": {"seed": 0}}}
        params = {"seed_offset": 10, "seed_base": 100, "seed_node_id": "3", "seed_param_name": "seed"}
        result = _inject_parameters(graph, params, 2)
        assert result["3"]["inputs"]["seed"] == 120  # 100 + 2*10
    
    def test_prompt_injection(self):
        graph = {"1": {"inputs": {"text": "old"}}}
        params = {"prompt_list": ["a", "b", "c"], "prompt_node_id": "1", "prompt_param_name": "text"}
        result = _inject_parameters(graph, params, 1)
        assert result["1"]["inputs"]["text"] == "b"
    
    def test_no_injection_when_nodes_missing(self):
        graph = {}
        params = {"seed_offset": 10, "seed_base": 0, "prompt_list": ["a"]}
        result = _inject_parameters(graph, params, 0)
        assert result == {}
    
    def test_prompt_out_of_range(self):
        graph = {"1": {"inputs": {"text": "default"}}}
        params = {"prompt_list": ["a"], "prompt_node_id": "1", "prompt_param_name": "text"}
        result = _inject_parameters(graph, params, 5)
        assert result["1"]["inputs"]["text"] == "default"


class TestPSNYAMLBatchDefiner:
    """Tests for the main node class."""
    
    def setup_method(self):
        self.node = PSN_YAML_Batch_Definer()
    
    def test_basic_batch_generation(self):
        yaml_content = "count: 3\nseed_offset: 100\nseed_base: 1000"
        base_graph = json.dumps({"3": {"inputs": {"seed": 0}}})
        batch_graphs, metadata = self.node.run(yaml_content, base_graph)
        
        assert len(batch_graphs) == 3
        assert metadata["count"] == 3
        assert metadata["seed_offset"] == 100
        assert metadata["seed_base"] == 1000
        
        # Check seeds are distinct
        seeds = []
        for bg in batch_graphs:
            g = json.loads(bg)
            seeds.append(g["3"]["inputs"]["seed"])
        assert seeds == [1000, 1100, 1200]
        assert len(set(seeds)) == 3
    
    def test_prompt_list_cycling(self):
        yaml_content = "count: 4\nseed_offset: 1\nprompt_list:\n  - cat\n  - dog"
        base_graph = json.dumps({"1": {"inputs": {"text": "default"}}, "3": {"inputs": {"seed": 0}}})
        batch_graphs, metadata = self.node.run(yaml_content, base_graph)
        
        assert len(batch_graphs) == 4
        prompts = []
        for bg in batch_graphs:
            g = json.loads(bg)
            prompts.append(g["1"]["inputs"]["text"])
        # Only 2 prompts, so iterations 2 and 3 keep default
        assert prompts == ["cat", "dog", "default", "default"]
    
    def test_single_iteration(self):
        yaml_content = "count: 1\nseed_offset: 5"
        base_graph = json.dumps({"3": {"inputs": {"seed": 0}}})
        batch_graphs, metadata = self.node.run(yaml_content, base_graph)
        
        assert len(batch_graphs) == 1
        g = json.loads(batch_graphs[0])
        assert g["3"]["inputs"]["seed"] == 0
    
    def test_invalid_base_graph_json(self):
        yaml_content = "count: 2"
        with pytest.raises(ValueError, match="Invalid base_graph JSON"):
            self.node.run(yaml_content, "not valid json")
    
    def test_base_graph_not_dict(self):
        yaml_content = "count: 2"
        with pytest.raises(ValueError, match="must be a JSON object"):
            self.node.run(yaml_content, "[1, 2, 3]")
    
    def test_count_less_than_one_defaults_to_one(self):
        yaml_content = "count: 0\nseed_offset: 1"
        base_graph = json.dumps({"3": {"inputs": {"seed": 0}}})
        batch_graphs, metadata = self.node.run(yaml_content, base_graph)
        assert len(batch_graphs) == 1
    
    def test_seed_base_override(self):
        yaml_content = "count: 2\nseed_offset: 10"
        base_graph = json.dumps({"3": {"inputs": {"seed": 0}}})
        batch_graphs, metadata = self.node.run(yaml_content, base_graph, seed_base=500)
        
        assert metadata["seed_base"] == 500
        seeds = [json.loads(bg)["3"]["inputs"]["seed"] for bg in batch_graphs]
        assert seeds == [500, 510]
    
    def test_empty_yaml_content(self):
        base_graph = json.dumps({"3": {"inputs": {"seed": 0}}})
        batch_graphs, metadata = self.node.run("", base_graph)
        assert len(batch_graphs) == 1  # Default count is 1
        assert metadata == {"seed_base": 0}
    
    def test_complex_graph_preserved(self):
        base_graph = json.dumps({
            "1": {"inputs": {"text": "original"}},
            "3": {"inputs": {"seed": 0, "steps": 20}},
            "4": {"inputs": {"cfg": 7.5}}
        })
        yaml_content = "count: 2\nseed_offset: 100\nprompt_list:\n  - new prompt"
        batch_graphs, metadata = self.node.run(yaml_content, base_graph)
        
        assert len(batch_graphs) == 2
        g0 = json.loads(batch_graphs[0])
        g1 = json.loads(batch_graphs[1])
        
        # Prompt injected only for first iteration
        assert g0["1"]["inputs"]["text"] == "new prompt"
        assert g1["1"]["inputs"]["text"] == "original"
        
        # Seeds distinct
        assert g0["3"]["inputs"]["seed"] == 0
        assert g1["3"]["inputs"]["seed"] == 100
        
        # Other params preserved
        assert g0["3"]["inputs"]["steps"] == 20
        assert g0["4"]["inputs"]["cfg"] == 7.5
        assert g1["4"]["inputs"]["cfg"] == 7.5
    
    def test_return_types_and_names(self):
        assert PSN_YAML_Batch_Definer.RETURN_TYPES == ("LIST", "DICT")
        assert PSN_YAML_Batch_Definer.RETURN_NAMES == ("batch_graphs", "metadata")
        assert PSN_YAML_Batch_Definer.FUNCTION == "run"
