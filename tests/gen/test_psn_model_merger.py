"""Tests for psn_nodes.gen.psn_model_merger."""

import json
import pytest

from psn_nodes.gen.psn_model_merger import (
    PSN_Merge_Checkpoints,
    PSN_Inspect_Model,
    merge_models,
    inspect_model,
    _parse_model,
    _lerp,
)


# --- Helper to build a model JSON string ---
def _model(layers):
    return json.dumps(layers)


# --- Tests for _parse_model ---

def test_parse_model_valid():
    m, err = _parse_model('{"conv1": [1.0, 2.0], "fc": [0.5]}')
    assert err is None
    assert m == {"conv1": [1.0, 2.0], "fc": [0.5]}


def test_parse_model_invalid_json():
    m, err = _parse_model("not json")
    assert m is None
    assert "invalid JSON" in err


def test_parse_model_not_dict():
    m, err = _parse_model("[1, 2, 3]")
    assert m is None
    assert "object" in err


def test_parse_model_non_numeric_weight():
    m, err = _parse_model('{"layer": [1.0, "bad"]}')
    assert m is None
    assert "numbers" in err


def test_parse_model_non_string_input():
    m, err = _parse_model(12345)
    assert m is None
    assert "JSON string" in err


# --- Tests for _lerp ---

def test_lerp_equal_lengths():
    result = _lerp([1.0, 2.0], [3.0, 4.0], 0.5, 0.5)
    assert result == [2.0, 3.0]


def test_lerp_different_lengths_zero_pad():
    result = _lerp([1.0], [3.0, 4.0], 0.5, 0.5)
    assert result == [2.0, 2.0]


def test_lerp_full_weight_a():
    result = _lerp([1.0, 2.0], [3.0, 4.0], 1.0, 0.0)
    assert result == [1.0, 2.0]


# --- Tests for merge_models ---

def test_merge_models_basic_average():
    model_a = _model({"conv1": [1.0, 2.0], "fc": [0.5]})
    model_b = _model({"conv1": [3.0, 4.0], "fc": [1.5]})
    merged, err = merge_models(model_a, model_b, 0.5, 0.5)
    assert err is None
    data = json.loads(merged)
    assert data["conv1"] == [2.0, 3.0]
    assert data["fc"] == [1.0]


def test_merge_models_disjoint_layers():
    model_a = _model({"layer_a": [1.0]})
    model_b = _model({"layer_b": [2.0]})
    merged, err = merge_models(model_a, model_b, 0.5, 0.5)
    assert err is None
    data = json.loads(merged)
    assert "layer_a" in data
    assert "layer_b" in data
    assert data["layer_a"] == [0.5]
    assert data["layer_b"] == [1.0]


def test_merge_models_invalid_input():
    merged, err = merge_models("bad json", "{}", 0.5, 0.5)
    assert merged is None
    assert "model_a" in err


def test_merge_models_bad_weight_type():
    merged, err = merge_models("{}", "{}", "not_a_number", 0.5)
    assert merged is None
    assert "weight_a" in err


# --- Tests for inspect_model ---

def test_inspect_model_basic():
    model = _model({"conv1": [1.0, 2.0, 3.0], "fc": [0.5, 0.6]})
    layer_names, param_count, err = inspect_model(model)
    assert err is None
    assert param_count == 5
    assert "conv1" in layer_names
    assert "fc" in layer_names


def test_inspect_model_empty():
    layer_names, param_count, err = inspect_model("{}")
    assert err is None
    assert param_count == 0
    assert layer_names == ""


def test_inspect_model_invalid():
    layer_names, param_count, err = inspect_model("not json")
    assert layer_names is None
    assert param_count == 0
    assert "invalid JSON" in err


# --- Tests for node classes ---

def test_psn_merge_checkpoints_node():
    node = PSN_Merge_Checkpoints()
    model_a = _model({"w": [1.0, 2.0]})
    model_b = _model({"w": [3.0, 4.0]})
    merged, error = node.run(model_a, model_b, 0.5, 0.5)
    assert error == ""
    data = json.loads(merged)
    assert data["w"] == [2.0, 3.0]


def test_psn_merge_checkpoints_node_error():
    node = PSN_Merge_Checkpoints()
    merged, error = node.run("bad", "{}", 0.5, 0.5)
    assert merged == "{}"
    assert "model_a" in error


def test_psn_inspect_model_node():
    node = PSN_Inspect_Model()
    model = _model({"a": [1.0, 2.0], "b": [3.0]})
    layer_names, param_count, error = node.run(model)
    assert error == ""
    assert param_count == 3
    assert "a" in layer_names
    assert "b" in layer_names


def test_psn_inspect_model_node_error():
    node = PSN_Inspect_Model()
    layer_names, param_count, error = node.run("invalid")
    assert layer_names == ""
    assert param_count == 0
    assert "invalid JSON" in error
