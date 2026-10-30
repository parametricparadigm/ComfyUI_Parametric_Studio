"""Tests for PSN_FramerateConverter pure-logic node."""

import json
import math

import pytest

from psn_nodes.gen.psn_framerateconverter import (
    PSN_FramerateConverter,
    _compute_frame_mapping,
    _validate_fps,
    _build_payload,
)


def test_basic_30_to_60_fps():
    """Converting 30fps to 60fps should double the frame count."""
    node = PSN_FramerateConverter()
    payload_json, mapping_json, target_count = node.run(
        source_fps=30.0, target_fps=60.0, source_frame_count=30
    )
    assert target_count == 60
    mapping = json.loads(mapping_json)
    assert len(mapping) == 60
    # Each source frame should appear roughly twice
    # Frame 0 -> 0, Frame 1 -> 0 or 1, etc.
    assert mapping[0] == 0
    assert mapping[-1] == 29
    payload = json.loads(payload_json)
    assert payload["source_fps"] == 30.0
    assert payload["target_fps"] == 60.0
    assert payload["target_frame_count"] == 60


def test_downscale_60_to_30_fps():
    """Converting 60fps to 30fps should halve the frame count."""
    node = PSN_FramerateConverter()
    payload_json, mapping_json, target_count = node.run(
        source_fps=60.0, target_fps=30.0, source_frame_count=60
    )
    assert target_count == 30
    mapping = json.loads(mapping_json)
    assert len(mapping) == 30
    # Should pick every other frame approximately
    assert mapping[0] == 0
    # Last target frame index is 29, ratio is 2.0, so 29*2=58
    assert mapping[-1] == 58


def test_same_fps_identity():
    """Same source and target FPS should produce identity mapping."""
    node = PSN_FramerateConverter()
    payload_json, mapping_json, target_count = node.run(
        source_fps=24.0, target_fps=24.0, source_frame_count=48
    )
    assert target_count == 48
    mapping = json.loads(mapping_json)
    assert mapping == list(range(48))


def test_invalid_zero_source_fps():
    """source_fps of 0 should raise ValueError."""
    node = PSN_FramerateConverter()
    with pytest.raises(ValueError, match="source_fps must be positive"):
        node.run(source_fps=0.0, target_fps=60.0, source_frame_count=30)


def test_invalid_negative_target_fps():
    """Negative target_fps should raise ValueError."""
    node = PSN_FramerateConverter()
    with pytest.raises(ValueError, match="target_fps must be positive"):
        node.run(source_fps=30.0, target_fps=-10.0, source_frame_count=30)


def test_invalid_nan_fps():
    """NaN fps should raise ValueError."""
    node = PSN_FramerateConverter()
    with pytest.raises(ValueError, match="finite number"):
        node.run(source_fps=float("nan"), target_fps=60.0, source_frame_count=30)


def test_invalid_non_numeric_fps():
    """Non-numeric fps should raise ValueError."""
    node = PSN_FramerateConverter()
    with pytest.raises(ValueError, match="must be a number"):
        node.run(source_fps="30", target_fps=60.0, source_frame_count=30)


def test_invalid_zero_frame_count():
    """source_frame_count of 0 should raise ValueError."""
    node = PSN_FramerateConverter()
    with pytest.raises(ValueError, match="positive integer"):
        node.run(source_fps=30.0, target_fps=60.0, source_frame_count=0)


def test_single_frame_upscale():
    """A single frame at any fps should still produce at least one target frame."""
    node = PSN_FramerateConverter()
    payload_json, mapping_json, target_count = node.run(
        source_fps=1.0, target_fps=60.0, source_frame_count=1
    )
    assert target_count >= 1
    mapping = json.loads(mapping_json)
    assert all(idx == 0 for idx in mapping)


def test_payload_structure():
    """Payload should contain all expected keys with correct types."""
    node = PSN_FramerateConverter()
    payload_json, _, _ = node.run(
        source_fps=25.0, target_fps=50.0, source_frame_count=100, job_id="test_job_123"
    )
    payload = json.loads(payload_json)
    assert payload["job_id"] == "test_job_123"
    assert payload["operation"] == "framerate_convert"
    assert payload["method"] == "nearest_neighbor"
    assert isinstance(payload["frame_mapping"], list)
    assert len(payload["frame_mapping"]) == payload["target_frame_count"]
    assert payload["source_frame_count"] == 100


def test_frame_mapping_bounds():
    """All mapped indices should be within valid source frame range."""
    node = PSN_FramerateConverter()
    _, mapping_json, _ = node.run(
        source_fps=10.0, target_fps=100.0, source_frame_count=5
    )
    mapping = json.loads(mapping_json)
    for idx in mapping:
        assert 0 <= idx <= 4


def test_validate_fps_helper():
    """_validate_fps should accept valid values and reject invalid ones."""
    assert _validate_fps(30.0) == 30.0
    assert _validate_fps(1) == 1.0
    with pytest.raises(ValueError):
        _validate_fps(-1.0)
    with pytest.raises(ValueError):
        _validate_fps(float("inf"))
    with pytest.raises(ValueError):
        _validate_fps("30")
