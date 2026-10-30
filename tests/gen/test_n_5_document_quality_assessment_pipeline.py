"""
Tests for PSN_Document_Quality_Assessor.

Covers the pure-logic assessment: good documents pass, blurry/low-res
documents fail, edge cases (zero/negative/invalid inputs, out-of-range
metrics, boundary thresholds) behave correctly, and the JSON issues output
is well-formed.  No files, no network, no image libraries.
"""

import json

import pytest

from psn_nodes.gen.n_5_document_quality_assessment_pipeline import (
    PSN_Document_Quality_Assessor,
    assess_document,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _run(width_px, height_px, dpi, sharpness, contrast,
         min_resolution=300, blur_threshold=0.4):
    node = PSN_Document_Quality_Assessor()
    return node.run(width_px, height_px, dpi, sharpness, contrast,
                    min_resolution, blur_threshold)


def test_high_quality_document_passes():
    """A sharp, high-contrast, 300 DPI scan should pass with a high score."""
    score, issues_json, passed = _run(
        width_px=2480, height_px=3508, dpi=300.0,
        sharpness=0.9, contrast=0.9)
    assert passed is True
    assert score >= 0.6
    issues = json.loads(issues_json)
    assert issues == []


def test_blurry_document_fails():
    """A blurry scan (low sharpness) should fail and report 'blurry'."""
    score, issues_json, passed = _run(
        width_px=2480, height_px=3508, dpi=300.0,
        sharpness=0.1, contrast=0.9)
    assert passed is False
    issues = json.loads(issues_json)
    assert "blurry" in issues


def test_low_resolution_document_fails():
    """A low-DPI scan should fail and report 'low_resolution'."""
    score, issues_json, passed = _run(
        width_px=1240, height_px=1754, dpi=150.0,
        sharpness=0.9, contrast=0.9)
    assert passed is False
    issues = json.loads(issues_json)
    assert "low_resolution" in issues


def test_low_contrast_document_reports_issue_and_fails():
    """Low contrast should be flagged and cause the document to fail."""
    score, issues_json, passed = _run(
        width_px=2480, height_px=3508, dpi=300.0,
        sharpness=0.9, contrast=0.1)
    issues = json.loads(issues_json)
    assert "low_contrast" in issues
    # Low contrast is a critical issue, so the document must fail.
    assert passed is False


def test_invalid_negative_dimensions_fail():
    """Negative or zero dimensions are invalid and must fail with an issue."""
    score, issues_json, passed = _run(
        width_px=-5, height_px=3508, dpi=300.0,
        sharpness=0.9, contrast=0.9)
    assert passed is False
    assert score == 0.0
    issues = json.loads(issues_json)
    assert "invalid_input" in issues


def test_non_numeric_input_fails_safely():
    """A non-numeric descriptor must not raise; it should fail with an issue."""
    score, issues_json, passed = _run(
        width_px="not-a-number", height_px=3508, dpi=300.0,
        sharpness=0.9, contrast=0.9)
    assert passed is False
    assert score == 0.0
    issues = json.loads(issues_json)
    assert "invalid_input" in issues


def test_out_of_range_metrics_clamped_and_flagged():
    """Sharpness/contrast above 1.0 are clamped for scoring but flagged."""
    score, issues_json, passed = _run(
        width_px=2480, height_px=3508, dpi=300.0,
        sharpness=1.5, contrast=1.5)
    issues = json.loads(issues_json)
    assert "out_of_range" in issues
    # Clamped to 1.0, so the document still passes (no critical issues).
    assert passed is True
    assert score == pytest.approx(1.0)


def test_boundary_blur_threshold():
    """Sharpness exactly at the blur threshold should not be flagged blurry."""
    score, issues_json, passed = _run(
        width_px=2480, height_px=3508, dpi=300.0,
        sharpness=0.4, contrast=0.9, blur_threshold=0.4)
    issues = json.loads(issues_json)
    assert "blurry" not in issues
    # No critical issues, high score, so it should pass.
    assert passed is True


def test_just_below_blur_threshold_flagged():
    """Sharpness just below the blur threshold should be flagged blurry and fail."""
    score, issues_json, passed = _run(
        width_px=2480, height_px=3508, dpi=300.0,
        sharpness=0.39, contrast=0.9, blur_threshold=0.4)
    issues = json.loads(issues_json)
    assert "blurry" in issues
    # Blurry is a critical issue, so it must fail.
    assert passed is False


def test_assess_document_returns_valid_structure():
    """The pure helper returns a well-formed dict for a valid descriptor."""
    result = assess_document(2480, 3508, 300.0, 0.9, 0.9, 300, 0.4)
    assert set(result.keys()) == {"quality_score", "issues", "pass_fail", "valid"}
    assert result["valid"] is True
    assert 0.0 <= result["quality_score"] <= 1.0
    assert isinstance(result["issues"], list)
    assert isinstance(result["pass_fail"], bool)


def test_assess_document_invalid_returns_zero_score():
    """The pure helper returns a zero score and valid=False for bad input."""
    result = assess_document(0, 3508, 300.0, 0.9, 0.9, 300, 0.4)
    assert result["valid"] is False
    assert result["quality_score"] == 0.0
    assert result["pass_fail"] is False
    assert "invalid_input" in result["issues"]


def test_node_registration_present():
    """The node is registered under its PSN_ id with a display name."""
    assert "PSN_Document_Quality_Assessor" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Document_Quality_Assessor"] is PSN_Document_Quality_Assessor
    assert "PSN_Document_Quality_Assessor" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_schema_shape():
    """INPUT_TYPES exposes the expected required fields with sane defaults."""
    spec = PSN_Document_Quality_Assessor.INPUT_TYPES()
    required = spec["required"]
    for key in ("width_px", "height_px", "dpi", "sharpness", "contrast",
                "min_resolution", "blur_threshold"):
        assert key in required
    assert required["min_resolution"][0] == "INT"
    assert required["blur_threshold"][0] == "FLOAT"
