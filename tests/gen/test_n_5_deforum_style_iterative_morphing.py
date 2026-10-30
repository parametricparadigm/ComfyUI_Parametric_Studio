"""
Tests for PSN_Iterative_Morphing_Engine (pure-logic morphing schedule).
No files, no network, no GPU.
"""

import json
import math
import pytest

from psn_nodes.gen.n_5_deforum_style_iterative_morphing import (
    PSN_Iterative_Morphing_Engine,
    _wave_value,
    _build_motion_curve,
    _compute_morph_params,
    _curve_to_json,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run_node(**kwargs):
    """Run the node with defaults, overriding with kwargs."""
    defaults = {
        "wave_function": "sine",
        "frequency": 0.1,
        "amplitude": 1.0,
        "num_frames": 10,
        "motion_strength": 1.0,
    }
    defaults.update(kwargs)
    node = PSN_Iterative_Morphing_Engine()
    return node.run(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sine_wave_frame5_differs_from_frame0():
    """Generate 10 frames with sine wave; frame 5 value != frame 0 value."""
    curve_json, params_json, count = _run_node(
        wave_function="sine",
        frequency=0.1,
        amplitude=1.0,
        num_frames=10,
        motion_strength=1.0,
    )
    assert count == 10
    curve = json.loads(curve_json)
    assert len(curve) == 10
    frame0_val = curve[0]["value"]
    frame5_val = curve[5]["value"]
    # With frequency 0.1, phase at frame 5 = 0.1*2*pi*5 = pi, sin(pi)~0
    # phase at frame 0 = 0, sin(0)=0 -> both near 0 but let's use a freq that differs
    # Use frequency 0.2 so frame 5 phase = 0.2*2*pi*5 = 2*pi -> sin=0, frame 0 sin=0
    # Better: frequency 0.05 -> frame 5 phase = 0.05*2*pi*5 = 0.5*pi, sin=1
    curve_json2, _, _ = _run_node(
        wave_function="sine",
        frequency=0.05,
        amplitude=1.0,
        num_frames=10,
        motion_strength=1.0,
    )
    curve2 = json.loads(curve_json2)
    f0 = curve2[0]["value"]
    f5 = curve2[5]["value"]
    assert abs(f0 - f5) > 0.1, f"frame0={f0}, frame5={f5} should differ"


def test_all_wave_modes_produce_valid_curves():
    """Each wave mode produces a curve of correct length and bounded values."""
    for mode in ["sine", "triangle", "saw", "beat"]:
        curve_json, params_json, count = _run_node(
            wave_function=mode,
            frequency=0.1,
            amplitude=2.0,
            num_frames=20,
            motion_strength=1.0,
        )
        assert count == 20
        curve = json.loads(curve_json)
        assert len(curve) == 20
        for entry in curve:
            assert "frame" in entry
            assert "value" in entry
            # amplitude is 2.0, wave in [-1,1], so value in [-2, 2]
            assert -2.0 - 1e-9 <= entry["value"] <= 2.0 + 1e-9


def test_morph_params_structure_and_scaling():
    """Morph params have correct keys and scale with motion_strength."""
    _, params_json, _ = _run_node(
        wave_function="sine",
        frequency=0.1,
        amplitude=1.0,
        num_frames=5,
        motion_strength=2.0,
    )
    params = json.loads(params_json)
    assert len(params) == 5
    for p in params:
        assert set(p.keys()) == {"frame", "wave_value", "warp_amount", "blur_amount", "color_shift"}
        # warp + blur + |color_shift| should relate to |wave_value| * motion_strength
        expected_total = abs(p["wave_value"]) * 2.0
        actual_total = p["warp_amount"] + p["blur_amount"] + abs(p["color_shift"])
        assert abs(actual_total - expected_total) < 1e-6


def test_zero_motion_strength_gives_zero_morph():
    """With motion_strength=0, all morph amounts are zero."""
    _, params_json, _ = _run_node(
        wave_function="sine",
        frequency=0.1,
        amplitude=1.0,
        num_frames=10,
        motion_strength=0.0,
    )
    params = json.loads(params_json)
    for p in params:
        assert p["warp_amount"] == 0.0
        assert p["blur_amount"] == 0.0
        assert p["color_shift"] == 0.0


def test_invalid_wave_function_raises():
    """An invalid wave function name raises ValueError."""
    with pytest.raises(ValueError, match="wave_function must be one of"):
        _run_node(wave_function="cosine")


def test_negative_frequency_raises():
    """Negative frequency raises ValueError."""
    with pytest.raises(ValueError, match="frequency must be >= 0"):
        _run_node(frequency=-0.1)


def test_zero_num_frames_raises():
    """num_frames=0 raises ValueError."""
    with pytest.raises(ValueError, match="num_frames must be >= 1"):
        _run_node(num_frames=0)


def test_negative_amplitude_raises():
    """Negative amplitude raises ValueError."""
    with pytest.raises(ValueError, match="amplitude must be >= 0"):
        _run_node(amplitude=-1.0)


def test_negative_motion_strength_raises():
    """Negative motion_strength raises ValueError."""
    with pytest.raises(ValueError, match="motion_strength must be >= 0"):
        _run_node(motion_strength=-0.5)


def test_large_frame_count_smoke():
    """Generate 100 frames; verify no errors and correct length."""
    curve_json, params_json, count = _run_node(
        wave_function="saw",
        frequency=0.05,
        amplitude=1.5,
        num_frames=100,
        motion_strength=0.8,
    )
    assert count == 100
    curve = json.loads(curve_json)
    params = json.loads(params_json)
    assert len(curve) == 100
    assert len(params) == 100
    # Verify frame indices are sequential
    for i, entry in enumerate(curve):
        assert entry["frame"] == i


def test_wave_value_bounds():
    """Each wave function stays within [-1, 1] for many phases."""
    for mode in ["sine", "triangle", "saw", "beat"]:
        for i in range(200):
            phase = i * 0.1
            v = _wave_value(mode, phase)
            assert -1.0 - 1e-9 <= v <= 1.0 + 1e-9, f"{mode} at phase {phase}: {v}"


def test_curve_json_is_valid_json():
    """The motion curve output is valid JSON and parseable."""
    curve_json, _, _ = _run_node(
        wave_function="triangle",
        frequency=0.2,
        amplitude=1.0,
        num_frames=8,
        motion_strength=1.0,
    )
    parsed = json.loads(curve_json)
    assert isinstance(parsed, list)
    assert len(parsed) == 8
    for item in parsed:
        assert isinstance(item["frame"], int)
        assert isinstance(item["value"], float)
