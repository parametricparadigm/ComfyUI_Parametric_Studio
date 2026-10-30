"""
Tests for PSN Dynamic Pipeline Parameter Injection nodes.
"""

import json
import pytest
from psn_nodes.gen.n_1_dynamic_pipeline_parameter_injection import (
    PSN_JSON_Config_Loader,
    PSN_Param_Injector,
    _resolve_key_path,
)


class TestPSN_JSON_Config_Loader:
    def test_parse_valid_json(self):
        node = PSN_JSON_Config_Loader()
        json_text = json.dumps({"sdxl": {"steps": 20, "cfg": 7.0}})
        config, success, reason = node.run(json_text=json_text)
        assert success is True
        assert config == {"sdxl": {"steps": 20, "cfg": 7.0}}
        assert "parsed full JSON dict" in reason

    def test_parse_with_key_path(self):
        node = PSN_JSON_Config_Loader()
        json_text = json.dumps({"model": {"sdxl": {"steps": 20, "cfg": 7.0}}})
        config, success, reason = node.run(json_text=json_text, key_path="model.sdxl.steps")
        assert success is True
        assert config == {}  # non-dict value returns empty dict
        assert "resolved key_path" in reason

    def test_parse_with_key_path_returns_dict(self):
        node = PSN_JSON_Config_Loader()
        json_text = json.dumps({"model": {"sdxl": {"steps": 20, "cfg": 7.0}}})
        config, success, reason = node.run(json_text=json_text, key_path="model.sdxl")
        assert success is True
        assert config == {"steps": 20, "cfg": 7.0}

    def test_invalid_json(self):
        node = PSN_JSON_Config_Loader()
        config, success, reason = node.run(json_text="{invalid json")
        assert success is False
        assert "JSON parse error" in reason

    def test_empty_json_text(self):
        node = PSN_JSON_Config_Loader()
        config, success, reason = node.run(json_text="")
        assert success is False
        assert "empty" in reason

    def test_non_dict_top_level(self):
        node = PSN_JSON_Config_Loader()
        config, success, reason = node.run(json_text="[1, 2, 3]")
        assert success is False
        assert "not a dict" in reason

    def test_key_path_not_found(self):
        node = PSN_JSON_Config_Loader()
        json_text = json.dumps({"a": {"b": 1}})
        config, success, reason = node.run(json_text=json_text, key_path="a.c")
        assert success is False
        assert "not found" in reason

    def test_key_path_traversal_into_non_dict(self):
        node = PSN_JSON_Config_Loader()
        json_text = json.dumps({"a": 1})
        config, success, reason = node.run(json_text=json_text, key_path="a.b")
        assert success is False
        assert "not a dict" in reason


class TestPSN_Param_Injector:
    def test_inject_into_mock_k_sampler(self):
        node = PSN_Param_Injector()
        graph = {
            "3": {
                "class_type": "KSampler",
                "inputs": {"steps": 20, "cfg": 7.0, "sampler_name": "euler"},
            }
        }
        updated, success, reason = node.run(
            graph=graph,
            target_node_id="3",
            param_name="steps",
            value=5,
        )
        assert success is True
        assert updated["3"]["inputs"]["steps"] == 5
        assert updated["3"]["inputs"]["cfg"] == 7.0  # unchanged
        assert "injected" in reason

    def test_inject_does_not_mutate_original(self):
        node = PSN_Param_Injector()
        graph = {
            "1": {
                "class_type": "KSampler",
                "inputs": {"steps": 20},
            }
        }
        original_steps = graph["1"]["inputs"]["steps"]
        updated, success, reason = node.run(
            graph=graph,
            target_node_id="1",
            param_name="steps",
            value=10,
        )
        assert success is True
        assert updated["1"]["inputs"]["steps"] == 10
        assert graph["1"]["inputs"]["steps"] == original_steps  # original unchanged

    def test_inject_into_nonexistent_node(self):
        node = PSN_Param_Injector()
        graph = {"1": {"class_type": "KSampler", "inputs": {"steps": 20}}}
        updated, success, reason = node.run(
            graph=graph,
            target_node_id="99",
            param_name="steps",
            value=5,
        )
        assert success is False
        assert "not found" in reason

    def test_inject_empty_node_id(self):
        node = PSN_Param_Injector()
        graph = {"1": {"class_type": "KSampler", "inputs": {"steps": 20}}}
        updated, success, reason = node.run(
            graph=graph,
            target_node_id="",
            param_name="steps",
            value=5,
        )
        assert success is False
        assert "empty" in reason

    def test_inject_empty_param_name(self):
        node = PSN_Param_Injector()
        graph = {"1": {"class_type": "KSampler", "inputs": {"steps": 20}}}
        updated, success, reason = node.run(
            graph=graph,
            target_node_id="1",
            param_name="",
            value=5,
        )
        assert success is False
        assert "empty" in reason

    def test_inject_node_without_inputs(self):
        node = PSN_Param_Injector()
        graph = {"1": {"class_type": "SomeNode"}}
        updated, success, reason = node.run(
            graph=graph,
            target_node_id="1",
            param_name="steps",
            value=5,
        )
        assert success is False
        assert "no 'inputs' dict" in reason

    def test_inject_non_dict_graph(self):
        node = PSN_Param_Injector()
        updated, success, reason = node.run(
            graph="not a dict",
            target_node_id="1",
            param_name="steps",
            value=5,
        )
        assert success is False
        assert "must be a dict" in reason


class TestResolveKeyPath:
    def test_resolve_simple_key(self):
        data = {"a": 1}
        found, value, reason = _resolve_key_path(data, "a")
        assert found is True
        assert value == 1

    def test_resolve_nested_key(self):
        data = {"a": {"b": {"c": 42}}}
        found, value, reason = _resolve_key_path(data, "a.b.c")
        assert found is True
        assert value == 42

    def test_resolve_missing_key(self):
        data = {"a": 1}
        found, value, reason = _resolve_key_path(data, "b")
        assert found is False
        assert value is None

    def test_resolve_empty_key_path(self):
        data = {"a": 1}
        found, value, reason = _resolve_key_path(data, "")
        assert found is True
        assert value == data
