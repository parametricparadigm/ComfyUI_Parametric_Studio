"""Tests for PSN_Workflow_Plugin_Exposer node and its helper functions."""

import json
import pytest

from psn_nodes.gen.n_6_expose_studio_workflows_as_plugins import (
    PSN_Workflow_Plugin_Exposer,
    build_plugin_descriptor,
    _validate_graph_json,
    _extract_node_ids,
    _validate_node_types,
    _validate_schema,
    _sanitize_plugin_name,
    _generate_plugin_id,
    _generate_endpoint_url,
    ALLOWED_NODE_TYPES,
    MAX_GRAPH_JSON_LENGTH,
    MAX_NODE_COUNT,
    PLUGIN_API_VERSION,
    SIMULATED_BASE_URL,
)


def _make_valid_graph():
    """Create a valid minimal graph JSON string."""
    graph = {
        "nodes": [
            {"id": 1, "type": "CheckpointLoaderSimple", "title": "Checkpoint"},
            {"id": 2, "type": "CLIPTextEncode", "title": "Prompt"},
            {"id": 3, "type": "KSampler", "title": "Sampler"},
            {"id": 4, "type": "VAEDecode", "title": "Decode"},
            {"id": 5, "type": "SaveImage", "title": "Save"},
        ]
    }
    return json.dumps(graph)


def _make_valid_input_schema():
    """Create a valid input schema JSON string."""
    schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "source_node": 2},
            "steps": {"type": "integer", "source_node": 3},
        },
    }
    return json.dumps(schema)


def _make_valid_output_schema():
    """Create a valid output schema JSON string."""
    schema = {
        "type": "object",
        "properties": {
            "image": {"type": "string", "source_node": 5},
        },
    }
    return json.dumps(schema)


