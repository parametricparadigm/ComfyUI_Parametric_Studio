"""
Tests for PSN_Video_Storyboarder node.
"""

import json
import pytest

from psn_nodes.gen.n_4_multi_scene_video_storyboarder import PSN_Video_Storyboarder


def test_basic_two_scenes():
    """Unit test from spec: 2 scenes, templates with {style}, style 'cinematic'."""
    node = PSN_Video_Storyboarder()
    prompts_json, metadata_json = node.run(
        scene_count=2,
        scene_templates='["Scene 1: {style}", "Scene 2: {style}"]',
        global_style="cinematic",
        transition_type="cut",
    )
    prompts = json.loads(prompts_json)
    metadata = json.loads(metadata_json)
    assert len(prompts) == 2
    assert "cinematic" in prompts[0]
    assert "cinematic" in prompts[1]
    assert metadata["scene_count"] == 2
    assert metadata["transition_type"] == "cut"
    assert metadata["scene_indices"] == [0, 1]


def test_three_scenes_valid_json():
    """GPU smoke test equivalent: scene_count=3, verify valid JSON output."""
    node = PSN_Video_Storyboarder()
    prompts_json, metadata_json = node.run(
        scene_count=3,
        scene_templates='["Scene {i}: {style}"]',
        global_style="noir",
        transition_type="fade",
    )
    prompts = json.loads(prompts_json)
    metadata = json.loads(metadata_json)
    assert len(prompts) == 3
    assert all("noir" in p for p in prompts)
    assert metadata["scene_indices"] == [0, 1, 2]
    assert metadata["transition_type"] == "fade"


def test_template_cycling():
    """When scene_count > len(templates), templates should cycle."""
    node = PSN_Video_Storyboarder()
    prompts_json, _ = node.run(
        scene_count=4,
        scene_templates='["A: {style}", "B: {style}"]',
        global_style="vivid",
        transition_type="dissolve",
    )
    prompts = json.loads(prompts_json)
    assert len(prompts) == 4
    assert "A: vivid" in prompts[0]
    assert "B: vivid" in prompts[1]
    assert "A: vivid" in prompts[2]
    assert "B: vivid" in prompts[3]


def test_invalid_json_templates():
    """Malformed JSON in scene_templates should raise ValueError."""
    node = PSN_Video_Storyboarder()
    with pytest.raises(ValueError, match="valid JSON"):
        node.run(
            scene_count=1,
            scene_templates="not valid json",
            global_style="test",
            transition_type="cut",
        )


def test_templates_not_array():
    """scene_templates that is valid JSON but not an array should raise ValueError."""
    node = PSN_Video_Storyboarder()
    with pytest.raises(ValueError, match="JSON array"):
        node.run(
            scene_count=1,
            scene_templates='{"key": "value"}',
            global_style="test",
            transition_type="cut",
        )


def test_invalid_scene_count():
    """scene_count of 0 or negative should raise ValueError."""
    node = PSN_Video_Storyboarder()
    with pytest.raises(ValueError, match="positive integer"):
        node.run(
            scene_count=0,
            scene_templates='["{style}"]',
            global_style="test",
            transition_type="cut",
        )
    with pytest.raises(ValueError, match="positive integer"):
        node.run(
            scene_count=-1,
            scene_templates='["{style}"]',
            global_style="test",
            transition_type="cut",
        )


def test_invalid_transition_type():
    """Invalid transition_type should raise ValueError."""
    node = PSN_Video_Storyboarder()
    with pytest.raises(ValueError, match="transition_type"):
        node.run(
            scene_count=1,
            scene_templates='["{style}"]',
            global_style="test",
            transition_type="zoom",
        )


def test_single_scene_with_index_placeholder():
    """Verify {i} placeholder is replaced with scene index."""
    node = PSN_Video_Storyboarder()
    prompts_json, _ = node.run(
        scene_count=3,
        scene_templates='["Scene {i} in {style} mode"]',
        global_style="anime",
        transition_type="cut",
    )
    prompts = json.loads(prompts_json)
    assert prompts[0] == "Scene 0 in anime mode"
    assert prompts[1] == "Scene 1 in anime mode"
    assert prompts[2] == "Scene 2 in anime mode"


def test_empty_template_string():
    """Empty template string should still produce a prompt (empty after substitution)."""
    node = PSN_Video_Storyboarder()
    prompts_json, _ = node.run(
        scene_count=2,
        scene_templates='["", "{style}"]',
        global_style="dark",
        transition_type="fade",
    )
    prompts = json.loads(prompts_json)
    assert prompts[0] == ""
    assert prompts[1] == "dark"
