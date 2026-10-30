"""
PSN_Document_Quality_Assessor

Pure-logic document quality assessment for OCR pre-filtering.

This module implements a secure-by-design, dependency-free quality gate that
operates on *plain numeric descriptors* of a document scan (width, height,
DPI, sharpness, contrast) rather than on raw image tensors.  It is the
"pure-logic, secure-by-design part" of the Document Quality Assessment
Pipeline: no torch, no ComfyUI internals, no file/network I/O, no eval/exec.

The node validates the descriptor, computes a 0.0-1.0 quality score from
resolution, sharpness and contrast, emits a JSON list of detected issues, and
returns a pass/fail boolean.  Downstream logic can route to OCR or reject the
document based on these outputs.

Inputs are plain values (ints, floats, strings).  The `image` input is
represented by its numeric descriptors (width_px, height_px, dpi, sharpness,
contrast) so that the node can be exercised without any image library.
"""

import json
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Standard print/scan DPI reference used to normalise resolution.
_REF_DPI = 300.0

# Sharpness and contrast are expected to be normalised to [0.0, 1.0].
# Values outside this range are clamped for scoring but flagged as issues.
_MIN_METRIC = 0.0
_MAX_METRIC = 1.0

# Weights for the composite quality score.  They sum to 1.0.
_WEIGHT_RESOLUTION = 0.4
_WEIGHT_SHARPNESS = 0.35
_WEIGHT_CONTRAST = 0.25

# A document passes when its composite score is at or above this value.
_PASS_SCORE = 0.6

# Issue labels (stable strings, safe for JSON and downstream matching).
_ISSUE_LOW_RESOLUTION = "low_resolution"
_ISSUE_BLURRY = "blurry"
_ISSUE_LOW_CONTRAST = "low_contrast"
_ISSUE_INVALID_INPUT = "invalid_input"
_ISSUE_OUT_OF_RANGE = "out_of_range"

# Category for the ComfyUI node tree.
_CAT = "ParametricStudio/DocumentQuality"


# ---------------------------------------------------------------------------
# Pure helpers (no I/O, no side effects)
# ---------------------------------------------------------------------------

def _clamp(value, lo, hi):
    """Clamp *value* into the closed interval [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _is_finite_number(value):
    """Return True if *value* is a real, finite number (int or float)."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _validate_descriptor(width_px, height_px, dpi, sharpness, contrast):
    """
    Validate the numeric descriptor of a document scan.

    Returns a tuple (ok, issues) where *issues* is a list of issue labels.
    A descriptor is considered valid when every field is a finite number and
    the geometric fields (width, height, dpi) are positive.
    """
    issues = []

    fields = (width_px, height_px, dpi, sharpness, contrast)
    for field in fields:
        if not _is_finite_number(field):
            issues.append(_ISSUE_INVALID_INPUT)
            return False, issues

    if width_px <= 0 or height_px <= 0 or dpi <= 0:
        issues.append(_ISSUE_INVALID_INPUT)
        return False, issues

    # Sharpness and contrast are expected in [0, 1]; out-of-range values are
    # clamped for scoring but recorded so the caller can inspect them.
    if not (_MIN_METRIC <= sharpness <= _MAX_METRIC):
        issues.append(_ISSUE_OUT_OF_RANGE)
    if not (_MIN_METRIC <= contrast <= _MAX_METRIC):
        issues.append(_ISSUE_OUT_OF_RANGE)

    return True, issues


def _resolution_score(width_px, height_px, dpi, min_resolution):
    """
    Compute a resolution sub-score in [0, 1].

    The effective DPI is compared against the required *min_resolution*.
    A document at or above the required resolution scores 1.0; below it, the
    score scales linearly with the ratio of effective DPI to the requirement.
    """
    if min_resolution <= 0:
        # No meaningful requirement; treat resolution as fully satisfied.
        return 1.0
    ratio = dpi / float(min_resolution)
    return _clamp(ratio, 0.0, 1.0)


def _sharpness_score(sharpness):
    """Return the clamped sharpness as a sub-score in [0, 1]."""
    return _clamp(sharpness, _MIN_METRIC, _MAX_METRIC)


def _contrast_score(contrast):
    """Return the clamped contrast as a sub-score in [0, 1]."""
    return _clamp(contrast, _MIN_METRIC, _MAX_METRIC)


