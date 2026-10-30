"""
Tests for PSN_Face_Preserve_Inpaint node.
"""

import json
import pytest
from psn_nodes.gen.n_8_face_identity_preservation_in_inpainti import (
    PSN_Face_Preserve_Inpaint,
    _validate_face_model,
    _validate_identity_strength,
    _compute_mask_face_overlap,
    _build_plan,
    _KNOWN_FACE_MODELS,
)


def _make_mask(height, width, fill=0):
    """Create a 2D list of zeros."""
    return [[fill for _ in range(width)] for _ in range(height)]


def _mask_with_face_overlap(height=10, width=10):
    """Create a mask where the center (face region) is masked."""
    mask = _make_mask(height, width)
    # Face box is roughly x: 2.5-7.5, y: 1.5-6.5 for 10x10
    for y in range(2, 7):
        for x in range(3, 8):
            mask[y][x] = 1
    return mask


def _mask_no_face_overlap(height=10, width=10):
    """Create a mask only in the bottom-right corner (outside face box)."""
    mask = _make_mask(height, width)
    for y in range(8, 10):
        for x in range(8, 10):
            mask[y][x] = 1
    return mask


class TestValidateFaceModel:
    def test_valid_model(self):
        valid, reason = _validate_face_model("buffalo_l")
        assert valid is True
        assert reason == "valid model"

    def test_valid_model_case_insensitive(self):
        valid, reason = _validate_face_model("Buffalo_L")
        assert valid is True

    def test_invalid_model(self):
        valid, reason = _validate_face_model("unknown_model_xyz")
        assert valid is False
        assert "not in the allow-list" in reason

    def test_empty_model(self):
        valid, reason = _validate_face_model("")
        assert valid is False
        assert "must not be empty" in reason

    def test_non_string_model(self):
        valid, reason = _validate_face_model(123)
        assert valid is False
        assert "must be a string" in reason

    def test_all_known_models_valid(self):
        for model in _KNOWN_FACE_MODELS:
            valid, _ = _validate_face_model(model)
            assert valid is True, f"Model {model} should be valid"


class TestValidateIdentityStrength:
    def test_valid_strength(self):
        valid, val, reason = _validate_identity_strength(0.5)
        assert valid is True
        assert val == 0.5
        assert reason == "identity_strength valid"

    def test_strength_below_zero_clamped(self):
        valid, val, reason = _validate_identity_strength(-0.5)
        assert valid is True
        assert val == 0.0
        assert "clamped to 0.0" in reason

    def test_strength_above_one_clamped(self):
        valid, val, reason = _validate_identity_strength(1.5)
        assert valid is True
        assert val == 1.0
        assert "clamped to 1.0" in reason

    def test_strength_zero(self):
        valid, val, reason = _validate_identity_strength(0.0)
        assert valid is True
        assert val == 0.0

    def test_strength_one(self):
        valid, val, reason = _validate_identity_strength(1.0)
        assert valid is True
        assert val == 1.0

    def test_non_numeric_strength(self):
        valid, val, reason = _validate_identity_strength("high")
        assert valid is False
        assert "must be a number" in reason


class TestComputeMaskFaceOverlap:
    def test_empty_mask(self):
        overlap, has_content = _compute_mask_face_overlap([])
        assert overlap == 0.0
        assert has_content is False

    def test_all_zero_mask(self):
        mask = _make_mask(10, 10, 0)
        overlap, has_content = _compute_mask_face_overlap(mask)
        assert overlap == 0.0
        assert has_content is False

    def test_mask_with_face_overlap(self):
        mask = _mask_with_face_overlap()
        overlap, has_content = _compute_mask_face_overlap(mask)
        assert has_content is True
        assert overlap > 0.0
        assert overlap <= 1.0

    def test_mask_no_face_overlap(self):
        mask = _mask_no_face_overlap()
        overlap, has_content = _compute_mask_face_overlap(mask)
        assert has_content is True
        assert overlap == 0.0

    def test_invalid_mask_structure(self):
        overlap, has_content = _compute_mask_face_overlap("not a list")
        assert overlap == 0.0
        assert has_content is False

    def test_mask_with_non_list_rows(self):
        mask = [[1, 1], "bad_row", [0, 0]]
        overlap, has_content = _compute_mask_face_overlap(mask)
        assert overlap == 0.0
        assert has_content is False


