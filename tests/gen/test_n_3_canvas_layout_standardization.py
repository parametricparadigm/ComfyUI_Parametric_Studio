"""Tests for psn_nodes.gen.n_3_canvas_layout_standardization."""

import json

import pytest

from psn_nodes.gen.n_3_canvas_layout_standardization import (
    PSN_LayoutEnforcer,
    PSN_WirelessRouter,
    _build_layout_config,
    _route_wireless,
    _is_valid_id,
    THEMES,
    GROUPING_RULES,
)


def _ten_nodes():
    """A graph of 10 nodes with mixed types/functions."""
    return [
        {"id": "n01", "type": "Model", "function": "Input"},
        {"id": "n02", "type": "Model", "function": "Input"},
        {"id": "n03", "type": "Conditioning", "function": "Process"},
        {"id": "n04", "type": "Conditioning", "function": "Process"},
        {"id": "n05", "type": "Latent", "function": "Process"},
        {"id": "n06", "type": "Sampler", "function": "Process"},
        {"id": "n07", "type": "Sampler", "function": "Process"},
        {"id": "n08", "type": "Decode", "function": "Output"},
        {"id": "n09", "type": "Decode", "function": "Output"},
        {"id": "n10", "type": "Other", "function": "Other"},
    ]


def test_layout_enforcer_groups_by_type():
    node = PSN_LayoutEnforcer()
    (config,) = node.run(
        graph_id="graph_1",
        theme="Dark",
        grouping_rule="By Type",
        nodes=_ten_nodes(),
    )
    assert config["graph_id"] == "graph_1"
    assert config["theme"] == "Dark"
    assert config["grouping_rule"] == "By Type"
    assert config["node_count"] == 10
    assert config["wireless_routing"] is True
    # Grouped by type.
    assert config["groups"]["Model"] == ["n01", "n02"]
    assert config["groups"]["Conditioning"] == ["n03", "n04"]
    assert config["groups"]["Sampler"] == ["n06", "n07"]
    assert config["groups"]["Decode"] == ["n08", "n09"]
    assert config["groups"]["Other"] == ["n10"]
    # Config must be JSON-serializable (frontend payload).
    json.dumps(config)


def test_layout_enforcer_groups_by_function():
    node = PSN_LayoutEnforcer()
    (config,) = node.run(
        graph_id="graph_2",
        theme="Studio",
        grouping_rule="By Function",
        nodes=_ten_nodes(),
    )
    assert config["grouping_rule"] == "By Function"
    assert config["groups"]["Input"] == ["n01", "n02"]
    assert config["groups"]["Process"] == ["n03", "n04", "n05", "n06", "n07"]
    assert config["groups"]["Output"] == ["n08", "n09"]
    assert config["groups"]["Other"] == ["n10"]


def test_layout_enforcer_accepts_plain_string_ids():
    node = PSN_LayoutEnforcer()
    (config,) = node.run(
        graph_id="g",
        theme="Light",
        grouping_rule="By Type",
        nodes=["a", "b", "c"],
    )
    # Plain strings default to type/function "Other".
    assert config["groups"]["Other"] == ["a", "b", "c"]
    assert config["node_count"] == 3


def test_layout_enforcer_rejects_bad_theme():
    node = PSN_LayoutEnforcer()
    with pytest.raises(ValueError):
        node.run(graph_id="g", theme="Neon", grouping_rule="By Type", nodes=[])


def test_layout_enforcer_rejects_bad_grouping_rule():
    node = PSN_LayoutEnforcer()
    with pytest.raises(ValueError):
        node.run(graph_id="g", theme="Dark", grouping_rule="By Color", nodes=[])


def test_layout_enforcer_rejects_bad_graph_id():
    node = PSN_LayoutEnforcer()
    # Id starting with a digit is invalid.
    with pytest.raises(ValueError):
        node.run(graph_id="1graph", theme="Dark", grouping_rule="By Type", nodes=[])


def test_layout_enforcer_rejects_bad_node_id_in_list():
    node = PSN_LayoutEnforcer()
    with pytest.raises(ValueError):
        node.run(
            graph_id="g",
            theme="Dark",
            grouping_rule="By Type",
            nodes=["ok", "9bad"],
        )


def test_wireless_router_passes_data_wirelessly():
    node = PSN_WirelessRouter()
    (routed,) = node.run(
        source_node_id="src",
        target_node_id="dst",
        wireless=True,
        payload="hello",
    )
    assert routed["source"] == "src"
    assert routed["target"] == "dst"
    assert routed["wireless"] is True
    assert routed["visual_wire"] is False
    assert routed["data"] == "hello"


def test_wireless_router_wired_connection():
    node = PSN_WirelessRouter()
    (routed,) = node.run(
        source_node_id="a",
        target_node_id="b",
        wireless=False,
        payload=None,
    )
    assert routed["wireless"] is False
    assert routed["visual_wire"] is True
    assert routed["data"] is None


def test_wireless_router_rejects_bad_source_id():
    node = PSN_WirelessRouter()
    with pytest.raises(ValueError):
        node.run(source_node_id="1bad", target_node_id="ok", wireless=True)


def test_wireless_router_rejects_non_bool_wireless():
    node = PSN_WirelessRouter()
    with pytest.raises(ValueError):
        node.run(source_node_id="a", target_node_id="b", wireless="yes")


def test_is_valid_id_edge_cases():
    assert _is_valid_id("abc") is True
    assert _is_valid_id("A1_-") is True
    assert _is_valid_id("") is False
    assert _is_valid_id("1abc") is False
    assert _is_valid_id("has space") is False
    assert _is_valid_id(123) is False


def test_build_layout_config_empty_graph():
    config = _build_layout_config("g", "Dark", "By Type", [])
    assert config["node_count"] == 0
    assert config["groups"] == {}
    json.dumps(config)
