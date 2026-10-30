"""Tests for psn_nodes.gen.n_6_motion_data_cleaning_pipeline."""

import json
import math

import pytest

from psn_nodes.gen.n_6_motion_data_cleaning_pipeline import (
    PSN_MotionClean_Smooth,
    _jitter_metric,
    _moving_average,
    _kalman,
    _spline,
    _parse_motion,
    _smooth,
    _to_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_noisy_signal(n=50, base=0.0, amplitude=1.0, noise=0.3, seed=42):
    """Generate a smooth sine signal plus deterministic pseudo-noise."""
    import random
    rng = random.Random(seed)
    out = []
    for i in range(n):
        smooth = base + amplitude * math.sin(2.0 * math.pi * i / 20.0)
        out.append(smooth + rng.uniform(-noise, noise))
    return out


def _clean(node, motion_data, window=5, method="moving_average"):
    cleaned, jb, ja = node.run(motion_data, window, method)
    return cleaned, jb, ja


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_smoothing_reduces_jitter_moving_average():
    """Moving-average smoothing should reduce the jitter metric."""
    node = PSN_MotionClean_Smooth()
    noisy = _make_noisy_signal(n=60, noise=0.5)
    jb = _jitter_metric(noisy)
    cleaned, jitter_before, jitter_after = _clean(node, json.dumps(noisy), window=5, method="moving_average")
    assert jitter_before == pytest.approx(jb)
    assert jitter_after < jitter_before
    # cleaned should be a valid JSON list of the same length
    parsed = json.loads(cleaned)
    assert len(parsed) == len(noisy)
    assert all(isinstance(v, (int, float)) for v in parsed)


def test_smoothing_reduces_jitter_kalman():
    """Kalman smoothing should reduce the jitter metric."""
    node = PSN_MotionClean_Smooth()
    noisy = _make_noisy_signal(n=60, noise=0.5, seed=7)
    jb = _jitter_metric(noisy)
    _, jitter_before, jitter_after = _clean(node, json.dumps(noisy), window=5, method="kalman")
    assert jitter_before == pytest.approx(jb)
    assert jitter_after < jitter_before


def test_smoothing_reduces_jitter_spline():
    """Spline (weighted MA) smoothing should reduce the jitter metric."""
    node = PSN_MotionClean_Smooth()
    noisy = _make_noisy_signal(n=60, noise=0.5, seed=13)
    jb = _jitter_metric(noisy)
    _, jitter_before, jitter_after = _clean(node, json.dumps(noisy), window=7, method="spline")
    assert jitter_before == pytest.approx(jb)
    assert jitter_after < jitter_before


def test_perfectly_smooth_signal_has_zero_jitter():
    """A linear signal has zero second-difference, so jitter is 0."""
    seq = [float(i) for i in range(20)]
    assert _jitter_metric(seq) == pytest.approx(0.0)
    node = PSN_MotionClean_Smooth()
    _, jb, ja = _clean(node, json.dumps(seq), window=5, method="moving_average")
    assert jb == pytest.approx(0.0)
    # Moving average of a linear signal is still linear (except at edges),
    # so the interior jitter should be very small.
    assert ja < 0.1


def test_short_sequence_edge_cases():
    """Sequences with fewer than 3 samples should have jitter 0 and pass through."""
    node = PSN_MotionClean_Smooth()
    # 1 sample
    cleaned, jb, ja = _clean(node, json.dumps([1.0]), window=5, method="moving_average")
    assert jb == 0.0
    assert ja == 0.0
    assert json.loads(cleaned) == [1.0]
    # 2 samples
    cleaned, jb, ja = _clean(node, json.dumps([1.0, 2.0]), window=5, method="moving_average")
    assert jb == 0.0
    assert ja == 0.0
    # For n=2, moving average with window=5:
    # i=0: lo=0, hi=2 -> avg(1.0, 2.0) = 1.5
    # i=1: lo=0, hi=2 -> avg(1.0, 2.0) = 1.5
    assert json.loads(cleaned) == pytest.approx([1.5, 1.5])


def test_bad_input_empty_string():
    """Empty motion_data string should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="empty"):
        node.run("", 5, "moving_average")


def test_bad_input_invalid_json():
    """Non-JSON string should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="not valid JSON"):
        node.run("not a json array", 5, "moving_average")