class TestBuildPlan:
    def test_identity_active_with_valid_inputs(self):
        mask = _mask_with_face_overlap()
        plan = _build_plan("buffalo_l", 0.8, mask)
        assert plan["identity_active"] is True
        assert plan["model_valid"] is True
        assert plan["identity_strength"] == 0.8
        assert plan["face_overlap"] > 0.0
        assert "active" in plan["reason"].lower()

    def test_identity_inactive_invalid_model(self):
        mask = _mask_with_face_overlap()
        plan = _build_plan("bad_model", 0.8, mask)
        assert plan["identity_active"] is False
        assert plan["model_valid"] is False
        assert "disabled" in plan["reason"].lower()

    def test_identity_inactive_zero_strength(self):
        mask = _mask_with_face_overlap()
        plan = _build_plan("buffalo_l", 0.0, mask)
        assert plan["identity_active"] is False
        assert "strength is 0.0" in plan["reason"]

    def test_identity_inactive_empty_mask(self):
        plan = _build_plan("buffalo_l", 0.8, [])
        assert plan["identity_active"] is False
        assert "mask is empty" in plan["reason"]

    def test_identity_inactive_no_overlap(self):
        mask = _mask_no_face_overlap()
        plan = _build_plan("buffalo_l", 0.8, mask)
        assert plan["identity_active"] is False
        assert "does not overlap" in plan["reason"]

    def test_strength_clamped_in_plan(self):
        mask = _mask_with_face_overlap()
        plan = _build_plan("buffalo_l", 2.0, mask)
        assert plan["identity_strength"] == 1.0
        assert plan["identity_active"] is True


class TestNodeRun:
    def test_run_valid_inputs(self):
        node = PSN_Face_Preserve_Inpaint()
        mask = _mask_with_face_overlap()
        mask_json = json.dumps(mask)
        plan_json, identity_active, reason = node.run("buffalo_l", 0.8, mask_json)
        plan = json.loads(plan_json)
        assert identity_active is True
        assert plan["identity_active"] is True
        assert plan["face_model"] == "buffalo_l"
        assert plan["identity_strength"] == 0.8

    def test_run_invalid_model(self):
        node = PSN_Face_Preserve_Inpaint()
        mask = _mask_with_face_overlap()
        mask_json = json.dumps(mask)
        plan_json, identity_active, reason = node.run("nonexistent", 0.8, mask_json)
        plan = json.loads(plan_json)
        assert identity_active is False
        assert plan["model_valid"] is False

    def test_run_invalid_mask_json(self):
        node = PSN_Face_Preserve_Inpaint()
        plan_json, identity_active, reason = node.run("buffalo_l", 0.8, "not valid json")
        plan = json.loads(plan_json)
        assert identity_active is False
        assert plan["mask_has_content"] is False

    def test_run_empty_mask(self):
        node = PSN_Face_Preserve_Inpaint()
        plan_json, identity_active, reason = node.run("buffalo_l", 0.8, "[]")
        plan = json.loads(plan_json)
        assert identity_active is False
        assert "mask is empty" in reason

    def test_run_strength_clamped(self):
        node = PSN_Face_Preserve_Inpaint()
        mask = _mask_with_face_overlap()
        mask_json = json.dumps(mask)
        plan_json, identity_active, reason = node.run("buffalo_l", 1.5, mask_json)
        plan = json.loads(plan_json)
        assert plan["identity_strength"] == 1.0
        assert identity_active is True

    def test_run_non_numeric_strength(self):
        node = PSN_Face_Preserve_Inpaint()
        mask = _mask_with_face_overlap()
        mask_json = json.dumps(mask)
        plan_json, identity_active, reason = node.run("buffalo_l", "abc", mask_json)
        plan = json.loads(plan_json)
        assert identity_active is False
        assert plan["identity_strength"] == 0.0
