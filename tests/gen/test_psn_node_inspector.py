"""Tests for PSN_NodeInspector (psn_nodes.gen.psn_node_inspector)."""

import json

from psn_nodes.gen.psn_node_inspector import (
    PSN_NodeInspector,
    build_dot_graph,
    build_tree_string,
    _parse_graph,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _node(node_id, node_type, inputs=None):
    node = {"type": node_type}
    if inputs is not None:
        node["inputs"] = inputs
    return node


def test_tree_structure_matches_input_graph():
    graph = {
        "1": _node("1", "LoadImage", {"image": ["2", 0]}),
        "2": _node("2", "KSampler", {}),
    }
    graph_json = json.dumps(graph)
    node = PSN_NodeInspector()
    tree, dot = node.run(graph_json)
    assert "Node Graph (2 nodes)" in tree
    assert "[1] LoadImage" in tree
    assert "[2] KSampler" in tree
    assert "image <- 2" in tree
    assert "(no inputs)" in tree
    assert "digraph ComfyUI" in dot
    # Edge goes from source (2) to consumer (1)
    assert '"2" -> "1" [label="image"];' in dot


def test_empty_graph_object():
    node = PSN_NodeInspector()
    tree, dot = node.run("{}")
    assert "Node Graph (0 nodes)" in tree
    assert "digraph ComfyUI" in dot
    assert tree.strip() == "Node Graph (0 nodes)"


def test_invalid_json_returns_error():
    node = PSN_NodeInspector()
    tree, dot = node.run("{not valid json")
    assert tree.startswith("ERROR:")
    assert "invalid JSON" in tree
    assert "digraph ComfyUI" in dot
    assert "ERROR" in dot


def test_non_dict_json_rejected():
    node = PSN_NodeInspector()
    tree, dot = node.run("[1, 2, 3]")
    assert tree.startswith("ERROR:")
    assert "must be an object" in tree


def test_non_string_input_rejected():
    node = PSN_NodeInspector()
    tree, dot = node.run(12345)
    assert tree.startswith("ERROR:")
    assert "must be a string" in tree


def test_node_not_object_rejected():
    graph = {"1": "not a dict"}
    node = PSN_NodeInspector()
    tree, dot = node.run(json.dumps(graph))
    assert tree.startswith("ERROR:")
    assert "must be an object" in tree


def test_inputs_with_non_list_ref_ignored():
    graph = {
        "1": _node("1", "A", {"x": "not-a-list", "y": ["2", 0]}),
        "2": _node("2", "B", {}),
    }
    node = PSN_NodeInspector()
    tree, dot = node.run(json.dumps(graph))
    assert "y <- 2" in tree
    assert "x <-" not in tree
    assert '"2" -> "1" [label="y"];' in dot
    assert '[label="x"]' not in dot


def test_large_graph_exceeds_cap():
    graph = {str(i): _node(str(i), "N%d" % i, {}) for i in range(6000)}
    node = PSN_NodeInspector()
    tree, dot = node.run(json.dumps(graph))
    assert tree.startswith("ERROR:")
    assert "too large" in tree


def test_node_label_fallback_and_quoting():
    graph = {
        "1": {"class_type": "My\"Node"},
        "2": {},
    }
    node = PSN_NodeInspector()
    tree, dot = node.run(json.dumps(graph))
    assert "My\"Node" in tree
    assert "node" in tree  # node 2 has no label fields
    assert 'label="My\\"Node"' in dot


def test_module_mappings_present():
    assert "PSN_NodeInspector" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_NodeInspector"] is PSN_NodeInspector
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_NodeInspector"] == "PSN Node Inspector"
