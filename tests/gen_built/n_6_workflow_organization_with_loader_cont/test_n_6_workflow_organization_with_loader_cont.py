"""Tests for PSN_Workflow_Structure node."""

import torch
import json

from n_6_workflow_organization_with_loader_cont import (
    PSN_Workflow_Structure,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_loader,
    _validate_controller,
    _validate_sampler,
)


def test_module_mappings():
    """Test that module-level mappings exist and are correct."""
    assert "PSN_Workflow_Structure" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Workflow_Structure"] is PSN_Workflow_Structure
    assert "PSN_Workflow_Structure" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_Workflow_Structure"], str)


def test_input_types():
    """Test that INPUT_TYPES returns the expected structure."""
    it = PSN_Workflow_Structure.INPUT_TYPES()
    assert "required" in it
    assert "loader_output" in it["required"]
    assert "controller_settings" in it["required"]
    assert "sampler_input" in it["required"]
    assert it["required"]["loader_output"] == ("ANY",)
    assert it["required"]["controller_settings"] == ("DICT",)
    assert it["required"]["sampler_input"] == ("ANY",)
    assert "optional" in it
    assert "log_structure" in it["optional"]


def test_return_types():
    """Test RETURN_TYPES and RETURN_NAMES."""
    assert PSN_Workflow_Structure.RETURN_TYPES == ("DICT", "BOOLEAN")
    assert PSN_Workflow_Structure.RETURN_NAMES == ("structured_data", "validation_status")
    assert PSN_Workflow_Structure.FUNCTION == "run"
    assert PSN_Workflow_Structure.CATEGORY == "ParametricStudio/Workflow"


def test_valid_inputs_tensor():
    """Test with valid tensor inputs."""
    node = PSN_Workflow_Structure()
    loader = torch.randn(2, 4, 4, 3)  # small IMAGE-like tensor
    controller = {"steps": 20, "cfg": 7.5}
    sampler = torch.randn(2, 4, 4, 3)

    structured, valid = node.run(loader, controller, sampler)
    assert valid is True
    assert isinstance(structured, dict)
    assert structured["all_valid"] is True
    assert structured["structure"] == "Loader -> Controller -> Sampler"
    assert structured["loader"]["valid"] is True
    assert structured["controller"]["valid"] is True
    assert structured["sampler"]["valid"] is True
    # Verify data is passed through
    assert torch.equal(structured["loader"]["data"], loader)
    assert structured["controller"]["settings"] == controller
    assert torch.equal(structured["sampler"]["data"], sampler)


def test_valid_inputs_dict():
    """Test with dict inputs (e.g., LATENT dict)."""
    node = PSN_Workflow_Structure()
    latent = {"samples": torch.randn(1, 4, 8, 8)}
    controller = {"scheduler": "euler"}
    sampler = {"steps": 30}

    structured, valid = node.run(latent, controller, sampler)
    assert valid is True
    assert structured["all_valid"] is True
    assert structured["loader"]["data"] == latent
    assert structured["controller"]["settings"] == controller
    assert structured["sampler"]["data"] == sampler


def test_invalid_loader_none():
    """Test that None loader_output is invalid."""
    node = PSN_Workflow_Structure()
    controller = {"steps": 10}
    sampler = torch.randn(1, 2, 2, 3)

    structured, valid = node.run(None, controller, sampler)
    assert valid is False
    assert structured["all_valid"] is False
    assert structured["loader"]["valid"] is False
    assert "None" in structured["loader"]["info"]


def test_invalid_controller_type():
    """Test that non-dict controller_settings is invalid."""
    node = PSN_Workflow_Structure()
    loader = torch.randn(1, 2, 2, 3)
    sampler = torch.randn(1, 2, 2, 3)

    structured, valid = node.run(loader, "not_a_dict", sampler)
    assert valid is False
    assert structured["all_valid"] is False
    assert structured["controller"]["valid"] is False
    assert "dict" in structured["controller"]["info"]


def test_invalid_sampler_none():
    """Test that None sampler_input is invalid."""
    node = PSN_Workflow_Structure()
    loader = torch.randn(1, 2, 2, 3)
    controller = {"steps": 10}

    structured, valid = node.run(loader, controller, None)
    assert valid is False
    assert structured["all_valid"] is False
    assert structured["sampler"]["valid"] is False
    assert "None" in structured["sampler"]["info"]


