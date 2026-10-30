"""Tests for the PSN_Character_Prompt_Builder node."""

import pytest

from psn_nodes.gen.n_3_structured_character_prompt_builder import (
    PSN_Character_Prompt_Builder,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _clean_field,
    _split_accessories,
    _build_negative_prompt,
    _truncate,
)


def _run(builder, **overrides):
    kwargs = {
        "identity": "a young woman",
        "hair_style": "long wavy",
        "hair_color": "auburn",
        "accessories": "glasses, earrings",
        "pose": "standing",
        "outfit": "red dress",
        "background": "studio",
        "style_modifiers": "photorealistic",
        "include_negative": True,
        "character_type": "character",
        "max_length": 0,
    }
    kwargs.update(overrides)
    return builder.run(**kwargs)


def test_full_fields_order_and_comma_separation():
    builder = PSN_Character_Prompt_Builder()
    positive, negative = _run(builder)
    expected = (
        "a young woman, long wavy, auburn, red dress, glasses, earrings, "
        "standing, studio, photorealistic"
    )
    assert positive == expected
    assert "low quality" in negative
    assert "extra limbs" in negative


def test_empty_fields_are_omitted():
    builder = PSN_Character_Prompt_Builder()
    positive, _ = _run(
        builder,
        identity="a man",
        hair_style="",
        hair_color="   ",
        accessories="",
        pose="",
        outfit="suit",
        background="",
        style_modifiers="",
    )
    assert positive == "a man, suit"
    assert ",," not in positive
    assert not positive.startswith(",")
    assert not positive.endswith(",")


def test_accessories_split_into_individual_tokens():
    builder = PSN_Character_Prompt_Builder()
    positive, _ = _run(
        builder,
        identity="hero",
        hair_style="",
        hair_color="",
        accessories="  hat ,  scarf ,, ring  ",
        pose="",
        outfit="",
        background="",
        style_modifiers="",
    )
    assert positive == "hero, hat, scarf, ring"


def test_whitespace_normalization():
    builder = PSN_Character_Prompt_Builder()
    positive, _ = _run(
        builder,
        identity="  a   tall  man  ",
        hair_style="",
        hair_color="",
        accessories="",
        pose="",
        outfit="",
        background="",
        style_modifiers="",
    )
    assert positive == "a tall man"


def test_negative_prompt_disabled():
    builder = PSN_Character_Prompt_Builder()
    positive, negative = _run(builder, include_negative=False)
    assert positive != ""
    assert negative == ""


def test_negative_prompt_varies_by_character_type():
    builder = PSN_Character_Prompt_Builder()
    _, portrait_neg = _run(builder, character_type="portrait")
    _, animal_neg = _run(builder, character_type="animal")
    assert "watermark" in portrait_neg
    assert "human face" in animal_neg
    assert "low quality" in portrait_neg
    assert "low quality" in animal_neg


def test_max_length_truncates_positive_prompt():
    builder = PSN_Character_Prompt_Builder()
    positive, _ = _run(builder, max_length=10)
    assert len(positive) <= 10
    assert not positive.endswith(",")
    assert not positive.endswith(" ")


def test_max_length_zero_means_no_truncation():
    builder = PSN_Character_Prompt_Builder()
    positive_zero, _ = _run(builder, max_length=0)
    positive_default, _ = _run(builder)
    assert positive_zero == positive_default


def test_bad_input_none_values_are_safe():
    builder = PSN_Character_Prompt_Builder()
    positive, negative = _run(
        builder,
        identity=None,
        hair_style=None,
        hair_color=None,
        accessories=None,
        pose=None,
        outfit=None,
        background=None,
        style_modifiers=None,
    )
    assert positive == ""
    assert negative != ""


def test_all_empty_inputs_produce_empty_positive():
    builder = PSN_Character_Prompt_Builder()
    positive, negative = _run(
        builder,
        identity="",
        hair_style="",
        hair_color="",
        accessories="",
        pose="",
        outfit="",
        background="",
        style_modifiers="",
    )
    assert positive == ""
    assert negative != ""


def test_helper_clean_field():
    assert _clean_field("  a   b  ") == "a b"
    assert _clean_field(None) == ""
    assert _clean_field("   ") == ""
    assert _clean_field(123) == "123"


def test_helper_split_accessories():
    assert _split_accessories("a, b,,c") == ["a", "b", "c"]
    assert _split_accessories(None) == []
    assert _split_accessories("  ") == []


def test_helper_truncate():
    assert _truncate("hello world", 5) == "hello"
    assert _truncate("hello, world", 6) == "hello"
    assert _truncate("short", 10) == "short"
    assert _truncate("hello", 0) == "hello"


def test_node_mappings_registered():
    assert "PSN_Character_Prompt_Builder" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Character_Prompt_Builder"] is PSN_Character_Prompt_Builder
    assert "PSN_Character_Prompt_Builder" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_schema_shape():
    schema = PSN_Character_Prompt_Builder.INPUT_TYPES()
    assert "required" in schema and "optional" in schema
    for key in (
        "identity",
        "hair_style",
        "hair_color",
        "accessories",
        "pose",
        "outfit",
        "background",
        "style_modifiers",
        "include_negative",
    ):
        assert key in schema["required"]
    assert "character_type" in schema["optional"]
    assert "max_length" in schema["optional"]
    assert PSN_Character_Prompt_Builder.RETURN_TYPES == ("STRING", "STRING")
    assert PSN_Character_Prompt_Builder.FUNCTION == "run"
