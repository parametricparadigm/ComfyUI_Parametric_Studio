"""Tests for PSN_One_Click_Prompt_Generator."""

import pytest

from psn_nodes.gen.n_9_one_click_prompt_generator import (
    PSN_One_Click_Prompt_Generator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    THEMES,
)


def test_node_registered():
    assert "PSN_One_Click_Prompt_Generator" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_One_Click_Prompt_Generator"] is PSN_One_Click_Prompt_Generator
    assert "PSN_One_Click_Prompt_Generator" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_structure():
    it = PSN_One_Click_Prompt_Generator.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "theme" in req
    assert "complexity" in req
    assert "seed" in req
    # theme is a COMBO: (list_of_options,)
    assert req["theme"] == (THEMES,)
    assert req["complexity"][0] == "INT"
    assert req["seed"][0] == "INT"


def test_prompt_non_empty_and_string():
    node = PSN_One_Click_Prompt_Generator()
    prompt, neg = node.run(theme="fantasy", complexity=3, seed=1)
    assert isinstance(prompt, str)
    assert isinstance(neg, str)
    assert len(prompt) > 0
    assert len(neg) > 0


def test_same_seed_same_prompt():
    node = PSN_One_Click_Prompt_Generator()
    p1, n1 = node.run(theme="sci-fi", complexity=4, seed=42)
    p2, n2 = node.run(theme="sci-fi", complexity=4, seed=42)
    assert p1 == p2
    assert n1 == n2


def test_different_seed_may_differ():
    node = PSN_One_Click_Prompt_Generator()
    p1, _ = node.run(theme="realistic", complexity=2, seed=100)
    p2, _ = node.run(theme="realistic", complexity=2, seed=200)
    # With different seeds the prompt should (almost certainly) differ
    assert p1 != p2


def test_complexity_affects_detail_count():
    node = PSN_One_Click_Prompt_Generator()
    p_low, _ = node.run(theme="anime", complexity=1, seed=7)
    p_high, _ = node.run(theme="anime", complexity=5, seed=7)
    # Higher complexity should produce a longer prompt (more detail tokens)
    assert len(p_high) >= len(p_low)


def test_all_themes_produce_strings():
    node = PSN_One_Click_Prompt_Generator()
    for theme in THEMES:
        prompt, neg = node.run(theme=theme, complexity=3, seed=99)
        assert isinstance(prompt, str)
        assert isinstance(neg, str)
        assert len(prompt) > 0
        assert len(neg) > 0


def test_invalid_theme_raises():
    node = PSN_One_Click_Prompt_Generator()
    with pytest.raises(ValueError):
        node.run(theme="underwater", complexity=3, seed=1)


def test_invalid_complexity_raises():
    node = PSN_One_Click_Prompt_Generator()
    with pytest.raises(ValueError):
        node.run(theme="fantasy", complexity=0, seed=1)
    with pytest.raises(ValueError):
        node.run(theme="fantasy", complexity=6, seed=1)


def test_non_int_complexity_raises():
    node = PSN_One_Click_Prompt_Generator()
    with pytest.raises(TypeError):
        node.run(theme="fantasy", complexity="3", seed=1)


def test_non_int_seed_raises():
    node = PSN_One_Click_Prompt_Generator()
    with pytest.raises(TypeError):
        node.run(theme="fantasy", complexity=3, seed="1")


def test_negative_prompt_contains_base_terms():
    node = PSN_One_Click_Prompt_Generator()
    _, neg = node.run(theme="realistic", complexity=2, seed=5)
    # Base negative terms should always be present
    assert "low quality" in neg
    assert "blurry" in neg
