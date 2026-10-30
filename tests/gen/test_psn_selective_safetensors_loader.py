"""Tests for psn_nodes.gen.psn_selective_safetensors_loader (pure logic only)."""

import json

import pytest

from psn_nodes.gen.psn_selective_safetensors_loader import (
    PSN_SelectiveSafetensorsLoader,
    _build_load_plan,
    _parse_layer_spec,
    _parse_safetensors_header,
    _select_keys,
)


def _header(keys_shapes):
    """Build a minimal valid safetensors header JSON string."""
    data = {}
    for i, (name, shape) in enumerate(keys_shapes):
        data[name] = {"dtype": "F32", "shape": shape, "data_offsets": [i * 100, (i + 1) * 100]}
    return json.dumps(data)


def test_selective_load_selects_matching_prefixes():
    header = _header([("blocks.0.weight", [4, 4]), ("blocks.1.weight", [4, 4]), ("final.norm", [8])])
    plan = _build_load_plan(header, "blocks.0,blocks.1", "cpu")
    assert plan["selected_keys"] == ["blocks.0.weight", "blocks.1.weight"]
    assert plan["missing_keys"] == ["final.norm"]
    assert plan["device"] == "cpu"
    assert plan["selected_count"] == 2
    assert plan["missing_count"] == 1


def test_selective_load_exact_key_match():
    header = _header([("final.norm", [8]), ("blocks.0.weight", [4, 4])])
    plan = _build_load_plan(header, "final.norm", "cuda")
    assert plan["selected_keys"] == ["final.norm"]
    assert plan["missing_keys"] == ["blocks.0.weight"]


def test_selective_load_no_match_returns_all_missing():
    header = _header([("a.b", [1]), ("c.d", [1])])
    plan = _build_load_plan(header, "zzz", "cpu")
    assert plan["selected_keys"] == []
    assert plan["missing_keys"] == ["a.b", "c.d"]
    assert plan["selected_count"] == 0


def test_bad_device_rejected():
    header = _header([("a", [1])])
    with pytest.raises(ValueError):
        _build_load_plan(header, "a", "metal")


def test_empty_layers_rejected():
    header = _header([("a", [1])])
    with pytest.raises(ValueError):
        _build_load_plan(header, "  ,  ", "cpu")


def test_invalid_header_json_rejected():
    with pytest.raises(ValueError):
        _build_load_plan("{not json", "a", "cpu")


def test_header_entry_missing_offsets_rejected():
    bad = json.dumps({"a": {"dtype": "F32", "shape": [1]}})
    with pytest.raises(ValueError):
        _parse_safetensors_header(bad)


def test_layer_prefix_path_traversal_rejected():
    with pytest.raises(ValueError):
        _parse_layer_spec("..")


def test_node_run_returns_json_plan_and_missing():
    node = PSN_SelectiveSafetensorsLoader()
    header = _header([("blocks.0.weight", [4, 4]), ("final.norm", [8])])
    plan_json, missing, reason = node.run(
        path="/tmp/model.safetensors", header=header, layers="blocks.0", device="cpu")
    plan = json.loads(plan_json)
    assert plan["selected_keys"] == ["blocks.0.weight"]
    assert missing == "final.norm"
    assert reason.startswith("ok:")
    assert plan["path"] == "/tmp/model.safetensors"


def test_node_run_bad_input_returns_error_reason():
    node = PSN_SelectiveSafetensorsLoader()
    plan_json, missing, reason = node.run(
        path="x", header="{}", layers="", device="cpu")
    assert plan_json == "{}"
    assert missing == ""
    assert reason.startswith("error:")


def test_select_keys_sorted_deterministic():
    keys = ["z", "a", "m"]
    selected, missing = _select_keys(keys, ["a"])
    assert selected == ["a"]
    assert missing == ["m", "z"]


def test_max_keys_truncation():
    node = PSN_SelectiveSafetensorsLoader()
    header = _header([("k%d" % i, [1]) for i in range(10)])
    plan_json, _, _ = node.run(path="p", header=header, layers="k", device="cpu", max_keys=3)
    plan = json.loads(plan_json)
    assert plan.get("truncated") is True
    assert len(plan["selected_keys"]) <= 3
