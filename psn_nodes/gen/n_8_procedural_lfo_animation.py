"""
PSN_LFO_Generator: Procedural Low-Frequency Oscillator (LFO) signal generator.

Generates a continuous oscillating signal (sine, triangle, square, or saw)
over a specified duration at a given sample rate. The signal is returned as
a list of float values (representing a keyframed curve) and the current
value at a specified frame index.

Pure Python standard library only. No numpy, no torch, no file/network I/O.
"""

import math
import json

# Allowed wave types
WAVE_TYPES = ["sine", "triangle", "square", "saw"]

# Category for the node
CAT = "ParametricStudio/Animation"


def _generate_lfo(wave_type, frequency, amplitude, phase, duration, sample_rate):
    """
    Generate an LFO signal as a list of float values.

    Args:
        wave_type: One of "sine", "triangle", "square", "saw".
        frequency: Frequency in Hz.
        amplitude: Peak amplitude of the LFO.
        phase: Initial phase offset in radians.
        duration: Duration in seconds.
        sample_rate: Number of samples per second.

    Returns:
        List of float values representing the LFO signal.
    """
    if wave_type not in WAVE_TYPES:
        raise ValueError(f"Invalid wave_type: {wave_type}. Must be one of {WAVE_TYPES}")
    if frequency < 0:
        raise ValueError("Frequency must be non-negative")
    if duration < 0:
        raise ValueError("Duration must be non-negative")
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")

    num_samples = max(1, int(duration * sample_rate))
    signal = []

    for i in range(num_samples):
        t = i / sample_rate
        # Normalize time to cycles: t * frequency gives cycles, multiply by 2*pi for radians
        angle = 2.0 * math.pi * frequency * t + phase

        if wave_type == "sine":
            value = math.sin(angle)
        elif wave_type == "triangle":
            # Triangle wave: period 2*pi, range [-1, 1]
            # Use the formula: 2/pi * arcsin(sin(x))
            value = (2.0 / math.pi) * math.asin(math.sin(angle))
        elif wave_type == "square":
            # Square wave: +1 when sin(angle) >= 0, -1 otherwise
            value = 1.0 if math.sin(angle) >= 0 else -1.0
        elif wave_type == "saw":
            # Sawtooth wave: period 2*pi, range [-1, 1]
            # Normalize angle to [0, 2*pi), then map to [-1, 1]
            angle_mod = angle % (2.0 * math.pi)
            # angle_mod is in [0, 2*pi). Map to [-1, 1]:
            # At 0 -> -1, at pi -> 0, at 2*pi -> 1
            value = (angle_mod / math.pi) - 1.0
        else:
            raise ValueError(f"Invalid wave_type: {wave_type}")

        signal.append(amplitude * value)

    return signal


def _get_current_value(signal, frame_index):
    """
    Get the current LFO value at a given frame index.

    Args:
        signal: List of float values.
        frame_index: Integer index into the signal.

    Returns:
        The float value at the given index, or 0.0 if out of bounds.
    """
    if not signal:
        return 0.0
    if frame_index < 0 or frame_index >= len(signal):
        return 0.0
    return signal[frame_index]


class PSN_LFO_Generator:
    """
    Generates a procedural LFO signal for animation parameters.

    Outputs:
        lfo_curve: A JSON string representing the LFO signal as a list of floats.
        lfo_signal: The current LFO value at the specified frame index.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wave_type": (WAVE_TYPES,),
                "frequency": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1000.0, "step": 0.001}),
                "amplitude": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "phase": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "duration": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1e6, "step": 0.001}),
                "sample_rate": ("INT", {"default": 44100, "min": 1, "max": 1000000}),
            },
            "optional": {
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 10000000}),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("lfo_curve", "lfo_signal")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, wave_type, frequency, amplitude, phase, duration, sample_rate, frame_index=0):
        """
        Generate the LFO signal and return the curve as JSON and the current value.

        Args:
            wave_type: Type of wave ("sine", "triangle", "square", "saw").
            frequency: Frequency in Hz.
            amplitude: Peak amplitude.
            phase: Initial phase offset in radians.
            duration: Duration in seconds.
            sample_rate: Samples per second.
            frame_index: Index into the signal for the current value.

        Returns:
            Tuple of (lfo_curve_json, lfo_signal_value).
        """
        signal = _generate_lfo(wave_type, frequency, amplitude, phase, duration, sample_rate)
        lfo_curve_json = json.dumps(signal)
        current_value = _get_current_value(signal, frame_index)
        return (lfo_curve_json, current_value)


NODE_CLASS_MAPPINGS = {
    "PSN_LFO_Generator": PSN_LFO_Generator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LFO_Generator": "PSN LFO Generator",
}