def test_bad_input_non_array_json():
    """JSON that is not an array should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="must be an array"):
        node.run('{"a": 1}', 5, "moving_average")


def test_bad_input_non_numeric_element():
    """Array containing a non-numeric element should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="not a number"):
        node.run(json.dumps([1.0, "abc", 3.0]), 5, "moving_average")


def test_bad_input_non_finite_value():
    """Array containing NaN/Inf should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="not finite"):
        node.run(json.dumps([1.0, float("inf"), 3.0]), 5, "moving_average")


def test_bad_input_boolean_element():
    """Array containing a boolean should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="boolean"):
        node.run(json.dumps([1.0, True, 3.0]), 5, "moving_average")


def test_bad_input_none():
    """None motion_data should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="required"):
        node.run(None, 5, "moving_average")


def test_unknown_method_raises():
    """Unknown smoothing method should raise ValueError."""
    node = PSN_MotionClean_Smooth()
    with pytest.raises(ValueError, match="unknown smoothing method"):
        node.run(json.dumps([1.0, 2.0, 3.0]), 5, "gaussian")


def test_window_of_one_is_identity():
    """smoothing_window=1 should return the signal unchanged (for MA/spline)."""
    node = PSN_MotionClean_Smooth()
    seq = [1.0, 3.0, 2.0, 5.0, 4.0]
    cleaned, _, _ = _clean(node, json.dumps(seq), window=1, method="moving_average")
    assert json.loads(cleaned) == pytest.approx(seq)


def test_moving_average_known_values():
    """Verify moving average produces expected values for a small case."""
    seq = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = _moving_average(seq, 3)
    # window=3, half=1
    # i=0: avg(1,2)=1.5
    # i=1: avg(1,2,3)=2.0
    # i=2: avg(2,3,4)=3.0
    # i=3: avg(3,4,5)=4.0
    # i=4: avg(4,5)=4.5
    assert result == pytest.approx([1.5, 2.0, 3.0, 4.0, 4.5])


def test_kalman_reduces_noise_on_constant_signal():
    """Kalman filter on a noisy constant signal should converge near the constant."""
    import random
    rng = random.Random(99)
    n = 100
    seq = [5.0 + rng.uniform(-0.5, 0.5) for _ in range(n)]
    jb = _jitter_metric(seq)
    cleaned = _kalman(seq)
    ja = _jitter_metric(cleaned)
    assert ja < jb
    # The cleaned signal should be close to 5.0 on average
    mean_cleaned = sum(cleaned) / len(cleaned)
    assert abs(mean_cleaned - 5.0) < 0.5


def test_parse_motion_accepts_list_directly():
    """_parse_motion should accept a plain list of numbers."""
    seq = _parse_motion([1.0, 2.0, 3.0])
    assert seq == [1.0, 2.0, 3.0]


def test_parse_motion_accepts_numeric_strings():
    """_parse_motion should accept numeric strings in the array."""
    seq = _parse_motion(json.dumps(["1.0", "2.5", "3.0"]))
    assert seq == pytest.approx([1.0, 2.5, 3.0])


def test_to_json_roundtrip():
    """_to_json should produce valid JSON that round-trips."""
    seq = [1.0, 2.5, 3.14159]
    text = _to_json(seq)
    parsed = json.loads(text)
    assert parsed == pytest.approx(seq, abs=1e-5)


def test_node_class_mappings():
    """Verify module-level mappings are correctly defined."""
    from psn_nodes.gen.n_6_motion_data_cleaning_pipeline import (
        NODE_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS,
    )
    assert "PSN_MotionClean_Smooth" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_MotionClean_Smooth"] is PSN_MotionClean_Smooth
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_MotionClean_Smooth"] == "Motion Clean Smooth"


def test_input_types_structure():
    """Verify INPUT_TYPES has the expected keys and types."""
    it = PSN_MotionClean_Smooth.INPUT_TYPES()
    assert "required" in it
    assert "motion_data" in it["required"]
    assert "smoothing_window" in it["required"]
    assert "method" in it["required"]
    # method should be a combo of the three allowed values
    method_field = it["required"]["method"]
    assert method_field[0] == ["moving_average", "kalman", "spline"]
    # smoothing_window should be INT with min/max
    win_field = it["required"]["smoothing_window"]
    assert win_field[0] == "INT"
    assert win_field[1]["min"] >= 1
    assert win_field[1]["max"] >= 1
