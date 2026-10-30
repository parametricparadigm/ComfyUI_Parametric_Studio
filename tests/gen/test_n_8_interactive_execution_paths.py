"""Tests for psn_nodes.gen.n_8_interactive_execution_paths."""

import pytest

from psn_nodes.gen.n_8_interactive_execution_paths import (
    PSN_PathSelector,
    PSN_PathRouter,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_selector_valid_path():
    node = PSN_PathSelector()
    selected, is_valid, reason = node.run("Draft", '["Draft", "High-Quality"]')
    assert selected == "Draft"
    assert is_valid is True
    assert "allow-list" in reason


def test_selector_high_quality_path():
    node = PSN_PathSelector()
    selected, is_valid, reason = node.run("High-Quality", '["Draft", "High-Quality"]')
    assert selected == "High-Quality"
    assert is_valid is True


def test_selector_invalid_path_defaults_to_first():
    node = PSN_PathSelector()
    selected, is_valid, reason = node.run("Nonexistent", '["Draft", "High-Quality"]')
    assert selected == "Draft"
    assert is_valid is False
    assert "defaulted" in reason


def test_selector_empty_options_fails():
    node = PSN_PathSelector()
    selected, is_valid, reason = node.run("Draft", "[]")
    assert selected == ""
    assert is_valid is False
    assert "empty" in reason


def test_selector_invalid_json_options():
    node = PSN_PathSelector()
    selected, is_valid, reason = node.run("Draft", "not json")
    assert selected == ""
    assert is_valid is False
    assert "not valid JSON" in reason


def test_selector_options_not_a_list():
    node = PSN_PathSelector()
    selected, is_valid, reason = node.run("Draft", '{"a": 1}')
    assert selected == ""
    assert is_valid is False
    assert "must be a list" in reason


def test_router_routes_draft():
    node = PSN_PathRouter()
    node_id, data, routed, reason = node.run(
        "Draft", '{"Draft": "node_draft", "High-Quality": "node_hq"}', "payload"
    )
    assert node_id == "node_draft"
    assert data == "payload"
    assert routed is True
    assert "node_draft" in reason


def test_router_routes_high_quality():
    node = PSN_PathRouter()
    node_id, data, routed, reason = node.run(
        "High-Quality", '{"Draft": "node_draft", "High-Quality": "node_hq"}', "payload"
    )
    assert node_id == "node_hq"
    assert data == "payload"
    assert routed is True


def test_router_unknown_path_fails():
    node = PSN_PathRouter()
    node_id, data, routed, reason = node.run(
        "Unknown", '{"Draft": "node_draft"}', "payload"
    )
    assert node_id == ""
    assert routed is False
    assert "not found" in reason


def test_router_empty_selected_path_fails():
    node = PSN_PathRouter()
    node_id, data, routed, reason = node.run(
        "", '{"Draft": "node_draft"}', "payload"
    )
    assert routed is False
    assert "empty" in reason


def test_router_invalid_json_path_map():
    node = PSN_PathRouter()
    node_id, data, routed, reason = node.run(
        "Draft", "not json", "payload"
    )
    assert routed is False
    assert "not valid JSON" in reason


def test_router_path_map_not_a_dict():
    node = PSN_PathRouter()
    node_id, data, routed, reason = node.run(
        "Draft", '["a", "b"]', "payload"
    )
    assert routed is False
    assert "must be an object" in reason


def test_router_empty_path_map_fails():
    node = PSN_PathRouter()
    node_id, data, routed, reason = node.run(
        "Draft", "{}", "payload"
    )
    assert routed is False
    assert "empty" in reason


def test_node_mappings_present():
    assert "PSN_PathSelector" in NODE_CLASS_MAPPINGS
    assert "PSN_PathRouter" in NODE_CLASS_MAPPINGS
    assert "PSN_PathSelector" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_PathRouter" in NODE_DISPLAY_NAME_MAPPINGS


def test_selector_input_types_structure():
    it = PSN_PathSelector.INPUT_TYPES()
    assert "required" in it
    assert "path_name" in it["required"]
    assert "options" in it["required"]


def test_router_input_types_structure():
    it = PSN_PathRouter.INPUT_TYPES()
    assert "required" in it
    assert "selected_path" in it["required"]
    assert "path_map" in it["required"]
    assert "optional" in it
    assert "value" in it["optional"]
