"""Tests for psn_nodes.gen.psn_templates (pure-logic template orchestration)."""

import json

import pytest

from psn_nodes.gen.psn_templates import (
    TEMPLATE_NAMES,
    PSN_Template_Loader,
    PSN_Template_Controller,
    build_plan,
    build_payload,
    payload_to_json,
    parse_payload,
    _redact,
)


def test_loader_returns_valid_plan_for_each_template():
    loader = PSN_Template_Loader()
    for name in TEMPLATE_NAMES:
        plan, payload_json = loader.run(template_name=name)
        assert plan["template"] == name
        assert plan["steps"] >= 1
        assert 0.0 <= plan["denoise"] <= 1.0
        parsed = json.loads(payload_json)
        assert parsed["template"] == name
        assert parsed["sampler"]["name"] == plan["sampler_name"]


def test_loader_applies_numeric_overrides():
    loader = PSN_Template_Loader()
    plan, _ = loader.run(template_name="basic_img2img", steps=42, cfg=9.5, denoise=0.5)
    assert plan["steps"] == 42
    assert plan["cfg"] == 9.5
    assert plan["denoise"] == 0.5


def test_loader_clamps_out_of_range_overrides():
    loader = PSN_Template_Loader()
    plan, _ = loader.run(template_name="video_gen", steps=99999, cfg=500.0, denoise=5.0)
    assert plan["steps"] == 1000
    assert plan["cfg"] == 100.0
    assert plan["denoise"] == 1.0


def test_build_plan_rejects_unknown_template():
    with pytest.raises(ValueError):
        build_plan("not_a_template")
    with pytest.raises(ValueError):
        build_plan(123)


def test_build_plan_rejects_non_numeric_steps():
    with pytest.raises(ValueError):
        build_plan("inpaint", steps="twenty")
    # bool is not accepted as a number
    with pytest.raises(ValueError):
        build_plan("inpaint", steps=True)


def test_controller_round_trips_loader_payload():
    loader = PSN_Template_Loader()
    _, payload_json = loader.run(template_name="inpaint")
    controller = PSN_Template_Controller()
    plan, status, ok = controller.run(payload_json=payload_json)
    assert ok is True
    assert plan["template"] == "inpaint"
    assert "ready" in status


def test_controller_rejects_malformed_payload():
    controller = PSN_Template_Controller()
    plan, status, ok = controller.run(payload_json="{not json")
    assert ok is False
    assert plan == {}
    assert "invalid payload" in status


def test_controller_rejects_payload_missing_sampler():
    controller = PSN_Template_Controller()
    bad = json.dumps({"template": "inpaint"})
    plan, status, ok = controller.run(payload_json=bad)
    assert ok is False
    assert "invalid" in status


def test_parse_payload_validates_shape():
    good = json.dumps({"template": "inpaint", "sampler": {
        "name": "dpmpp_2m", "scheduler": "sgm_uniform",
        "steps": 25, "cfg": 5.0, "denoise": 0.9}})
    data = parse_payload(good)
    assert data["sampler"]["steps"] == 25
    with pytest.raises(ValueError):
        parse_payload(json.dumps({"sampler": {"name": "x"}}))


def test_redact_masks_sensitive_values():
    assert _redact("api_token=abc123") == "api_token=***"
    assert _redact("password: hunter2") == "password: ***"
    assert _redact("steps=20") == "steps=20"
    assert _redact(42) == 42


def test_payload_notes_are_redacted():
    payload = build_payload("basic_img2img", notes="key=supersecret")
    assert "supersecret" not in payload_to_json(payload)
    assert "***" in payload_to_json(payload)