def test_log_structure():
    """Test that log_structure=True adds a log field."""
    node = PSN_Workflow_Structure()
    loader = torch.randn(1, 2, 2, 3)
    controller = {"steps": 10}
    sampler = torch.randn(1, 2, 2, 3)

    structured, valid = node.run(loader, controller, sampler, log_structure=True)
    assert valid is True
    assert "log" in structured
    assert isinstance(structured["log"], str)
    assert "PSN_Workflow_Structure" in structured["log"]
    assert "OK" in structured["log"]


def test_log_structure_invalid():
    """Test log with invalid inputs shows FAIL."""
    node = PSN_Workflow_Structure()
    controller = {"steps": 10}
    sampler = torch.randn(1, 2, 2, 3)

    structured, valid = node.run(None, controller, sampler, log_structure=True)
    assert valid is False
    assert "log" in structured
    assert "FAIL" in structured["log"]


def test_controller_none_defaults():
    """Test that None controller_settings uses defaults."""
    node = PSN_Workflow_Structure()
    loader = torch.randn(1, 2, 2, 3)
    sampler = torch.randn(1, 2, 2, 3)

    structured, valid = node.run(loader, None, sampler)
    assert valid is True
    assert structured["controller"]["settings"] == {}
    assert structured["controller"]["valid"] is True


def test_no_in_place_modification():
    """Test that inputs are not modified in place."""
    node = PSN_Workflow_Structure()
    loader = torch.randn(2, 3, 3, 3)
    controller = {"steps": 20, "cfg": 7.5}
    sampler = torch.randn(2, 3, 3, 3)

    loader_copy = loader.clone()
    controller_copy = dict(controller)
    sampler_copy = sampler.clone()

    node.run(loader, controller, sampler)

    assert torch.equal(loader, loader_copy)
    assert controller == controller_copy
    assert torch.equal(sampler, sampler_copy)


def test_validate_functions_directly():
    """Test the validation helper functions directly."""
    # Loader validation
    ok, msg = _validate_loader(torch.randn(1, 2, 2, 3))
    assert ok is True
    ok, msg = _validate_loader(None)
    assert ok is False
    ok, msg = _validate_loader("hello")
    assert ok is True
    ok, msg = _validate_loader(42)
    assert ok is True

    # Controller validation
    ok, msg = _validate_controller({"a": 1})
    assert ok is True
    ok, msg = _validate_controller(None)
    assert ok is True
    ok, msg = _validate_controller("bad")
    assert ok is False
    ok, msg = _validate_controller(123)
    assert ok is False

    # Sampler validation
    ok, msg = _validate_sampler(torch.randn(1, 2, 2, 3))
    assert ok is True
    ok, msg = _validate_sampler(None)
    assert ok is False
    ok, msg = _validate_sampler([1, 2, 3])
    assert ok is True


def test_json_serializable_structure():
    """Test that the structure metadata (excluding tensor data) is JSON-serializable."""
    node = PSN_Workflow_Structure()
    loader = torch.randn(1, 2, 2, 3)
    controller = {"steps": 10}
    sampler = torch.randn(1, 2, 2, 3)

    structured, valid = node.run(loader, controller, sampler)
    # Extract just the metadata (no tensors)
    meta = {
        "structure": structured["structure"],
        "all_valid": structured["all_valid"],
        "loader_valid": structured["loader"]["valid"],
        "controller_valid": structured["controller"]["valid"],
        "sampler_valid": structured["sampler"]["valid"],
    }
    # This should not raise
    json.dumps(meta)


def main():
    test_module_mappings()
    test_input_types()
    test_return_types()
    test_valid_inputs_tensor()
    test_valid_inputs_dict()
    test_invalid_loader_none()
    test_invalid_controller_type()
    test_invalid_sampler_none()
    test_log_structure()
    test_log_structure_invalid()
    test_controller_none_defaults()
    test_no_in_place_modification()
    test_validate_functions_directly()
    test_json_serializable_structure()
    print("ok")


if __name__ == "__main__":
    main()
