"""Tests for PSN_Attention_Style_Patch (pure-logic payload builder)."""

import json

from psn_nodes.gen.psn_attention_style_patch import (
    PSN_Attention_Style_Patch,
    _validate_vector,
    _validate_strength,
    _checksum,
)


def test_valid_payload_add():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run("[0.1, -0.2, 0.3]", 0.5, "add")
    assert valid is True
    assert reason == "ok"
    data = json.loads(payload)
    assert data["op"] == "add"
    assert data["vector"] == [0.1, -0.2, 0.3]
    assert data["strength"] == 0.5
    assert data["checksum"] == _checksum("add", [0.1, -0.2, 0.3], 0.5)


def test_valid_payload_scale_add_with_tag():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run("[1.0, 2.0]", 0.25, "scale_add", model_tag="dreamy")
    assert valid is True
    data = json.loads(payload)
    assert data["op"] == "scale_add"
    assert data["model_tag"] == "dreamy"
    assert data["strength"] == 0.25


def test_invalid_json_vector():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run("not json", 0.5, "add")
    assert valid is False
    assert payload == ""
    assert "not valid JSON" in reason


def test_vector_not_array():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run("1.0", 0.5, "add")
    assert valid is False
    assert "must be a JSON array" in reason


def test_vector_empty():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run("[]", 0.5, "add")
    assert valid is False
    assert "must not be empty" in reason


def test_vector_non_numeric_element():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run('[0.1, "x"]', 0.5, "add")
    assert valid is False
    assert "is not a number" in reason


def test_vector_bool_rejected():
    ok, vec, why = _validate_vector("[true]")
    assert ok is False
    assert "is not a number" in why


def test_vector_nan_rejected():
    ok, vec, why = _validate_vector("[0.1, NaN]")
    assert ok is False
    assert "NaN" in why


def test_strength_nan_rejected():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run("[0.1]", float("nan"), "add")
    assert valid is False
    assert "NaN" in reason


def test_strength_out_of_bounds():
    ok, val, why = _validate_strength(1e12)
    assert ok is False
    assert "out of bounds" in why


def test_op_not_in_allowlist():
    node = PSN_Attention_Style_Patch()
    payload, valid, reason = node.run("[0.1]", 0.5, "multiply")
    assert valid is False
    assert "allow-list" in reason


def test_checksum_deterministic():
    a = _checksum("add", [1.0, 2.0], 0.5)
    b = _checksum("add", [1.0, 2.0], 0.5)
    assert a == b
    c = _checksum("add", [1.0, 2.0], 0.6)
    assert a != c
