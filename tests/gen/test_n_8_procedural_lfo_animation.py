"""
Tests for PSN_LFO_Generator node.
"""

import json
import math
import pytest

from psn_nodes.gen.n_8_procedural_lfo_animation import (
    PSN_LFO_Generator,
    _generate_lfo,
    _get_current_value,
    WAVE_TYPES,
)


class TestPSNLFOGenerator:
    """Tests for the PSN_LFO_Generator node and helper functions."""

    def test_sine_wave_peak_and_trough(self):
        """Generate a 1Hz sine wave for 1 second; assert peak is 1.0 and trough is -1.0."""
        signal = _generate_lfo("sine", 1.0, 1.0, 0.0, 1.0, 1000)
        assert len(signal) == 1000
        peak = max(signal)
        trough = min(signal)
        # Allow small floating point tolerance
        assert abs(peak - 1.0) < 1e-6, f"Peak {peak} not close to 1.0"
        assert abs(trough - (-1.0)) < 1e-6, f"Trough {trough} not close to -1.0"

    def test_sine_wave_amplitude_scaling(self):
        """Sine wave with amplitude 2.0 should have peak 2.0 and trough -2.0."""
        signal = _generate_lfo("sine", 1.0, 2.0, 0.0, 1.0, 1000)
        peak = max(signal)
        trough = min(signal)
        assert abs(peak - 2.0) < 1e-6
        assert abs(trough - (-2.0)) < 1e-6

    def test_triangle_wave_range(self):
        """Triangle wave should stay within [-amplitude, amplitude]."""
        signal = _generate_lfo("triangle", 1.0, 1.0, 0.0, 1.0, 1000)
        for val in signal:
            assert -1.0 - 1e-9 <= val <= 1.0 + 1e-9, f"Value {val} out of range"
        # Check that it reaches close to 1.0 and -1.0
        assert max(signal) > 0.99
        assert min(signal) < -0.99

    def test_square_wave_values(self):
        """Square wave should only have values +amplitude or -amplitude."""
        signal = _generate_lfo("square", 1.0, 1.0, 0.0, 1.0, 1000)
        for val in signal:
            assert abs(abs(val) - 1.0) < 1e-9, f"Square wave value {val} not ±1.0"

    def test_saw_wave_range(self):
        """Saw wave should stay within [-amplitude, amplitude]."""
        signal = _generate_lfo("saw", 1.0, 1.0, 0.0, 1.0, 1000)
        for val in signal:
            assert -1.0 - 1e-9 <= val <= 1.0 + 1e-9, f"Saw value {val} out of range"

    def test_smoke_test_10_second_lfo(self):
        """Generate a 10-second LFO; verify no errors and correct length."""
        signal = _generate_lfo("sine", 1.0, 1.0, 0.0, 10.0, 100)
        assert len(signal) == 1000  # 10 seconds * 100 Hz
        # All values should be finite
        for val in signal:
            assert math.isfinite(val)

    def test_invalid_wave_type_raises(self):
        """Invalid wave type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid wave_type"):
            _generate_lfo("invalid", 1.0, 1.0, 0.0, 1.0, 100)

    def test_negative_frequency_raises(self):
        """Negative frequency should raise ValueError."""
        with pytest.raises(ValueError, match="Frequency must be non-negative"):
            _generate_lfo("sine", -1.0, 1.0, 0.0, 1.0, 100)

    def test_negative_duration_raises(self):
        """Negative duration should raise ValueError."""
        with pytest.raises(ValueError, match="Duration must be non-negative"):
            _generate_lfo("sine", 1.0, 1.0, 0.0, -1.0, 100)

    def test_zero_sample_rate_raises(self):
        """Zero or negative sample rate should raise ValueError."""
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            _generate_lfo("sine", 1.0, 1.0, 0.0, 1.0, 0)

    def test_node_run_returns_json_and_float(self):
        """Node run should return a JSON string and a float."""
        node = PSN_LFO_Generator()
        curve_json, current_val = node.run(
            wave_type="sine",
            frequency=1.0,
            amplitude=1.0,
            phase=0.0,
            duration=1.0,
            sample_rate=100,
            frame_index=0,
        )
        # curve_json should be valid JSON
        parsed = json.loads(curve_json)
        assert isinstance(parsed, list)
        assert len(parsed) == 100
        assert all(isinstance(x, float) for x in parsed)
        # current_val should be a float
        assert isinstance(current_val, float)

    def test_node_run_frame_index_out_of_bounds(self):
        """Frame index out of bounds should return 0.0."""
        node = PSN_LFO_Generator()
        curve_json, current_val = node.run(
            wave_type="sine",
            frequency=1.0,
            amplitude=1.0,
            phase=0.0,
            duration=1.0,
            sample_rate=100,
            frame_index=99999,
        )
        assert current_val == 0.0

    def test_get_current_value_empty_signal(self):
        """Empty signal should return 0.0."""
        assert _get_current_value([], 0) == 0.0

    def test_get_current_value_negative_index(self):
        """Negative index should return 0.0."""
        signal = [1.0, 2.0, 3.0]
        assert _get_current_value(signal, -1) == 0.0

    def test_phase_offset_shifts_sine(self):
        """Phase offset should shift the sine wave."""
        # Sine with phase 0 starts at 0
        signal_no_phase = _generate_lfo("sine", 1.0, 1.0, 0.0, 1.0, 1000)
        # Sine with phase pi/2 starts at 1.0
        signal_phase = _generate_lfo("sine", 1.0, 1.0, math.pi / 2, 1.0, 1000)
        assert abs(signal_no_phase[0] - 0.0) < 1e-6
        assert abs(signal_phase[0] - 1.0) < 1e-6

    def test_zero_frequency_constant_signal(self):
        """Zero frequency should produce a constant signal."""
        signal = _generate_lfo("sine", 0.0, 1.0, 0.0, 1.0, 100)
        # All values should be sin(0) = 0
        for val in signal:
            assert abs(val) < 1e-9

    def test_wave_types_list_is_complete(self):
        """WAVE_TYPES should contain all four expected types."""
        assert set(WAVE_TYPES) == {"sine", "triangle", "square", "saw"}
