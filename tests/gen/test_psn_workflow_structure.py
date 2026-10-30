"""Tests for PSN_WorkflowStructure node."""

import pytest
from psn_nodes.gen.psn_workflow_structure import PSN_WorkflowStructure


def test_valid_structure_returns_organized_dict():
    """Test that valid inputs produce a correctly organized dictionary."""
    node = PSN_WorkflowStructure()
    loader_out = {"model": "test_model"}
    controller_cfg = {"steps": 20, "cfg": 7.5}
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is True
    assert structured_data["loader"] == loader_out
    assert structured_data["controller"] == controller_cfg
    assert structured_data["sampler"] == sampler_in


def test_invalid_controller_settings_returns_false():
    """Test that non-dict controller_settings results in validation failure."""
    node = PSN_WorkflowStructure()
    loader_out = {"model": "test_model"}
    controller_cfg = "not_a_dict"  # Invalid: should be a dict
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is False
    assert structured_data == {}


def test_none_loader_output_returns_false():
    """Test that None loader_output results in validation failure."""
    node = PSN_WorkflowStructure()
    loader_out = None  # Invalid: should not be None
    controller_cfg = {"steps": 20}
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is False
    assert structured_data == {}


def test_none_sampler_input_returns_false():
    """Test that None sampler_input results in validation failure."""
    node = PSN_WorkflowStructure()
    loader_out = {"model": "test_model"}
    controller_cfg = {"steps": 20}
    sampler_in = None  # Invalid: should not be None

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is False
    assert structured_data == {}


def test_log_structure_includes_summary():
    """Test that log_structure=True includes a structure summary in the output."""
    node = PSN_WorkflowStructure()
    loader_out = {"model": "test_model"}
    controller_cfg = {"steps": 20, "cfg": 7.5}
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in, log_structure=True)

    assert validation_status is True
    assert "structure_summary" in structured_data
    # Verify the summary is valid JSON
    import json
    summary = json.loads(structured_data["structure_summary"])
    assert summary["loader_type"] == "dict"
    assert set(summary["controller_keys"]) == {"steps", "cfg"}
    assert summary["sampler_type"] == "str"


def test_empty_controller_settings_is_valid():
    """Test that an empty dict for controller_settings is still valid."""
    node = PSN_WorkflowStructure()
    loader_out = {"model": "test_model"}
    controller_cfg = {}  # Empty dict is still a valid dict
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is True
    assert structured_data["controller"] == {}


def test_complex_nested_data_preserved():
    """Test that complex nested data structures are preserved correctly."""
    node = PSN_WorkflowStructure()
    loader_out = {"model": "test", "config": {"nested": {"deep": [1, 2, 3]}}}
    controller_cfg = {"steps": 20, "advanced": {"param": True}}
    sampler_in = {"prompt": "test", "negative": "bad"}

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is True
    assert structured_data["loader"] == loader_out
    assert structured_data["controller"] == controller_cfg
    assert structured_data["sampler"] == sampler_in
