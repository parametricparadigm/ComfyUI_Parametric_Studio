"""Tests for psn_nodes.gen.n_8_nvidia_vfx_integration (pure-logic planner)."""

import json

from psn_nodes.gen.n_8_nvidia_vfx_integration import (
    PSN_Nvidia_VFX_Upscale,
    build_upscale_plan,
    _ALLOWED_VFX_MODELS,
)


def test_plan_scales_dimensions_correctly():
    ok, why, plan = build_upscale_plan(512, 512, 2, "rtx_video_sr")
    assert ok is True
    assert why == "ok"
    assert plan["output"]["width"] == 1024
    assert plan["output"]["height"] == 1024
    assert plan["input"] == {"width": 512, "height": 512}
    assert plan["scale"] == 2


def test_plan_rejects_scale_out_of_range():
    ok, why, plan = build_upscale_plan(512, 512, 0, "rtx_video_sr")
    assert ok is False
    assert plan is None
    assert "scale" in why
    ok2, why2, plan2 = build_upscale_plan(512, 512, 9, "rtx_video_sr")
    assert ok2 is False
    assert plan2 is None


def test_plan_rejects_non_integer_scale():
    ok, why, plan = build_upscale_plan(512, 512, 2.5, "rtx_video_sr")
    assert ok is False
    assert plan is None
    # bool is an int subclass and must be rejected
    okb, whyb, planb = build_upscale_plan(512, 512, True, "rtx_video_sr")
    assert okb is False
    assert planb is None


def test_plan_rejects_disallowed_model():
    ok, why, plan = build_upscale_plan(512, 512, 2, "totally_fake_model")
    assert ok is False
    assert plan is None
    assert "allow-list" in why
    # every allow-listed model should be accepted
    for m in _ALLOWED_VFX_MODELS:
        okm, whym, planm = build_upscale_plan(128, 64, 1, m)
        assert okm is True, (m, whym)
        assert planm["vfx_model"] == m


def test_plan_rejects_bad_dimensions():
    ok, why, plan = build_upscale_plan(0, 512, 2, "rtx_video_sr")
    assert ok is False
    assert plan is None
    ok2, why2, plan2 = build_upscale_plan(512, -3, 2, "rtx_video_sr")
    assert ok2 is False
    ok3, why3, plan3 = build_upscale_plan("512", 512, 2, "rtx_video_sr")
    assert ok3 is False
    ok4, why4, plan4 = build_upscale_plan(16385, 512, 2, "rtx_video_sr")
    assert ok4 is False


def test_node_run_happy_path_and_json_roundtrip():
    node = PSN_Nvidia_VFX_Upscale()
    ok, plan_json, out_w, out_h = node.run(512, 512, 2, "rtx_video_sr")
    assert ok is True
    assert out_w == 1024
    assert out_h == 1024
    plan = json.loads(plan_json)
    assert plan["op"] == "nvidia_vfx_upscale"
    assert plan["output"] == {"width": 1024, "height": 1024}


def test_node_run_uses_image_json_dimensions_when_valid():
    node = PSN_Nvidia_VFX_Upscale()
    img = json.dumps({"width": 256, "height": 128})
    ok, plan_json, out_w, out_h = node.run(999, 999, 2, "rtx_video_sr", image_json=img)
    assert ok is True
    assert out_w == 512
    assert out_h == 256
    plan = json.loads(plan_json)
    assert plan["input"] == {"width": 256, "height": 128}


def test_node_run_ignores_invalid_image_json_and_falls_back():
    node = PSN_Nvidia_VFX_Upscale()
    # invalid JSON -> fall back to explicit width/height
    ok, plan_json, out_w, out_h = node.run(100, 50, 2, "rtx_video_sr", image_json="{not json")
    assert ok is True
    assert out_w == 200
    assert out_h == 100
    # JSON without integer dims -> fall back
    ok2, _, out_w2, out_h2 = node.run(100, 50, 2, "rtx_video_sr", image_json='{"width":"x"}')
    assert ok2 is True
    assert out_w2 == 200
    assert out_h2 == 100


def test_node_run_reports_failure_cleanly():
    node = PSN_Nvidia_VFX_Upscale()
    ok, plan_json, out_w, out_h = node.run(512, 512, 2, "not_a_real_model")
    assert ok is False
    assert out_w == 0
    assert out_h == 0
    payload = json.loads(plan_json)
    assert payload["ok"] is False
    assert "reason" in payload
