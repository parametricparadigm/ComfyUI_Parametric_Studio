"""Tests for PSN_LLM_Offloader pure-logic node."""

import json
import time

from psn_nodes.gen.psn_llm_offloader import (
    PSN_LLM_Offloader,
    _build_payload,
    _parse_response,
    _rate_limit_ok,
    _validate_target,
)


def test_validate_target_ram():
    assert _validate_target("RAM") is True


def test_validate_target_disk():
    assert _validate_target("DISK") is True


def test_validate_target_invalid():
    assert _validate_target("GPU") is False
    assert _validate_target("") is False
    assert _validate_target(None) is False


def test_build_payload_ram():
    payload_str = _build_payload("RAM", "my-model")
    data = json.loads(payload_str)
    assert data["action"] == "swap_to_cpu"
    assert data["model"] == "my-model"


def test_build_payload_disk():
    payload_str = _build_payload("DISK", "my-model")
    data = json.loads(payload_str)
    assert data["action"] == "terminate"
    assert data["model"] == "my-model"


def test_parse_response_success_ram():
    resp = json.dumps({"success": True, "freed_vram_gb": 4.5})
    status, freed = _parse_response(resp, "RAM")
    assert status == "OFFLOADED"
    assert freed == 4.5


def test_parse_response_failure():
    resp = json.dumps({"success": False, "error": "model not loaded"})
    status, freed = _parse_response(resp, "RAM")
    assert status == "FAILED"
    assert freed == 0.0


def test_parse_response_invalid_json():
    status, freed = _parse_response("not json", "RAM")
    assert status == "FAILED"
    assert freed == 0.0


def test_parse_response_non_dict():
    status, freed = _parse_response("[1,2,3]", "RAM")
    assert status == "FAILED"
    assert freed == 0.0


def test_rate_limit_ok_first_call():
    assert _rate_limit_ok(None) is True


def test_rate_limit_ok_recent_trigger():
    now = time.time()
    last = now - 0.5  # 0.5s ago, less than 2s limit
    assert _rate_limit_ok(last, now) is False


def test_rate_limit_ok_old_trigger():
    now = time.time()
    last = now - 3.0  # 3s ago, more than 2s limit
    assert _rate_limit_ok(last, now) is True


def test_node_no_trigger():
    node = PSN_LLM_Offloader()
    status, freed, payload = node.run(trigger=False, offload_target="RAM")
    assert status == "NO_ACTION"
    assert freed == 0.0
    assert payload == ""


def test_node_trigger_no_response():
    node = PSN_LLM_Offloader()
    status, freed, payload = node.run(
        trigger=True,
        offload_target="RAM",
        model_id="test-model",
        api_response="",
        last_trigger_time=0.0,
    )
    assert status == "NO_ACTION"
    assert freed == 0.0
    data = json.loads(payload)
    assert data["action"] == "swap_to_cpu"
    assert data["model"] == "test-model"


def test_node_trigger_with_success_response():
    node = PSN_LLM_Offloader()
    resp = json.dumps({"success": True, "freed_vram_gb": 8.0})
    status, freed, payload = node.run(
        trigger=True,
        offload_target="DISK",
        model_id="big-model",
        api_response=resp,
        last_trigger_time=0.0,
    )
    assert status == "OFFLOADED"
    assert freed == 8.0
    data = json.loads(payload)
    assert data["action"] == "terminate"


def test_node_invalid_target():
    node = PSN_LLM_Offloader()
    status, freed, payload = node.run(
        trigger=True,
        offload_target="GPU",
        model_id="x",
        api_response="",
        last_trigger_time=0.0,
    )
    assert status == "FAILED"
    assert freed == 0.0
    assert payload == ""


def test_node_rate_limited():
    node = PSN_LLM_Offloader()
    now = time.time()
    recent = now - 0.1  # just triggered 0.1s ago
    status, freed, payload = node.run(
        trigger=True,
        offload_target="RAM",
        model_id="x",
        api_response="",
        last_trigger_time=recent,
    )
    assert status == "NO_ACTION"
    assert freed == 0.0
    assert payload == ""
