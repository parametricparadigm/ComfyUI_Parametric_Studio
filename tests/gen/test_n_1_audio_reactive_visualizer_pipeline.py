import json
import math

from psn_nodes.gen.n_1_audio_reactive_visualizer_pipeline import (
    PSN_Audio_Amplitude_Extractor,
    PSN_Audio_Reactive_Driver,
    _psn_parse_float_list,
    _psn_rms,
    _psn_smooth,
)


def _sine(freq, rate, seconds, amp=1.0):
    n = int(seconds * rate)
    return [amp * math.sin(2 * math.pi * freq * i / rate) for i in range(n)]


def test_extractor_sine_low_band_peak_near_one():
    rate = 44100
    samples = _sine(100, rate, 0.5)
    node = PSN_Audio_Amplitude_Extractor()
    curve_json, peak = node.run(json.dumps(samples), 1024, 512, "low", rate)
    curve = json.loads(curve_json)
    assert len(curve) > 0
    assert peak > 0.0
    # The normalized curve should reach near 1.0 somewhere.
    assert max(curve) > 0.9


def test_extractor_sine_high_band_low_energy():
    rate = 44100
    samples = _sine(100, rate, 0.5)
    node = PSN_Audio_Amplitude_Extractor()
    low_json, low_peak = node.run(json.dumps(samples), 1024, 512, "low", rate)
    high_json, high_peak = node.run(json.dumps(samples), 1024, 512, "high", rate)
    # A 100 Hz sine has little high-frequency (difference) energy relative to low.
    assert high_peak < low_peak


def test_extractor_bad_json_returns_empty():
    node = PSN_Audio_Amplitude_Extractor()
    curve_json, peak = node.run("not json", 1024, 512, "full", 44100)
    assert json.loads(curve_json) == []
    assert peak == 0.0


def test_extractor_non_numeric_element_rejected():
    node = PSN_Audio_Amplitude_Extractor()
    curve_json, peak = node.run(json.dumps([0.1, "x", 0.2]), 1024, 512, "full", 44100)
    assert json.loads(curve_json) == []
    assert peak == 0.0


def test_extractor_too_short_audio_empty():
    node = PSN_Audio_Amplitude_Extractor()
    curve_json, peak = node.run(json.dumps([0.1, 0.2]), 1024, 512, "full", 44100)
    assert json.loads(curve_json) == []
    assert peak == 0.0


def test_driver_constant_half_maps_to_midpoint():
    curve = [0.5] * 10
    node = PSN_Audio_Reactive_Driver()
    val, curve_json = node.run(json.dumps(curve), "scale", 0.0, 2.0, 0.0, 0)
    assert abs(val - 1.0) < 1e-9
    mapped = json.loads(curve_json)
    assert all(abs(v - 1.0) < 1e-9 for v in mapped)


def test_driver_smoothing_reduces_step_response():
    curve = [0.0] * 5 + [1.0] * 5
    node = PSN_Audio_Reactive_Driver()
    raw_val, _ = node.run(json.dumps(curve), "brightness", 0.0, 1.0, 0.0, 5)
    smooth_val, _ = node.run(json.dumps(curve), "brightness", 0.0, 1.0, 0.8, 5)
    # With smoothing, the value at the step should be less than the raw 1.0.
    assert smooth_val < raw_val


def test_driver_frame_index_clamped():
    curve = [0.0, 0.5, 1.0]
    node = PSN_Audio_Reactive_Driver()
    val, _ = node.run(json.dumps(curve), "scale", 0.0, 1.0, 0.0, 999)
    assert abs(val - 1.0) < 1e-9


def test_parse_float_list_rejects_nan():
    ok, res = _psn_parse_float_list(json.dumps([0.1, float("nan")]))
    assert not ok


def test_smooth_alpha_zero_returns_raw():
    vals = [0.1, 0.5, 0.9]
    assert _psn_smooth(vals, 0.0) == vals


def test_rms_empty_is_zero():
    assert _psn_rms([]) == 0.0
