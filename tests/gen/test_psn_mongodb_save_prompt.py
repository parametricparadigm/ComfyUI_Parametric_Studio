"""Tests for psn_nodes.gen.psn_mongodb_save_prompt."""

import json
import pytest

from psn_nodes.gen.psn_mongodb_save_prompt import (
    PSN_MongoDB_Save_Prompt,
    _psn_validate_params,
    _psn_generate_doc_id,
    _psn_build_document,
)


def test_psn_validate_params_valid():
    ok, parsed, err = _psn_validate_params('{"steps": 20, "cfg": 7.5}')
    assert ok is True
    assert parsed == {"steps": 20, "cfg": 7.5}
    assert err == ""


def test_psn_validate_params_empty_string():
    ok, parsed, err = _psn_validate_params("")
    assert ok is False
    assert parsed is None
    assert "empty" in err


def test_psn_validate_params_invalid_json():
    ok, parsed, err = _psn_validate_params("{not valid json")
    assert ok is False
    assert parsed is None
    assert "invalid JSON" in err


def test_psn_validate_params_not_object():
    ok, parsed, err = _psn_validate_params("[1, 2, 3]")
    assert ok is False
    assert parsed is None
    assert "JSON object" in err


def test_psn_validate_params_unknown_key():
    ok, parsed, err = _psn_validate_params('{"hacker_key": true}')
    assert ok is False
    assert parsed is None
    assert "unknown param keys" in err


def test_psn_validate_params_non_string_input():
    ok, parsed, err = _psn_validate_params(12345)
    assert ok is False
    assert parsed is None
    assert "string" in err


def test_psn_generate_doc_id_deterministic():
    params = {"steps": 20}
    ts = 1700000000.0
    id1 = _psn_generate_doc_id("hello", params, ts)
    id2 = _psn_generate_doc_id("hello", params, ts)
    assert id1 == id2
    assert id1.startswith("psn_")
    assert len(id1) == 28  # "psn_" + 24 hex chars


def test_psn_generate_doc_id_differs_for_different_prompts():
    params = {"steps": 20}
    ts = 1700000000.0
    id1 = _psn_generate_doc_id("prompt A", params, ts)
    id2 = _psn_generate_doc_id("prompt B", params, ts)
    assert id1 != id2


def test_psn_build_document_structure():
    params = {"steps": 20, "cfg": 7.0}
    ts = 1700000000.0
    doc_id = "psn_test123"
    doc = _psn_build_document("my prompt", params, ts, doc_id)
    assert doc["_id"] == doc_id
    assert doc["prompt"] == "my prompt"
    assert doc["params"] == params
    assert doc["schema_version"] == 1
    assert doc["created_at"] == ts


def test_psn_node_run_success():
    node = PSN_MongoDB_Save_Prompt()
    doc_id, doc_json = node.run("a test prompt", '{"steps": 20}', timestamp=1700000000.0)
    assert doc_id.startswith("psn_")
    doc = json.loads(doc_json)
    assert doc["_id"] == doc_id
    assert doc["prompt"] == "a test prompt"
    assert doc["params"] == {"steps": 20}
    assert doc["created_at"] == 1700000000.0


def test_psn_node_run_invalid_params():
    node = PSN_MongoDB_Save_Prompt()
    doc_id, doc_json = node.run("prompt", "not json")
    assert doc_id == ""
    doc = json.loads(doc_json)
    assert "error" in doc


def test_psn_node_run_empty_prompt():
    node = PSN_MongoDB_Save_Prompt()
    doc_id, doc_json = node.run("", '{"steps": 20}', timestamp=1700000000.0)
    # Empty prompt is still a valid string; should succeed
    assert doc_id.startswith("psn_")
    doc = json.loads(doc_json)
    assert doc["prompt"] == ""


def test_psn_node_run_non_string_prompt():
    node = PSN_MongoDB_Save_Prompt()
    doc_id, doc_json = node.run(12345, '{"steps": 20}')
    assert doc_id == ""
    doc = json.loads(doc_json)
    assert "error" in doc
