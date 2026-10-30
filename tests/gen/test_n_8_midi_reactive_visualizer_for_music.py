import json

import pytest

from psn_nodes.gen.n_8_midi_reactive_visualizer_for_music import (
    PSN_MIDI_Visualizer,
    _parse_events,
    _build_frames,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _make_node():
    return PSN_MIDI_Visualizer()


def test_parse_events_pipe_form_valid():
    text = "0.0|60|100|on;0.125|60|0|off;0.25|64|127|on"
    events, error = _parse_events(text)
    assert error is None
    assert events == [(0.0, 60, 100, "on"), (0.125, 60, 0, "off"), (0.25, 64, 127, "on")]


def test_parse_events_json_form_valid():
    text = json.dumps([
        {"time": 0.0, "note": 60, "velocity": 100, "type": "on"},
        {"time": 0.5, "note": 64, "velocity": 127, "type": "on"},
    ])
    events, error = _parse_events(text)
    assert error is None
    assert len(events) == 2
    assert events[0] == (0.0, 60, 100, "on")
    assert events[1] == (0.5, 64, 127, "on")


def test_parse_events_bad_note_range():
    text = "0.0|200|100|on"
    events, error = _parse_events(text)
    assert events is None
    assert "note out of range" in error


def test_parse_events_bad_type():
    text = "0.0|60|100|hold"
    events, error = _parse_events(text)
    assert events is None
    assert "invalid type" in error


def test_parse_events_empty_input():
    events, error = _parse_events("   ")
    assert events is None
    assert "empty" in error


def test_parse_events_non_string_input():
    events, error = _parse_events(12345)
    assert events is None
    assert "must be a string" in error


def test_run_bars_style_produces_frames():
    node = _make_node()
    midi = "0.0|60|100|on;0.1|64|127|on;0.2|67|90|on"
    video, status = node.run(midi, "bars", 1.0, fps=30.0, duration=1.0)
    assert status.startswith("ok:")
    payload = json.loads(video)
    assert payload["style"] == "bars"
    assert payload["frame_count"] > 0
    assert all("bars" in frame for frame in payload["frames"])


def test_run_particles_style_produces_particles():
    node = _make_node()
    midi = "0.0|60|100|on;0.1|64|127|on"
    video, status = node.run(midi, "particles", 2.0, fps=24.0, duration=0.5)
    assert status.startswith("ok:")
    payload = json.loads(video)
    assert payload["style"] == "particles"
    assert all("particles" in frame for frame in payload["frames"])


def test_run_waveform_style_produces_waveform():
    node = _make_node()
    midi = "0.0|60|100|on;0.1|64|127|on;0.2|67|90|on"
    video, status = node.run(midi, "waveform", 1.5, fps=30.0, duration=1.0)
    assert status.startswith("ok:")
    payload = json.loads(video)
    assert payload["style"] == "waveform"
    assert all("waveform" in frame for frame in payload["frames"])


def test_run_invalid_style_reports_error():
    node = _make_node()
    video, status = node.run("0.0|60|100|on", "spirograph", 1.0)
    assert status.startswith("error:")
    payload = json.loads(video)
    assert "error" in payload


def test_run_invalid_midi_reports_error():
    node = _make_node()
    video, status = node.run("0.0|60|100|hold", "bars", 1.0)
    assert status.startswith("error:")
    payload = json.loads(video)
    assert "error" in payload


def test_run_sensitivity_clamped_and_reactivity_scales():
    node = _make_node()
    midi = "0.0|60|127|on"
    video_low, _ = node.run(midi, "bars", 0.0, fps=30.0, duration=0.5)
    video_high, _ = node.run(midi, "bars", 100.0, fps=30.0, duration=0.5)
    low = json.loads(video_low)
    high = json.loads(video_high)
    assert low["sensitivity"] == 0.0
    assert high["sensitivity"] == 100.0
    assert low["frames"][0]["reactivity"] == 0.0
    assert high["frames"][0]["reactivity"] > 0.0


def test_build_frames_single_event_zero_duration_fallback():
    events = [(0.0, 60, 100, "on")]
    frames, frame_count, duration = _build_frames(events, "bars", 1.0, 30.0, 0.0)
    assert duration == 1.0
    assert frame_count >= 1
    assert len(frames) == frame_count


def test_node_mappings_registered():
    assert "PSN_MIDI_Visualizer" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_MIDI_Visualizer"] is PSN_MIDI_Visualizer
    assert "PSN_MIDI_Visualizer" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_shape():
    spec = PSN_MIDI_Visualizer.INPUT_TYPES()
    assert "midi_data" in spec["required"]
    assert "visual_style" in spec["required"]
    assert "sensitivity" in spec["required"]
    assert "fps" in spec["optional"]
    assert "duration" in spec["optional"]
    assert PSN_MIDI_Visualizer.RETURN_NAMES == ("video", "status")
    assert PSN_MIDI_Visualizer.FUNCTION == "run"
