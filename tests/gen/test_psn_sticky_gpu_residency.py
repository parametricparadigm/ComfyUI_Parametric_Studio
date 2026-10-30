"""
Tests for psn_nodes.gen.psn_sticky_gpu_residency
"""

import json
import pytest

from psn_nodes.gen.psn_sticky_gpu_residency import (
    PSN_Sticky_GPU_Residency,
    compute_residency_policy,
    _validate_priority,
    _parse_weight_map,
    _validate_device,
)


def test_sticky_true_keeps_cuda_tensors():
    """When sticky=True, all CUDA tensors stay on GPU regardless of priority."""
    weight_map = {
        "layer1.weight": "cuda:0",
        "layer2.bias": "cuda:1",
        "embed.weight": "cpu",
    }
    new_map, offloaded, kept, reason = compute_residency_policy(
        sticky=True, priority=0, weight_map=weight_map
    )
    assert new_map["layer1.weight"] == "cuda:0"
    assert new_map["layer2.bias"] == "cuda:1"
    assert new_map["embed.weight"] == "cpu"
    assert offloaded == []
    assert "layer1.weight" in kept
    assert "layer2.bias" in kept
    assert "embed.weight" in kept
    assert "sticky=True" in reason


def test_sticky_false_low_priority_offloads():
    """When sticky=False and priority < 5, CUDA tensors are offloaded to CPU."""
    weight_map = {
        "a.weight": "cuda:0",
        "b.bias": "cuda:2",
    }
    new_map, offloaded, kept, reason = compute_residency_policy(
        sticky=False, priority=3, weight_map=weight_map
    )
    assert new_map["a.weight"] == "cpu"
    assert new_map["b.bias"] == "cpu"
    assert offloaded == ["a.weight", "b.bias"]
    assert kept == []
    assert "priority=3" in reason


def test_sticky_false_high_priority_keeps():
    """When sticky=False and priority >= 5, CUDA tensors stay on GPU."""
    weight_map = {
        "c.weight": "cuda:0",
        "d.bias": "cuda:1",
    }
    new_map, offloaded, kept, reason = compute_residency_policy(
        sticky=False, priority=7, weight_map=weight_map
    )
    assert new_map["c.weight"] == "cuda:0"
    assert new_map["d.bias"] == "cuda:1"
    assert offloaded == []
    assert "c.weight" in kept
    assert "d.bias" in kept


def test_priority_boundary_values():
    """Priority 0 and 10 are valid; 4 offloads, 5 keeps when sticky=False."""
    wm = {"t": "cuda:0"}
    # priority=4 -> offload
    nm, off, _, _ = compute_residency_policy(False, 4, wm)
    assert nm["t"] == "cpu"
    assert off == ["t"]
    # priority=5 -> keep
    nm, off, _, _ = compute_residency_policy(False, 5, wm)
    assert nm["t"] == "cuda:0"
    assert off == []
    # priority=0 -> offload
    nm, off, _, _ = compute_residency_policy(False, 0, wm)
    assert nm["t"] == "cpu"
    # priority=10 -> keep
    nm, off, _, _ = compute_residency_policy(False, 10, wm)
    assert nm["t"] == "cuda:0"


def test_invalid_priority_rejected():
    """Priority outside [0,10] or non-int is rejected."""
    ok, err = _validate_priority(11)
    assert not ok
    assert "between" in err

    ok, err = _validate_priority(-1)
    assert not ok

    ok, err = _validate_priority(3.5)
    assert not ok
    assert "integer" in err

    ok, err = _validate_priority(True)
    assert not ok  # bool is subclass of int but should be rejected


def test_invalid_weight_map_json():
    """Malformed JSON or wrong types in weight_map are rejected."""
    # Not a string
    _, err = _parse_weight_map(12345)
    assert "JSON string" in err

    # Invalid JSON
    _, err = _parse_weight_map("{bad json")
    assert "invalid JSON" in err

    # Not a dict
    _, err = _parse_weight_map("[1,2,3]")
    assert "object" in err

    # Invalid device
    _, err = _parse_weight_map('{"w": "gpu:0"}')
    assert "device" in err

    # Empty tensor name
    _, err = _parse_weight_map('{"": "cpu"}')
    assert "non-empty" in err


def test_node_run_sticky_true():
    """End-to-end node run with sticky=True."""
    node = PSN_Sticky_GPU_Residency()
    wm = json.dumps({"net.0.weight": "cuda:0", "net.1.bias": "cpu"})
    new_map_str, offloaded_str, kept_str, reason = node.run(
        sticky=True, priority=2, weight_map=wm
    )
    new_map = json.loads(new_map_str)
    offloaded = json.loads(offloaded_str)
    kept = json.loads(kept_str)
    assert new_map["net.0.weight"] == "cuda:0"
    assert new_map["net.1.bias"] == "cpu"
    assert offloaded == []
    assert "net.0.weight" in kept
    assert "sticky=True" in reason


def test_node_run_invalid_priority():
    """Node returns error reason when priority is out of range."""
    node = PSN_Sticky_GPU_Residency()
    wm = json.dumps({"w": "cuda:0"})
    new_map_str, offloaded_str, kept_str, reason = node.run(
        sticky=True, priority=99, weight_map=wm
    )
    assert reason.startswith("ERROR")
    assert "priority" in reason


def test_node_run_invalid_weight_map():
    """Node returns error reason when weight_map is malformed."""
    node = PSN_Sticky_GPU_Residency()
    new_map_str, offloaded_str, kept_str, reason = node.run(
        sticky=True, priority=5, weight_map="not json at all"
    )
    assert reason.startswith("ERROR")
    assert "JSON" in reason


def test_empty_weight_map():
    """Empty weight map produces empty outputs without error."""
    new_map, offloaded, kept, reason = compute_residency_policy(
        sticky=True, priority=5, weight_map={}
    )
    assert new_map == {}
    assert offloaded == []
    assert kept == []
