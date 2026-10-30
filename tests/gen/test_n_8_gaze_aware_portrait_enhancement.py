"""
Tests for the pure-logic core of the Gaze-Aware Portrait Enhancement nodes.

These tests exercise the numeric/validation logic only (no torch, no
mediapipe, no opencv, no files, no network).
"""

import math

from psn_nodes.gen.n_8_gaze_aware_portrait_enhancement import (
    PSN_GazeEstimator,
    PSN_GazeCorrector,
    _normalize_vector,
    _correction_offset,
    _confidence_from_vector,
)


def test_gaze_estimator_normalizes_forward_gaze():
    node = PSN_GazeEstimator()
    gaze, pupil, conf, reason = node.run("0.0, 0.0, 1.0", "512, 384")
    assert reason == "ok"
    # Normalized forward vector.
    assert math.isclose(gaze[0], 0.0, abs_tol=1e-9)
    assert math.isclose(gaze[1], 0.0, abs_tol=1e-9)
    assert math.isclose(gaze[2], 1.0, abs_tol=1e-9)
    assert pupil == [512, 384]
    # Forward, unit-length vector should be high confidence.
    assert conf > 0.9


def test_gaze_estimator_left_gaze_has_negative_x():
    node = PSN_GazeEstimator()
    # Eyes looking left => negative x component.
    gaze, pupil, conf, reason = node.run("-0.5, 0.0, 0.866", "400, 384")
    assert reason == "ok"
    assert gaze[0] < 0.0
    # Still a valid unit-ish vector.
    norm = math.sqrt(sum(c * c for c in gaze))
    assert math.isclose(norm, 1.0, abs_tol=1e-6)


def test_gaze_estimator_rejects_zero_vector():
    node = PSN_GazeEstimator()
    gaze, pupil, conf, reason = node.run("0.0, 0.0, 0.0", "512, 384")
    assert reason != "ok"
    assert conf == 0.0
    # Fallback defaults.
    assert gaze == [0.0, 0.0, 1.0]
    assert pupil == [0, 0]


def test_gaze_estimator_rejects_bad_pupil_position():
    node = PSN_GazeEstimator()
    gaze, pupil, conf, reason = node.run("0.0, 0.0, 1.0", "512")
    assert reason != "ok"
    assert pupil == [0, 0]


def test_gaze_estimator_rejects_non_numeric_gaze():
    node = PSN_GazeEstimator()
    gaze, pupil, conf, reason = node.run("a, b, c", "512, 384")
    assert reason != "ok"
    assert conf == 0.0


def test_gaze_corrector_center_to_center_is_zero():
    node = PSN_GazeCorrector()
    offset, mag, safe, reason = node.run("0.0, 0.0, 1.0", "0.0, 0.0, 1.0", 0.5)
    assert reason == "ok"
    assert math.isclose(offset[0], 0.0, abs_tol=1e-9)
    assert math.isclose(offset[1], 0.0, abs_tol=1e-9)
    assert math.isclose(offset[2], 0.0, abs_tol=1e-9)
    assert math.isclose(mag, 0.0, abs_tol=1e-9)
    assert safe is True


def test_gaze_corrector_left_to_center_moves_positive_x():
    node = PSN_GazeCorrector()
    # Current gaze left (negative x), target center. Correction should push x positive.
    # Use a small strength to keep the correction within the safe bound.
    offset, mag, safe, reason = node.run("-0.5, 0.0, 0.866", "0.0, 0.0, 1.0", 0.5)
    assert reason == "ok"
    assert offset[0] > 0.0
    assert safe is True


def test_gaze_corrector_clamps_strength_and_flags_unsafe():
    node = PSN_GazeCorrector()
    # Opposite gazes with strength 1.0 produce a large offset (magnitude ~2).
    offset, mag, safe, reason = node.run("0.0, 0.0, 1.0", "0.0, 0.0, -1.0", 1.0)
    assert reason != "ok"
    assert safe is False
    assert mag > 0.5


def test_gaze_corrector_rejects_bad_target():
    node = PSN_GazeCorrector()
    offset, mag, safe, reason = node.run("0.0, 0.0, 1.0", "0.0, 1.0", 0.5)
    assert reason != "ok"
    assert safe is False


def test_normalize_vector_helper_rejects_wrong_length():
    vec, ok, reason = _normalize_vector([1.0, 0.0])
    assert ok is False
    assert vec is None


def test_correction_offset_helper_clamps_strength():
    offset, mag, ok, reason = _correction_offset(
        [0.0, 0.0, 1.0], [0.0, 0.0, -1.0], 5.0
    )
    assert ok is True
    # Strength clamped to 1.0, so offset magnitude is 2.0.
    assert math.isclose(mag, 2.0, abs_tol=1e-9)


def test_confidence_helper_zero_vector_is_zero():
    assert _confidence_from_vector([0.0, 0.0, 0.0]) == 0.0
