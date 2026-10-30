"""Tests for psn_nodes.gen.psn_fast_attention_patch (pure-logic attention patch planner)."""

import json

import pytest

from psn_nodes.gen.psn_fast_attention_patch import (
    PSN_Fast_Attention_Patch,
    build_patch_plan,
    resolve_backend,
    _normalize_backend,
)


def test_auto_prefers_flash_when_available():
    backend, reason = resolve_backend("auto", 80, {"flash_attn": True, "sageattention": True})
    assert backend == "flash"
    assert "flash" in reason


def test_auto_falls_back_to_sage_when_flash_missing():
    backend, reason = resolve_backend("auto", 80, {"flash_attn": False, "sageattention": True})
    assert backend == "sage"


def test_auto_falls_back_to_sdpa_on_low_sm():
    # sm_70 is below flash/sage minimum (80), so sdpa is chosen.
    backend, reason = resolve_backend("auto", 70, {"flash_attn": True, "sageattention": True})
    assert backend == "sdpa"
    assert "sdpa" in reason


def test_explicit_flash_unavailable_falls_back_to_sdpa():
    backend, reason = resolve_backend("flash", 80, {"flash_attn": False})
    assert backend == "sdpa"
    assert "fell back" in reason


def test_explicit_sdpa_always_feasible():
    backend, reason = resolve_backend("sdpa", 50, {})
    assert backend == "sdpa"
    assert backend != "auto"


def test_normalize_backend_rejects_unknown():
    with pytest.raises(ValueError):
        _normalize_backend("quantum")


def test_normalize_backend_rejects_non_string():
    with pytest.raises(ValueError):
        _normalize_backend(123)


def test_build_patch_plan_feasible_flash():
    plan = build_patch_plan("flash", 80, {"flash_attn": True}, 64, 2, 512)
    assert plan["backend"] == "flash"
    assert plan["feasible"] is True
    assert plan["replacement"] == "flash_attn.flash_attn_func"
    assert plan["target_function"] == "torch.nn.functional.scaled_dot_product_attention"
    # memory estimate: 2 * 16 * 512 * 512 * 2 bytes = 16,777,216 bytes = 16.0 MB
    assert plan["memory_estimate_mb"] == 16.0


def test_build_patch_plan_invalid_dims_zero_memory():
    plan = build_patch_plan("sdpa", 80, {}, 0, 1, 1024)
    assert plan["memory_estimate_mb"] == 0.0
    assert plan["feasible"] is True


def test_node_run_returns_json_and_feasible():
    node = PSN_Fast_Attention_Patch()
    plan_json, feasible, reason = node.run(
        backend="auto", sm=80,
        available_packages=json.dumps({"flash_attn": True}),
        head_dim=64, batch_size=1, seq_len=256,
    )
    plan = json.loads(plan_json)
    assert feasible is True
    assert plan["backend"] == "flash"
    assert "flash" in reason


def test_node_run_bad_json_packages_defaults_empty():
    node = PSN_Fast_Attention_Patch()
    plan_json, feasible, reason = node.run(
        backend="flash", sm=80,
        available_packages="not-json",
        head_dim=64, batch_size=1, seq_len=128,
    )
    plan = json.loads(plan_json)
    # flash requested but package map empty -> falls back to sdpa
    assert plan["backend"] == "sdpa"
    assert feasible is True


def test_node_run_low_sm_sdpa_feasible():
    node = PSN_Fast_Attention_Patch()
    plan_json, feasible, reason = node.run(
        backend="auto", sm=50,
        available_packages="{}",
        head_dim=32, batch_size=1, seq_len=64,
    )
    plan = json.loads(plan_json)
    assert plan["backend"] == "sdpa"
    assert feasible is True


def test_node_run_sm_below_sdpa_min_still_reports():
    # sm_40 is below even sdpa's nominal minimum (50); plan marks infeasible but
    # still returns sdpa as last resort.
    plan = build_patch_plan("sdpa", 40, {}, 64, 1, 128)
    assert plan["backend"] == "sdpa"
    assert plan["feasible"] is False
