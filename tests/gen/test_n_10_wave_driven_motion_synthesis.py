"""Tests for PSN_Wave_Motion_Synthesizer (pure-logic wave combination)."""

import json
import math

import pytest

from psn_nodes.gen.n_10_wave_driven_motion_synthesis import (
    PSN_Wave_Motion_Synthesizer,
    _parse_wave,
    _combine,
    _wave_value,
)


def _sine(amp=1.0, freq=1.0, phase=0.0):
    return json.dumps({"type": "sine", "amplitude": amp, "frequency": freq, "phase": phase})


def _const(amp=1.0):
    return json.dumps({"type": "constant", "amplitude": amp})


def test_add_two_identical_sines_doubles_amplitude():
    node = PSN_Wave_Motion_Synthesizer()
    w1 = _sine(amp=1.0, freq=1.0)
    w2 = _sine(amp=1.0, freq=1.0)
    combined, motion_value, motion_values_json = node.run(w1, w2, "add", 8)
    values = json.loads(motion_values_json)
    assert len(values) == 8
    # At t=0.25 (frame 2 of 8), sin(2*pi*0.25)=1, so each wave=1, sum=2
    expected = 2.0 * math.sin(2.0 * math.pi * (2 / 8.0))
    assert values[2] == pytest.approx(expected, rel=1e-9)
    # Amplitude of combined sine should be 2.0
    max_val = max(abs(v) for v in values)
    assert max_val == pytest.approx(2.0, rel=1e-6)


def test_multiply_two_sines():
    node = PSN_Wave_Motion_Synthesizer()
    w1 = _sine(amp=2.0, freq=1.0)
    w2 = _sine(amp=3.0, freq=1.0)
    combined, motion_value, motion_values_json = node.run(w1, w2, "multiply", 4)
    values = json.loads(motion_values_json)
    # At t=0.25 (frame 1 of 4), sin(pi/2)=1, so 2*1 * 3*1 = 6
    assert values[1] == pytest.approx(6.0, rel=1e-9)


def test_modulate_operation():
    node = PSN_Wave_Motion_Synthesizer()
    w1 = _sine(amp=1.0, freq=1.0)
    w2 = _const(amp=0.5)
    combined, motion_value, motion_values_json = node.run(w1, w2, "modulate", 4)
    values = json.loads(motion_values_json)
    # modulate: v1 * (1 + v2) = sin(2*pi*t) * 1.5
    for i in range(4):
        t = i / 4.0
        expected = math.sin(2.0 * math.pi * t) * 1.5
        assert values[i] == pytest.approx(expected, rel=1e-9)


def test_smoke_100_frames_no_errors():
    node = PSN_Wave_Motion_Synthesizer()
    w1 = _sine(amp=1.0, freq=2.0)
    w2 = _sine(amp=0.5, freq=3.0, phase=0.5)
    combined, motion_value, motion_values_json = node.run(w1, w2, "add", 100)
    values = json.loads(motion_values_json)
    assert len(values) == 100
    assert all(math.isfinite(v) for v in values)
    assert isinstance(combined, str)
    parsed_combined = json.loads(combined)
    assert parsed_combined["operation"] == "add"


def test_bad_wave_json_raises():
    node = PSN_Wave_Motion_Synthesizer()
    with pytest.raises(ValueError):
        node.run("not json", _sine(), "add", 10)


def test_unsupported_wave_type_raises():
    node = PSN_Wave_Motion_Synthesizer()
    bad = json.dumps({"type": "square", "amplitude": 1.0})
    with pytest.raises(ValueError):
        node.run(bad, _sine(), "add", 10)


def test_unsupported_operation_raises():
    node = PSN_Wave_Motion_Synthesizer()
    with pytest.raises(ValueError):
        node.run(_sine(), _sine(), "subtract", 10)


def test_num_frames_zero_raises():
    node = PSN_Wave_Motion_Synthesizer()
    with pytest.raises(ValueError):
        node.run(_sine(), _sine(), "add", 0)


def test_current_frame_out_of_range_wraps_to_zero():
    node = PSN_Wave_Motion_Synthesizer()
    w1 = _sine(amp=1.0, freq=1.0)
    w2 = _const(amp=0.0)
    combined, motion_value, motion_values_json = node.run(w1, w2, "add", 4, current_frame=99)
    values = json.loads(motion_values_json)
    assert motion_value == pytest.approx(values[0], rel=1e-9)


def test_parse_wave_non_string_raises():
    with pytest.raises(ValueError):
        _parse_wave(12345)


def test_wave_value_constant():
    wave = _parse_wave(_const(amp=3.0))
    assert _wave_value(wave, 0.0) == pytest.approx(3.0)
    assert _wave_value(wave, 0.5) == pytest.approx(3.0)
    assert _wave_value(wave, 1.0) == pytest.approx(3.0)
