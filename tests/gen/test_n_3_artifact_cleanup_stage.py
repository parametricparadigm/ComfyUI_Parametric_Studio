"""Tests for psn_nodes.gen.n_3_artifact_cleanup_stage (pure-logic NAFNet denoise stage)."""

import json

from psn_nodes.gen.n_3_artifact_cleanup_stage import (
    PSN_NAFNet_Denoise,
    build_denoise_plan,
    ALLOWED_MODELS,
)


def _meta(width=512, height=512, channels=3):
    return json.dumps({"width": width, "height": height, "channels": channels})


def test_valid_plan_shape_and_content():
    ok, reason, plan = build_denoise_plan(0.1, "nafnet_srgb", _meta())
    assert ok is True
    assert reason == "ok"
    assert plan is not None
    assert plan["model_path"] == "nafnet_srgb"
    assert plan["width"] == 512
    assert plan["height"] == 512
    assert plan["channels"] == 3
    # gains: one per channel, within (0,1]
    assert len(plan["gains"]) == 3
    for g in plan["gains"]:
        assert 0.05 <= g <= 1.0
    # blur kernel is odd and in [3,7]
    assert plan["blur_kernel"] % 2 == 1
    assert 3 <= plan["blur_kernel"] <= 7
    # preview shape matches capped dims (stored as list for JSON)
    assert plan["preview_shape"] == [4, 4, 3]
    assert len(plan["preview"]) == 4 * 4 * 3


def test_denoise_changes_data_higher_noise_stronger():
    low_ok, _, low_plan = build_denoise_plan(0.0, "nafnet_srgb", _meta())
    high_ok, _, high_plan = build_denoise_plan(1.0, "nafnet_srgb", _meta())
    assert low_ok and high_ok
    # higher noise -> lower (stronger) gains
    for c in range(3):
        assert high_plan["gains"][c] < low_plan["gains"][c]
    # preview differs between noise levels (denoising occurred)
    assert low_plan["preview"] != high_plan["preview"]


def test_invalid_noise_level_out_of_range():
    ok, reason, plan = build_denoise_plan(1.5, "nafnet_srgb", _meta())
    assert ok is False
    assert plan is None
    assert "out of range" in reason


def test_invalid_noise_level_non_numeric():
    ok, reason, plan = build_denoise_plan("0.1", "nafnet_srgb", _meta())
    assert ok is False
    assert plan is None
    assert "must be a number" in reason


def test_invalid_model_path_not_in_allowlist():
    ok, reason, plan = build_denoise_plan(0.1, "nafnet_unknown", _meta())
    assert ok is False
    assert plan is None
    assert "allow-list" in reason


def test_invalid_image_meta_bad_json():
    ok, reason, plan = build_denoise_plan(0.1, "nafnet_srgb", "not json {")
    assert ok is False
    assert plan is None
    assert "not valid JSON" in reason


def test_invalid_image_meta_bad_dimension():
    bad = json.dumps({"width": 0, "height": 512, "channels": 3})
    ok, reason, plan = build_denoise_plan(0.1, "nafnet_srgb", bad)
    assert ok is False
    assert plan is None
    assert "out of range" in reason


def test_node_run_returns_json_plan():
    node = PSN_NAFNet_Denoise()
    ok, reason, plan_json = node.run(0.2, "nafnet_yuv", _meta(width=256, height=128, channels=1))
    assert ok is True
    assert reason == "ok"
    plan = json.loads(plan_json)
    assert plan["model_path"] == "nafnet_yuv"
    assert plan["channels"] == 1
    assert len(plan["gains"]) == 1
    assert plan["preview_shape"] == [4, 4, 1]


def test_node_run_failure_returns_empty_plan_json():
    node = PSN_NAFNet_Denoise()
    ok, reason, plan_json = node.run(0.2, "bad_model", _meta())
    assert ok is False
    assert plan_json == ""
    assert "allow-list" in reason


def test_all_allowed_models_accepted():
    for model in ALLOWED_MODELS:
        ok, reason, plan = build_denoise_plan(0.3, model, _meta())
        assert ok is True, (model, reason)
        assert plan["model_path"] == model
