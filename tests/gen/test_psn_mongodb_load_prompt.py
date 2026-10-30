"""Tests for psn_nodes.gen.psn_mongodb_load_prompt (pure logic, no I/O)."""

import json

from psn_nodes.gen.psn_mongodb_load_prompt import (
    PSN_MongoDB_Load_Prompt,
    _parse_db_session,
    _fetch_document,
    _extract_prompt,
    _extract_params,
)


def _node():
    return PSN_MongoDB_Load_Prompt()


def _session(docs):
    return json.dumps(docs)


def test_run_returns_prompt_and_params_when_found():
    docs = {"abc": {"prompt": "a cat", "params": {"steps": 20, "cfg": 7}}}
    prompt, params, found, reason = _node().run(_session(docs), "abc")
    assert found is True
    assert reason == "ok"
    assert prompt == "a cat"
    assert json.loads(params) == {"steps": 20, "cfg": 7}


def test_run_missing_document_reports_not_found():
    docs = {"abc": {"prompt": "x", "params": {}}}
    prompt, params, found, reason = _node().run(_session(docs), "nope")
    assert found is False
    assert prompt == ""
    assert params == ""
    assert "not found" in reason


def test_run_invalid_json_session_is_rejected():
    prompt, params, found, reason = _node().run("{not json", "abc")
    assert found is False
    assert "not valid JSON" in reason


def test_run_non_object_session_is_rejected():
    prompt, params, found, reason = _node().run("[1, 2, 3]", "abc")
    assert found is False
    assert "must be a JSON object" in reason


def test_run_empty_session_is_rejected():
    prompt, params, found, reason = _node().run("   ", "abc")
    assert found is False
    assert "empty" in reason


def test_run_non_string_doc_id_is_rejected():
    docs = {"abc": {"prompt": "x", "params": {}}}
    prompt, params, found, reason = _node().run(_session(docs), 123)
    assert found is False
    assert "doc_id must be a string" in reason


def test_run_non_string_prompt_is_coerced_to_string():
    docs = {"abc": {"prompt": 42, "params": {}}}
    prompt, params, found, reason = _node().run(_session(docs), "abc")
    assert found is True
    assert prompt == "42"


def test_run_non_dict_params_is_wrapped():
    docs = {"abc": {"prompt": "x", "params": "raw"}}
    prompt, params, found, reason = _node().run(_session(docs), "abc")
    assert found is True
    assert json.loads(params) == {"value": "raw"}


def test_run_missing_params_defaults_to_empty_object():
    docs = {"abc": {"prompt": "x"}}
    prompt, params, found, reason = _node().run(_session(docs), "abc")
    assert found is True
    assert json.loads(params) == {}


def test_parse_db_session_non_string_input():
    data, err = _parse_db_session(123)
    assert data is None
    assert err is not None


def test_fetch_document_non_dict_doc():
    data, err = _parse_db_session(json.dumps({"abc": "notadict"}))
    assert err is None
    doc, err = _fetch_document(data, "abc")
    assert doc is None
    assert "not an object" in err


def test_extract_params_serializes_deterministically():
    doc = {"params": {"b": 1, "a": 2}}
    out = _extract_params(doc)
    assert out == '{"a":2,"b":1}'


def test_node_metadata_is_well_formed():
    cls = PSN_MongoDB_Load_Prompt
    it = cls.INPUT_TYPES()
    assert "db_session" in it["required"]
    assert "doc_id" in it["required"]
    assert cls.RETURN_TYPES == ("STRING", "STRING", "BOOLEAN", "STRING")
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