def _composite_score(res_score, sharp_score, contrast_score):
    """Combine sub-scores into a single 0.0-1.0 quality score."""
    score = (
        _WEIGHT_RESOLUTION * res_score
        + _WEIGHT_SHARPNESS * sharp_score
        + _WEIGHT_CONTRAST * contrast_score
    )
    return _clamp(score, 0.0, 1.0)


def _detect_issues(res_score, sharp_score, contrast_score,
                   min_resolution, blur_threshold, pre_issues):
    """
    Build the final list of issue labels.

    *pre_issues* are validation issues already collected (e.g. invalid or
    out-of-range inputs).  Quality issues are appended when a sub-score falls
    below its threshold.
    """
    issues = list(pre_issues)

    if res_score < 1.0:
        issues.append(_ISSUE_LOW_RESOLUTION)
    if sharp_score < blur_threshold:
        issues.append(_ISSUE_BLURRY)
    if contrast_score < 0.5:
        issues.append(_ISSUE_LOW_CONTRAST)

    # De-duplicate while preserving order.
    seen = set()
    ordered = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            ordered.append(issue)
    return ordered


def assess_document(width_px, height_px, dpi, sharpness, contrast,
                    min_resolution, blur_threshold):
    """
    Pure assessment routine.

    Returns a dict with keys: quality_score (float), issues (list[str]),
    pass_fail (bool), valid (bool).
    """
    valid, pre_issues = _validate_descriptor(
        width_px, height_px, dpi, sharpness, contrast)

    if not valid:
        # Cannot meaningfully score an invalid descriptor.
        return {
            "quality_score": 0.0,
            "issues": pre_issues,
            "pass_fail": False,
            "valid": False,
        }

    res_score = _resolution_score(width_px, height_px, dpi, min_resolution)
    sharp_score = _sharpness_score(sharpness)
    contrast_score = _contrast_score(contrast)

    score = _composite_score(res_score, sharp_score, contrast_score)
    issues = _detect_issues(
        res_score, sharp_score, contrast_score,
        min_resolution, blur_threshold, pre_issues)

    # A document fails if it has any critical quality issues (blurry, low
    # resolution, low contrast) OR if its composite score is below the pass
    # threshold.  This ensures that even a high composite score cannot mask
    # a critical defect like severe blur.
    has_critical_issue = (
        _ISSUE_BLURRY in issues or
        _ISSUE_LOW_RESOLUTION in issues or
        _ISSUE_LOW_CONTRAST in issues
    )
    pass_fail = (score >= _PASS_SCORE) and (not has_critical_issue)

    return {
        "quality_score": score,
        "issues": issues,
        "pass_fail": pass_fail,
        "valid": True,
    }


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

class PSN_Document_Quality_Assessor:
    """
    Assess the quality of a document scan before OCR or AI processing.

    Operates on plain numeric descriptors of the image (width, height, DPI,
    sharpness, contrast) so it can run without any image library.  Returns a
    0.0-1.0 quality score, a JSON string of detected issues, and a pass/fail
    boolean for conditional routing.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Numeric descriptors of the document scan.
                "width_px": ("INT", {"default": 2480, "min": 1, "max": 100000, "step": 1}),
                "height_px": ("INT", {"default": 3508, "min": 1, "max": 100000, "step": 1}),
                "dpi": ("FLOAT", {"default": 300.0, "min": 1.0, "max": 1200.0, "step": 1.0}),
                "sharpness": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
                "contrast": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
                # Quality requirements.
                "min_resolution": ("INT", {"default": 300, "min": 1, "max": 1200, "step": 1}),
                "blur_threshold": ("FLOAT", {"default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("FLOAT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("quality_score", "issues", "pass_fail")
    FUNCTION = "run"
    CATEGORY = _CAT

    def run(self, width_px, height_px, dpi, sharpness, contrast,
            min_resolution, blur_threshold):
        result = assess_document(
            width_px, height_px, dpi, sharpness, contrast,
            min_resolution, blur_threshold)

        issues_json = json.dumps(result["issues"], separators=(",", ":"))
        return (
            float(result["quality_score"]),
            issues_json,
            bool(result["pass_fail"]),
        )


# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Document_Quality_Assessor": PSN_Document_Quality_Assessor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Document_Quality_Assessor": "PSN Document Quality Assessor",
}
