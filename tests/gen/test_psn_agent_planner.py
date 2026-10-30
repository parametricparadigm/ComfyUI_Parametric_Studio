"""Tests for PSN_Agent_Planner node."""

import json
import pytest

from psn_nodes.gen.psn_agent_planner import (
    PSN_Agent_Planner,
    validate_plan,
    _validate_plan_structure,
    _validate_node,
    _validate_edge,
    _validate_metadata,
)


def _make_available_nodes():
    """Create a sample available_nodes dict."""
    return {
        "KSampler": {"inputs": {"seed": "INT", "steps": "INT"}},
        "CheckpointLoaderSimple": {"inputs": {"ckpt_name": "STRING"}},
        "CLIPTextEncode": {"inputs": {"text": "STRING"}},
    }


def _make_valid_plan():
    """Create a valid plan JSON string."""
    plan = {
        "nodes": [
            {"id": "node1", "class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
            {"id": "node2", "class_type": "CLIPTextEncode", "inputs": {"text": "cyberpunk city"}},
            {"id": "node3", "class_type": "KSampler", "inputs": {"seed": 42, "steps": 20}},
        ],
        "edges": [
            {"from_node": "node1", "from_slot": "0", "to_node": "node3", "to_slot": "0"},
            {"from_node": "node2", "from_slot": "0", "to_node": "node3", "to_slot": "1"},
        ],
        "metadata": {"reasoning": "Test plan", "version": "1.0"},
    }
    return json.dumps(plan)


class TestValidatePlanStructure:
    def test_valid_structure(self):
        plan = {"nodes": [], "edges": []}
        ok, why = _validate_plan_structure(plan)
        assert ok is True
        assert why == "OK"

    def test_missing_nodes(self):
        plan = {"edges": []}
        ok, why = _validate_plan_structure(plan)
        assert ok is False
        assert "nodes" in why

    def test_missing_edges(self):
        plan = {"nodes": []}
        ok, why = _validate_plan_structure(plan)
        assert ok is False
        assert "edges" in why

    def test_unexpected_top_level_key(self):
        plan = {"nodes": [], "edges": [], "foo": "bar"}
        ok, why = _validate_plan_structure(plan)
        assert ok is False
        assert "foo" in why

    def test_nodes_not_list(self):
        plan = {"nodes": "not a list", "edges": []}
        ok, why = _validate_plan_structure(plan)
        assert ok is False
        assert "list" in why


class TestValidateNode:
    def test_valid_node(self):
        available = _make_available_nodes()
        node_ids = set()
        node = {"id": "n1", "class_type": "KSampler", "inputs": {"seed": 1}}
        ok, why = _validate_node(node, available, node_ids)
        assert ok is True
        assert why == "OK"

    def test_unknown_class_type(self):
        available = _make_available_nodes()
        node_ids = set()
        node = {"id": "n1", "class_type": "UnknownNode"}
        ok, why = _validate_node(node, available, node_ids)
        assert ok is False
        assert "UnknownNode" in why

    def test_duplicate_node_id(self):
        available = _make_available_nodes()
        node_ids = {"n1"}
        node = {"id": "n1", "class_type": "KSampler"}
        ok, why = _validate_node(node, available, node_ids)
        assert ok is False
        assert "Duplicate" in why

    def test_missing_id(self):
        available = _make_available_nodes()
        node_ids = set()
        node = {"class_type": "KSampler"}
        ok, why = _validate_node(node, available, node_ids)
        assert ok is False
        assert "id" in why

    def test_missing_class_type(self):
        available = _make_available_nodes()
        node_ids = set()
        node = {"id": "n1"}
        ok, why = _validate_node(node, available, node_ids)
        assert ok is False
        assert "class_type" in why

    def test_unexpected_node_key(self):
        available = _make_available_nodes()
        node_ids = set()
        node = {"id": "n1", "class_type": "KSampler", "extra": "bad"}
        ok, why = _validate_node(node, available, node_ids)
        assert ok is False
        assert "extra" in why


class TestValidateEdge:
    def test_valid_edge(self):
        node_ids = {"n1", "n2"}
        edge = {"from_node": "n1", "from_slot": "0", "to_node": "n2", "to_slot": "0"}
        ok, why = _validate_edge(edge, node_ids)
        assert ok is True
        assert why == "OK"

    def test_unknown_from_node(self):
        node_ids = {"n1"}
        edge = {"from_node": "n99", "from_slot": "0", "to_node": "n1", "to_slot": "0"}
        ok, why = _validate_edge(edge, node_ids)
        assert ok is False
        assert "n99" in why

    def test_unknown_to_node(self):
        node_ids = {"n1"}
        edge = {"from_node": "n1", "from_slot": "0", "to_node": "n99", "to_slot": "0"}
        ok, why = _validate_edge(edge, node_ids)
        assert ok is False
        assert "n99" in why

    def test_self_loop(self):
        node_ids = {"n1"}
        edge = {"from_node": "n1", "from_slot": "0", "to_node": "n1", "to_slot": "0"}
        ok, why = _validate_edge(edge, node_ids)
        assert ok is False
        assert "itself" in why

    def test_missing_required_key(self):
        node_ids = {"n1", "n2"}
        edge = {"from_node": "n1", "to_node": "n2"}
        ok, why = _validate_edge(edge, node_ids)
        assert ok is False
        assert "from_slot" in why or "to_slot" in why


class TestValidateMetadata:
    def test_valid_metadata(self):
        meta = {"reasoning": "test", "version": "1.0"}
        ok, why = _validate_metadata(meta)
        assert ok is True
        assert why == "OK"

    def test_unexpected_metadata_key(self):
        meta = {"foo": "bar"}
        ok, why = _validate_metadata(meta)
        assert ok is False
        assert "foo" in why

    def test_metadata_not_dict(self):
        ok, why = _validate_metadata("not a dict")
        assert ok is False
        assert "object" in why


class TestValidatePlan:
    def test_valid_plan(self):
        available = _make_available_nodes()
        plan_json = _make_valid_plan()
        ok, why, cleaned = validate_plan(plan_json, available)
        assert ok is True
        assert why == "OK"
        assert len(cleaned["nodes"]) == 3
        assert len(cleaned["edges"]) == 2

    def test_invalid_json(self):
        available = _make_available_nodes()
        ok, why, cleaned = validate_plan("not json", available)
        assert ok is False
        assert "Invalid JSON" in why
        assert cleaned == {}

    def test_empty_plan_json(self):
        available = _make_available_nodes()
        ok, why, cleaned = validate_plan("", available)
        assert ok is False

    def test_plan_with_unknown_node_class(self):
        available = _make_available_nodes()
        plan = {
            "nodes": [{"id": "n1", "class_type": "NonExistent"}],
            "edges": [],
        }
        ok, why, cleaned = validate_plan(json.dumps(plan), available)
        assert ok is False
        assert "NonExistent" in why

    def test_plan_with_bad_edge(self):
        available = _make_available_nodes()
        plan = {
            "nodes": [
                {"id": "n1", "class_type": "KSampler"},
                {"id": "n2", "class_type": "KSampler"},
            ],
            "edges": [
                {"from_node": "n1", "from_slot": "0", "to_node": "n99", "to_slot": "0"},
            ],
        }
        ok, why, cleaned = validate_plan(json.dumps(plan), available)
        assert ok is False
        assert "n99" in why


class TestPSNAgentPlannerNode:
    def test_run_valid_plan(self):
        node = PSN_Agent_Planner()
        available = _make_available_nodes()
        plan_json = _make_valid_plan()
        result_json, reasoning, is_valid = node.run(
            goal="Create a cyberpunk cityscape",
            available_nodes=available,
            plan_json=plan_json,
        )
        assert is_valid is True
        assert "validated successfully" in reasoning
        parsed = json.loads(result_json)
        assert len(parsed["nodes"]) == 3
        assert len(parsed["edges"]) == 2

    def test_run_invalid_json(self):
        node = PSN_Agent_Planner()
        available = _make_available_nodes()
        result_json, reasoning, is_valid = node.run(
            goal="Test",
            available_nodes=available,
            plan_json="invalid json",
        )
        assert is_valid is False
        assert "validation failed" in reasoning
        assert result_json == "{}"

    def test_run_with_empty_available_nodes(self):
        node = PSN_Agent_Planner()
        plan = {
            "nodes": [{"id": "n1", "class_type": "KSampler"}],
            "edges": [],
        }
        result_json, reasoning, is_valid = node.run(
            goal="Test",
            available_nodes={},
            plan_json=json.dumps(plan),
        )
        assert is_valid is False
        assert "Unknown class_type" in reasoning

    def test_run_with_none_llm_connection(self):
        node = PSN_Agent_Planner()
        available = _make_available_nodes()
        plan_json = _make_valid_plan()
        result_json, reasoning, is_valid = node.run(
            goal="Test",
            available_nodes=available,
            plan_json=plan_json,
            llm_connection=None,
        )
        assert is_valid is True

    def test_run_with_non_dict_available_nodes(self):
        node = PSN_Agent_Planner()
        plan_json = _make_valid_plan()
        result_json, reasoning, is_valid = node.run(
            goal="Test",
            available_nodes="not a dict",
            plan_json=plan_json,
        )
        assert is_valid is False
        assert "Unknown class_type" in reasoning

    def test_input_types_structure(self):
        it = PSN_Agent_Planner.INPUT_TYPES()
        assert "required" in it
        assert "optional" in it
        assert "goal" in it["required"]
        assert "available_nodes" in it["required"]
        assert "plan_json" in it["required"]
        assert "llm_connection" in it["optional"]

    def test_return_types(self):
        assert PSN_Agent_Planner.RETURN_TYPES == ("STRING", "STRING", "BOOLEAN")
        assert PSN_Agent_Planner.RETURN_NAMES == ("plan_json", "reasoning", "is_valid")
        assert PSN_Agent_Planner.FUNCTION == "run"
