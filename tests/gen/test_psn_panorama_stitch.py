"""Tests for the PSN_Panorama_Stitch pure-logic panorama stitch planner."""

import json
import math

import pytest

from psn_nodes.gen.psn_panorama_stitch import (
    PSN_Panorama_Stitch,
    assess_seam_risk,
    blend_weights_at_angle,
    plan_panorama,
    summarize_plan,
    validate_panorama_config,
)


def test_validate_panorama_config_accepts_valid():
    ok, errors, warnings = validate_panorama_config(3, 90.0, 0.3)
    assert ok is True
    assert errors == []
    # 0.3 overlap is above the seam-risk threshold, so no seam warning expected.
    assert not any("seam" in w for w in warnings)


def test_validate_panorama_config_rejects_bad_inputs():
    # Non-numeric frame count.
    ok, errors, _ = validate_panorama_config("three", 90.0, 0.3)
    assert ok is False
    assert any("num_frames" in e for e in errors)

    # Out-of-range fov.
    ok, errors, _ = validate_panorama_config(3, 500.0, 0.3)
    assert ok is False
    assert any("fov" in e for e in errors)

    # Overlap above the allowed maximum.
    ok, errors, _ = validate_panorama_config(3, 90.0, 0.999)
    assert ok is False
    assert any("overlap" in e for e in errors)

    # Boolean is not treated as a number.
    ok, errors, _ = validate_panorama_config(True, 90.0, 0.3)
    assert ok is False


def test_validate_panorama_config_warns_on_low_overlap():
    ok, errors, warnings = validate_panorama_config(4, 90.0, 0.05)
    assert ok is True
    assert errors == []
    assert any("seam" in w for w in warnings)


def test_plan_panorama_uniform_step_and_coverage():
    plan = plan_panorama(3, 90.0, 0.3)
    # Step = fov * (1 - overlap) = 90 * 0.7 = 63.
    assert math.isclose(plan["angular_step"], 63.0, rel_tol=1e-9)
    assert plan["num_frames"] == 3
    # Frame coverage: each frame spans fov degrees.
    assert math.isclose(plan["frames"][0]["start_deg"], 0.0)
    assert math.isclose(plan["frames"][0]["end_deg"], 90.0)
    assert math.isclose(plan["frames"][1]["start_deg"], 63.0)
    assert math.isclose(plan["frames"][2]["start_deg"], 126.0)
    # Equirectangular canvas keeps a 2:1 aspect ratio.
    assert plan["out_width"] == 2 * plan["out_height"]
    assert plan["aspect_ratio"] == 2.0


def test_plan_panorama_single_frame():
    plan = plan_panorama(1, 120.0, 0.0)
    assert plan["angular_step"] == 120.0
    assert len(plan["frames"]) == 1
    assert plan["weights"] == [1.0]
    assert plan["seam_risk"] == "high"  # zero overlap


def test_plan_panorama_rejects_invalid_config():
    with pytest.raises(ValueError):
        plan_panorama(3, 90.0, 1.5)  # overlap out of range
    with pytest.raises(ValueError):
        plan_panorama(0, 90.0, 0.3)  # too few frames


def test_feather_weights_bounds_and_edges():
    plan = plan_panorama(4, 90.0, 0.4)
    weights = plan["weights"]
    assert len(weights) == 4
    # All weights are within [0, 1].
    for w in weights:
        assert 0.0 <= w <= 1.0
    # First and last frames are pinned to full weight.
    assert weights[0] == 1.0
    assert weights[-1] == 1.0


def test_blend_weights_at_angle_continuous_no_hard_seams():
    # Build a plan and sample blend weights across the full 360-degree sweep.
    plan = plan_panorama(6, 90.0, 0.3)
    total = 0.0
    samples = 720
    for i in range(samples):
        angle = 360.0 * i / samples
        weights = blend_weights_at_angle(angle, plan)
        assert len(weights) == 6
        for w in weights:
            assert 0.0 <= w <= 1.0
        total += sum(weights)
    # With sufficient overlap the combined coverage stays positive everywhere,
    # i.e. there is no angle where every frame contributes zero (a hard seam).
    assert total > 0.0
    # No single sample should have all-zero weights across the covered region.
    for i in range(samples):
        angle = 360.0 * i / samples
        weights = blend_weights_at_angle(angle, plan)
        # The covered region spans from 0 to (num_frames-1)*step + fov.
        covered_end = (plan["num_frames"] - 1) * plan["angular_step"] + plan["fov"]
        if 0.0 <= angle <= covered_end:
            assert sum(weights) > 0.0, "hard seam detected at angle %g" % angle


def test_assess_seam_risk_labels():
    assert assess_seam_risk(0.05)[0] == "high"
    assert assess_seam_risk(0.2)[0] == "medium"
    assert assess_seam_risk(0.5)[0] == "low"
    assert assess_seam_risk("nope")[0] == "unknown"
    assert assess_seam_risk(1.5)[0] == "invalid"


def test_summarize_plan_is_valid_json():
    plan = plan_panorama(3, 90.0, 0.3)
    text = summarize_plan(plan)
    parsed = json.loads(text)
    assert parsed["num_frames"] == 3
    assert parsed["projection"] == "equirectangular"
    assert "seam_risk" in parsed


def test_node_run_returns_plan_and_step():
    node = PSN_Panorama_Stitch()
    plan_json, summary, step, risk = node.run(3, 90.0, 0.3)
    parsed = json.loads(plan_json)
    assert parsed["num_frames"] == 3
    assert math.isclose(step, 63.0, rel_tol=1e-9)
    assert risk == "low"
    # Summary is also valid JSON.
    json.loads(summary)


def test_node_run_invalid_returns_error_payload():
    node = PSN_Panorama_Stitch()
    plan_json, summary, step, risk = node.run(3, 90.0, 1.5)
    parsed = json.loads(plan_json)
    assert parsed["ok"] is False
    assert step == 0.0
    assert risk == "invalid"
    assert "invalid" in summary
