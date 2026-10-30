"""
Tests for psn_nodes.gen.n_4_multi_shot_timeline_direction.

Covers:
- Valid 2-scene timeline: schedule values change at the boundary.
- 200-frame timeline with 2 scenes: no gaps or overlaps.
- Invalid JSON input.
- Overlapping scenes rejected.
- Bad curve shape rejected.
- Transition weights for cut / fade / dissolve.
- Bad transition type rejected.
- Bad duration rejected.
"""

import json

import pytest

from psn_nodes.gen.n_4_multi_shot_timeline_direction import (
    PSN_TimelineDirector,
    PSN_SceneTransition,
    _build_schedule,
    _parse_scene,
    _transition_weights,
)


def _director():
    return PSN_TimelineDirector()


def _transition():
    return PSN_SceneTransition()


def test_timeline_two_scenes_boundary_change():
    """Schedule values should change at the scene boundary."""
    scenes = [
        {"start_frame": 0, "end_frame": 100, "camera_curve": "linear", "energy_curve": "linear"},
        {"start_frame": 100, "end_frame": 200, "camera_curve": "ease_in", "energy_curve": "ease_out"},
    ]
    scenes_json = json.dumps(scenes)
    schedule_json, boundaries_json = _director().run(scenes_json, 200)
    schedule = json.loads(schedule_json)
    boundaries = json.loads(boundaries_json)

    # Boundaries should include frame 100.
    assert 100 in boundaries

    # Frame 99 is in scene 0, frame 100 is in scene 1.
    frame_99 = schedule[99]
    frame_100 = schedule[100]
    assert frame_99["scene_index"] == 0
    assert frame_100["scene_index"] == 1

    # Camera value at frame 99 (end of scene 0, linear) should be 1.0.
    assert frame_99["camera"] == pytest.approx(1.0)
    # Camera value at frame 100 (start of scene 1, ease_in) should be 0.0.
    assert frame_100["camera"] == pytest.approx(0.0)


def test_timeline_200_frames_no_gaps_or_overlaps():
    """A 200-frame timeline with 2 scenes should have exactly 200 entries."""
    scenes = [
        {"start_frame": 0, "end_frame": 100, "camera_curve": "linear", "energy_curve": "linear"},
        {"start_frame": 100, "end_frame": 200, "camera_curve": "linear", "energy_curve": "linear"},
    ]
    scenes_json = json.dumps(scenes)
    schedule_json, _ = _director().run(scenes_json, 200)
    schedule = json.loads(schedule_json)

    assert len(schedule) == 200
    # Verify frame indices are contiguous.
    for i, entry in enumerate(schedule):
        assert entry["frame"] == i


def test_timeline_invalid_json():
    """Invalid JSON should raise ValueError."""
    with pytest.raises(ValueError, match="not valid JSON"):
        _director().run("not json", 100)


def test_timeline_overlapping_scenes_rejected():
    """Overlapping scenes should be rejected."""
    scenes = [
        {"start_frame": 0, "end_frame": 100, "camera_curve": "linear", "energy_curve": "linear"},
        {"start_frame": 50, "end_frame": 150, "camera_curve": "linear", "energy_curve": "linear"},
    ]
    scenes_json = json.dumps(scenes)
    with pytest.raises(ValueError, match="overlaps"):
        _director().run(scenes_json, 200)


def test_timeline_bad_curve_shape_rejected():
    """An unknown curve shape should be rejected."""
    scenes = [
        {"start_frame": 0, "end_frame": 100, "camera_curve": "bogus", "energy_curve": "linear"},
    ]
    scenes_json = json.dumps(scenes)
    with pytest.raises(ValueError, match="camera_curve"):
        _director().run(scenes_json, 100)


def test_transition_cut_weights():
    """Cut transition should produce all 1.0 weights."""
    weights_json, _ = _transition().run("cut", 5)
    weights = json.loads(weights_json)
    assert len(weights) == 5
    assert all(w == 1.0 for w in weights)


def test_transition_fade_weights():
    """Fade transition should produce a linear ramp from 0 to 1."""
    weights_json, _ = _transition().run("fade", 5)
    weights = json.loads(weights_json)
    assert len(weights) == 5
    assert weights[0] == pytest.approx(0.0)
    assert weights[-1] == pytest.approx(1.0)
    # Middle should be 0.5.
    assert weights[2] == pytest.approx(0.5)


def test_transition_dissolve_weights():
    """Dissolve transition should produce a smoothstep ramp."""
    weights_json, _ = _transition().run("dissolve", 5)
    weights = json.loads(weights_json)
    assert len(weights) == 5
    assert weights[0] == pytest.approx(0.0)
    assert weights[-1] == pytest.approx(1.0)
    # Smoothstep at t=0.5 is 0.5.
    assert weights[2] == pytest.approx(0.5)


def test_transition_bad_type_rejected():
    """An unknown transition type should be rejected."""
    with pytest.raises(ValueError, match="transition_type"):
        _transition().run("bogus", 5)


def test_transition_bad_duration_rejected():
    """A non-positive duration should be rejected."""
    with pytest.raises(ValueError, match="duration"):
        _transition().run("fade", 0)


def test_transition_single_frame():
    """A 1-frame transition should produce a single weight of 1.0."""
    weights_json, _ = _transition().run("fade", 1)
    weights = json.loads(weights_json)
    assert weights == [1.0]
