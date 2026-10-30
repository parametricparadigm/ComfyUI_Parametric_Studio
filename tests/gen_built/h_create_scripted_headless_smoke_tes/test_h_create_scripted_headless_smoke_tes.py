"""Tests for h_create_scripted_headless_smoke_tes."""

import json
import torch

from h_create_scripted_headless_smoke_tes import (
    PSN_SmokeTestWorkflow,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    run_smoke_test,
)


def _make_image(h=4, w=4, c=3, val=0.5):
    return torch.full((1, h, w, c), val, dtype=torch.float32)


def test_node_class_mappings():
    """Module-level mappings exist and are consistent."""
    assert "PSN_SmokeTestWorkflow" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_SmokeTestWorkflow"] is PSN_SmokeTestWorkflow
    assert "PSN_SmokeTestWorkflow" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_SmokeTestWorkflow"], str)


def test_input_types():
    """INPUT_TYPES returns the expected structure."""
    it = PSN_SmokeTestWorkflow.INPUT_TYPES()
    assert "required" in it
    assert "workflow_json" in it["required"]
    assert "image" in it["required"]
    assert it["required"]["image"] == ("IMAGE",)
    assert PSN_SmokeTestWorkflow.RETURN_TYPES == ("STRING", "STRING", "IMAGE")
    assert PSN_SmokeTestWorkflow.FUNCTION == "run"
    assert PSN_SmokeTestWorkflow.CATEGORY.startswith("ParametricStudio/")


def test_pass_identity():
    """A simple identity workflow with valid expectations should PASS."""
    img = _make_image(val=0.5)
    wf = {
        "steps": [
            {"id": "s1", "op": "identity", "inputs": {"a": "img"},
             "expect": {"min": 0.0, "max": 1.0, "mean": 0.5, "tol": 1e-4}}
        ],
        "inputs": {"img": "img"},
    }
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "PASS", "expected PASS, got %s; report: %s" % (result, report)
    assert out.shape == img.shape
    assert torch.allclose(out, img)


def test_fail_mean_mismatch():
    """If the mean expectation is wrong, the test should FAIL."""
    img = _make_image(val=0.5)
    wf = {
        "steps": [
            {"id": "s1", "op": "identity", "inputs": {"a": "img"},
             "expect": {"mean": 0.9, "tol": 1e-4}}
        ],
        "inputs": {"img": "img"},
    }
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "FAIL", "expected FAIL, got %s" % result
    assert "mean check failed" in report


def test_scale_and_add():
    """Multi-step workflow with scale and add ops."""
    img = _make_image(val=0.25)
    wf = {
        "steps": [
            {"id": "s1", "op": "scale", "inputs": {"a": "img", "k": 2.0},
             "expect": {"mean": 0.5, "tol": 1e-4}},
            {"id": "s2", "op": "add", "inputs": {"a": "s1", "b": "img"},
             "expect": {"mean": 0.75, "tol": 1e-4}},
        ],
        "inputs": {"img": "img"},
    }
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "PASS", "expected PASS, got %s; report: %s" % (result, report)
    assert torch.allclose(out, torch.full_like(img, 0.75))


def test_threshold():
    """Threshold op: values above t become 1, below become 0."""
    img = torch.zeros(1, 2, 2, 1, dtype=torch.float32)
    img[0, 0, 0, 0] = 0.8
    img[0, 0, 1, 0] = 0.3
    img[0, 1, 0, 0] = 0.6
    img[0, 1, 1, 0] = 0.1
    wf = {
        "steps": [
            {"id": "s1", "op": "threshold", "inputs": {"a": "img", "t": 0.5},
             "expect": {"min": 0.0, "max": 1.0, "mean": 0.5, "tol": 1e-4}}
        ],
        "inputs": {"img": "img"},
    }
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "PASS", "expected PASS, got %s; report: %s" % (result, report)
    expected = torch.tensor([[[[1.0], [0.0]], [[1.0], [0.0]]]], dtype=torch.float32)
    assert torch.allclose(out, expected)


def test_bad_json():
    """Invalid JSON should return FAIL with an error message."""
    img = _make_image()
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run("not valid json {{{", img)
    assert result == "FAIL"
    assert "invalid workflow JSON" in report


def test_empty_steps():
    """Workflow with no steps should FAIL."""
    img = _make_image()
    wf = {"steps": [], "inputs": {"img": "img"}}
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "FAIL"
    assert "non-empty" in report


def test_missing_input_tensor():
    """Referencing an input tensor that was not provided should FAIL."""
    img = _make_image()
    wf = {
        "steps": [
            {"id": "s1", "op": "identity", "inputs": {"a": "img"}, "expect": {}}
        ],
        "inputs": {"img": "nonexistent_key"},
    }
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "FAIL"
    assert "not provided" in report


def test_unknown_op():
    """An unknown op should cause a step FAIL."""
    img = _make_image()
    wf = {
        "steps": [
            {"id": "s1", "op": "frobnicate", "inputs": {"a": "img"}, "expect": {}}
        ],
        "inputs": {"img": "img"},
    }
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "FAIL"
    assert "unknown op" in report


def test_no_in_place_modification():
    """The input tensor must not be modified by the node."""
    img = _make_image(val=0.5)
    original = img.clone()
    wf = {
        "steps": [
            {"id": "s1", "op": "scale", "inputs": {"a": "img", "k": 3.0}, "expect": {}}
        ],
        "inputs": {"img": "img"},
    }
    node = PSN_SmokeTestWorkflow()
    node.run(json.dumps(wf), img)
    assert torch.allclose(img, original), "input tensor was modified in place!"


def test_mean_op():
    """Mean op: spatial mean broadcast back to original shape."""
    img = torch.zeros(1, 2, 2, 1, dtype=torch.float32)
    img[0, 0, 0, 0] = 0.2
    img[0, 0, 1, 0] = 0.4
    img[0, 1, 0, 0] = 0.6
    img[0, 1, 1, 0] = 0.8
    wf = {
        "steps": [
            {"id": "s1", "op": "mean", "inputs": {"a": "img"},
             "expect": {"mean": 0.5, "tol": 1e-4}}
        ],
        "inputs": {"img": "img"},
    }
    node = PSN_SmokeTestWorkflow()
    result, report, out = node.run(json.dumps(wf), img)
    assert result == "PASS", "expected PASS, got %s; report: %s" % (result, report)
    assert torch.allclose(out, torch.full_like(img, 0.5))


def test_run_smoke_test_direct():
    """Call the core engine directly (not through the node)."""
    img = _make_image(val=0.3)
    wf = {
        "steps": [
            {"id": "s1", "op": "identity", "inputs": {"a": "img"},
             "expect": {"min": 0.0, "max": 1.0}}
        ],
        "inputs": {"img": "img"},
    }
    passed, report, last_out = run_smoke_test(wf, {"img": img})
    assert passed is True
    assert last_out is not None
    assert torch.allclose(last_out, img)


def test_non_dict_workflow():
    """Passing a non-dict workflow should FAIL gracefully."""
    passed, report, last_out = run_smoke_test([1, 2, 3], {})
    assert passed is False
    assert "must be a dict" in report
    assert last_out is None


if __name__ == "__main__":
    test_node_class_mappings()
    test_input_types()
    test_pass_identity()
    test_fail_mean_mismatch()
    test_scale_and_add()
    test_threshold()
    test_bad_json()
    test_empty_steps()
    test_missing_input_tensor()
    test_unknown_op()
    test_no_in_place_modification()
    test_mean_op()
    test_run_smoke_test_direct()
    test_non_dict_workflow()
    print("ok")