class TestBuildPluginDescriptor:
    """Tests for the build_plugin_descriptor function."""

    def test_valid_graph_and_schemas(self):
        """Test that a valid graph and schemas produce a correct descriptor."""
        graph_json = _make_valid_graph()
        input_schema = _make_valid_input_schema()
        output_schema = _make_valid_output_schema()

        descriptor = build_plugin_descriptor(
            graph_json=graph_json,
            plugin_name="test_plugin",
            input_schema=input_schema,
            output_schema=output_schema,
        )

        assert descriptor["plugin_name"] == "test_plugin"
        assert descriptor["api_version"] == PLUGIN_API_VERSION
        assert descriptor["node_ids"] == ["1", "2", "3", "4", "5"]
        assert descriptor["node_types"] == [
            "CheckpointLoaderSimple",
            "CLIPTextEncode",
            "KSampler",
            "VAEDecode",
            "SaveImage",
        ]
        assert descriptor["metadata"]["node_count"] == 5
        assert "plugin_id" in descriptor
        assert "endpoint_url" in descriptor
        assert descriptor["endpoint_url"].startswith(SIMULATED_BASE_URL)
        assert descriptor["input_schema"]["type"] == "object"
        assert descriptor["output_schema"]["type"] == "object"

    def test_invalid_graph_json_not_json(self):
        """Test that invalid JSON in graph_json raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            build_plugin_descriptor(
                graph_json="not valid json",
                plugin_name="test",
                input_schema="{}",
                output_schema="{}",
            )

    def test_invalid_graph_missing_nodes_key(self):
        """Test that graph without 'nodes' key raises ValueError."""
        with pytest.raises(ValueError, match="must contain a 'nodes' key"):
            build_plugin_descriptor(
                graph_json=json.dumps({"edges": []}),
                plugin_name="test",
                input_schema="{}",
                output_schema="{}",
            )

    def test_invalid_node_type_not_in_allowlist(self):
        """Test that a node type not in the allow-list raises ValueError."""
        graph = {
            "nodes": [
                {"id": 1, "type": "EvilNode", "title": "Bad"},
            ]
        }
        with pytest.raises(ValueError, match="not in the allowed node types list"):
            build_plugin_descriptor(
                graph_json=json.dumps(graph),
                plugin_name="test",
                input_schema="{}",
                output_schema="{}",
            )

    def test_invalid_schema_references_nonexistent_node(self):
        """Test that a schema referencing a nonexistent node raises ValueError."""
        graph_json = _make_valid_graph()
        bad_schema = json.dumps({
            "type": "object",
            "properties": {
                "data": {"type": "string", "source_node": 999},
            },
        })
        with pytest.raises(ValueError, match="does not exist in the graph"):
            build_plugin_descriptor(
                graph_json=graph_json,
                plugin_name="test",
                input_schema=bad_schema,
                output_schema=_make_valid_output_schema(),
            )

    def test_invalid_plugin_name_with_special_chars(self):
        """Test that a plugin name with invalid characters raises ValueError."""
        with pytest.raises(ValueError, match="may only contain"):
            build_plugin_descriptor(
                graph_json=_make_valid_graph(),
                plugin_name="bad/plugin name!",
                input_schema="{}",
                output_schema="{}",
            )

    def test_empty_plugin_name(self):
        """Test that an empty plugin name raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            build_plugin_descriptor(
                graph_json=_make_valid_graph(),
                plugin_name="   ",
                input_schema="{}",
                output_schema="{}",
            )

    def test_graph_too_large(self):
        """Test that a graph exceeding max length raises ValueError."""
        large_graph = "x" * (MAX_GRAPH_JSON_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            build_plugin_descriptor(
                graph_json=large_graph,
                plugin_name="test",
                input_schema="{}",
                output_schema="{}",
            )

    def test_too_many_nodes(self):
        """Test that a graph with too many nodes raises ValueError."""
        nodes = [{"id": i, "type": "KSampler"} for i in range(MAX_NODE_COUNT + 1)]
        graph = {"nodes": nodes}
        with pytest.raises(ValueError, match="maximum allowed"):
            build_plugin_descriptor(
                graph_json=json.dumps(graph),
                plugin_name="test",
                input_schema="{}",
                output_schema="{}",
            )

    def test_deterministic_plugin_id(self):
        """Test that the same inputs produce the same plugin ID."""
        graph_json = _make_valid_graph()
        input_schema = _make_valid_input_schema()
        output_schema = _make_valid_output_schema()

        desc1 = build_plugin_descriptor(
            graph_json=graph_json,
            plugin_name="test",
            input_schema=input_schema,
            output_schema=output_schema,
        )
        desc2 = build_plugin_descriptor(
            graph_json=graph_json,
            plugin_name="test",
            input_schema=input_schema,
            output_schema=output_schema,
        )
        assert desc1["plugin_id"] == desc2["plugin_id"]

    def test_different_graphs_produce_different_ids(self):
        """Test that different graphs produce different plugin IDs."""
        graph1 = _make_valid_graph()
        graph2 = json.dumps({
            "nodes": [
                {"id": 1, "type": "KSampler"},
                {"id": 2, "type": "SaveImage"},
            ]
        })

        desc1 = build_plugin_descriptor(
            graph_json=graph1,
            plugin_name="test",
            input_schema="{}",
            output_schema="{}",
        )
        desc2 = build_plugin_descriptor(
            graph_json=graph2,
            plugin_name="test",
            input_schema="{}",
            output_schema="{}",
        )
        assert desc1["plugin_id"] != desc2["plugin_id"]

    def test_empty_schema_objects_are_valid(self):
        """Test that empty object schemas '{}' are accepted as valid."""
        graph_json = _make_valid_graph()
        descriptor = build_plugin_descriptor(
            graph_json=graph_json,
            plugin_name="test",
            input_schema="{}",
            output_schema="{}",
        )
        assert descriptor["input_schema"] == {}
        assert descriptor["output_schema"] == {}


class TestPSNWorkflowPluginExposerNode:
    """Tests for the PSN_Workflow_Plugin_Exposer node class."""

    def test_node_run_valid(self):
        """Test that the node run method returns correct outputs."""
        node = PSN_Workflow_Plugin_Exposer()
        descriptor, endpoint_url = node.run(
            graph_json=_make_valid_graph(),
            plugin_name="my_plugin",
            input_schema=_make_valid_input_schema(),
            output_schema=_make_valid_output_schema(),
        )
        assert isinstance(descriptor, dict)
        assert isinstance(endpoint_url, str)
        assert descriptor["plugin_name"] == "my_plugin"
        assert endpoint_url == descriptor["endpoint_url"]

    def test_node_run_invalid_graph(self):
        """Test that the node raises ValueError for invalid graph."""
        node = PSN_Workflow_Plugin_Exposer()
        with pytest.raises(ValueError):
            node.run(
                graph_json="invalid",
                plugin_name="test",
                input_schema="{}",
                output_schema="{}",
            )

    def test_node_input_types(self):
        """Test that INPUT_TYPES returns the expected structure."""
        input_types = PSN_Workflow_Plugin_Exposer.INPUT_TYPES()
        assert "required" in input_types
        assert "graph_json" in input_types["required"]
        assert "plugin_name" in input_types["required"]
        assert "input_schema" in input_types["required"]
        assert "output_schema" in input_types["required"]

    def test_node_return_types(self):
        """Test that RETURN_TYPES and RETURN_NAMES are correct."""
        assert PSN_Workflow_Plugin_Exposer.RETURN_TYPES == ("DICT", "STRING")
        assert PSN_Workflow_Plugin_Exposer.RETURN_NAMES == ("plugin_descriptor", "endpoint_url")
        assert PSN_Workflow_Plugin_Exposer.FUNCTION == "run"
        assert PSN_Workflow_Plugin_Exposer.CATEGORY == "ParametricStudio/Plugins"


class TestHelperFunctions:
    """Tests for individual helper functions."""

    def test_sanitize_plugin_name_valid(self):
        """Test valid plugin names are returned unchanged."""
        assert _sanitize_plugin_name("my_plugin") == "my_plugin"
        assert _sanitize_plugin_name("My-Plugin.v2") == "My-Plugin.v2"
        assert _sanitize_plugin_name("plugin_123") == "plugin_123"

    def test_sanitize_plugin_name_too_long(self):
        """Test that a plugin name exceeding 128 chars raises ValueError."""
        with pytest.raises(ValueError, match="must not exceed 128"):
            _sanitize_plugin_name("a" * 129)

    def test_validate_schema_invalid_type(self):
        """Test that a schema with unsupported type raises ValueError."""
        with pytest.raises(ValueError, match="unsupported type"):
            _validate_schema(json.dumps({"type": "unknown_type"}), "test_schema")

    def test_validate_schema_missing_type(self):
        """Test that a schema without 'type' key raises ValueError (non-empty)."""
        with pytest.raises(ValueError, match="must contain a 'type' key"):
            _validate_schema(json.dumps({"properties": {}}), "test_schema")

    def test_validate_schema_empty_object_is_valid(self):
        """Test that an empty object schema is accepted."""
        result = _validate_schema("{}", "test_schema")
        assert result == {}

    def test_generate_endpoint_url_format(self):
        """Test that the endpoint URL has the correct format."""
        url = _generate_endpoint_url("abc123")
        assert url == f"{SIMULATED_BASE_URL}/plugins/abc123"

    def test_extract_node_ids_string_and_int(self):
        """Test that node IDs can be strings or integers."""
        graph = {
            "nodes": [
                {"id": 1, "type": "KSampler"},
                {"id": "node_2", "type": "SaveImage"},
            ]
        }
        ids = _extract_node_ids(graph)
        assert ids == ["1", "node_2"]
