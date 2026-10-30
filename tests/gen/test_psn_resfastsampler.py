"""Tests for psn_nodes.gen.psn_resfastsampler (pure-logic RES fast sampler)."""

import json

from psn_nodes.gen.psn_resfastsampler import (
    PSN_RESFastSampler,
    plan_res_steps,
    res_quality_risk,
    derive_latent_seed,
    build_res_payload,
    RES_MIN_STEPS,
    RES_MAX_STEPS,
)


def test_plan_res_steps_default_shape():
    plan = plan_res_steps(20)
    assert plan["steps"] == 20
    assert plan["schedule"] == "res"
    assert len(plan["sigmas"]) == 20
    assert plan["sigmas"][0] == 1.0
    assert plan["sigmas"][-1] == 0.0
    # strictly descending
    for a, b in zip(plan["sigmas"], plan["sigmas"][1:]):
        assert a > b


def test_plan_res_steps_clamps_low_and_high():
    assert plan_res_steps(3)["steps"] == RES_MIN_STEPS
    assert plan_res_steps(9999)["steps"] == RES_MAX_STEPS
    assert len(plan_res_steps(9999)["sigmas"]) == RES_MAX_STEPS


def test_plan_res_steps_bad_input_falls_back():
    # non-numeric input should not raise; it clamps to the minimum
    plan = plan_res_steps("not-a-number")
    assert plan["steps"] == RES_MIN_STEPS
    assert plan["sigmas"][-1] == 0.0


def test_quality_risk_below_minimum_fails():
    ok, reason = res_quality_risk(5)
    assert ok is False
    assert "below" in reason


def test_quality_risk_fast_and_standard_ranges():
    ok_fast, reason_fast = res_quality_risk(20)
    assert ok_fast is True
    assert "fast" in reason_fast
    ok_std, reason_std = res_quality_risk(60)
    assert ok_std is True
    assert "standard" in reason_std


def test_derive_latent_seed_deterministic_and_varies():
    s1 = derive_latent_seed(123, 20, 7.0)
    s2 = derive_latent_seed(123, 20, 7.0)
    assert s1 == s2
    s3 = derive_latent_seed(123, 21, 7.0)
    assert s1 != s3
    assert 0 <= s1 < 2**32


def test_build_res_payload_is_json_serializable():
    payload = build_res_payload(20, 7.0, 42)
    text = json.dumps(payload)
    assert json.loads(text)["steps"] == 20
    assert payload["quality_ok"] is True
    assert payload["schedule"] == "res"


def test_node_run_returns_consistent_outputs():
    node = PSN_RESFastSampler()
    payload_text, schedule_json, seed, ok = node.run(steps=20, cfg=7.0, seed=7)
    payload = json.loads(payload_text)
    assert ok is True
    assert seed == payload["seed"]
    assert json.loads(schedule_json) == payload["sigmas"]
    assert len(json.loads(schedule_json)) == 20


def test_node_run_low_steps_reports_risk():
    node = PSN_RESFastSampler()
    payload_text, _, _, ok = node.run(steps=5, cfg=7.0, seed=1)
    payload = json.loads(payload_text)
    assert ok is False
    assert payload["quality_ok"] is False
    # steps are clamped to the minimum for the schedule
    assert payload["steps"] == RES_MIN_STEPS


def test_node_run_bad_steps_does_not_crash():
    node = PSN_RESFastSampler()
    payload_text, _, seed, ok = node.run(steps="garbage", cfg=7.0, seed=0)
    payload = json.loads(payload_text)
    assert payload["steps"] == RES_MIN_STEPS
    assert 0 <= seed < 2**32
