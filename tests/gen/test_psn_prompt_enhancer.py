"""Tests for the PSN_Prompt_Enhancer pure-logic core."""

import pytest

from psn_nodes.gen.psn_prompt_enhancer import (
    PSN_PromptEnhancer,
    build_system_prompt,
    parse_llm_response,
)


def test_build_system_prompt_contains_model_and_verbosity():
    sp = build_system_prompt("SDXL", 3)
    assert "SDXL" in sp
    assert "verbosity level 3" in sp
    assert "Positive:" in sp and "Negative:" in sp


def test_build_system_prompt_clamps_verbosity():
    low = build_system_prompt("Flux", 0)
    high = build_system_prompt("Flux", 99)
    assert "verbosity level 1" in low
    assert "verbosity level 5" in high


def test_build_system_prompt_rejects_unknown_model():
    with pytest.raises(ValueError):
        build_system_prompt("DALL-E", 3)


def test_parse_splits_positive_and_negative():
    resp = "Positive: a cat on a windowsill, soft light\nNegative: blurry, low quality"
    pos, neg = parse_llm_response(resp, "cat")
    assert pos == "a cat on a windowsill, soft light"
    assert neg == "blurry, low quality"


def test_parse_tolerates_case_and_whitespace():
    resp = "  positive:   a dog running  \n   NEGATIVE:   extra limbs  "
    pos, neg = parse_llm_response(resp, "dog")
    assert pos == "a dog running"
    assert neg == "extra limbs"


def test_parse_empty_response_falls_back_to_raw_prompt():
    pos, neg = parse_llm_response("", "a red car")
    assert pos == "a red car"
    assert neg  # non-empty default negative


def test_parse_missing_negative_uses_default():
    resp = "Positive: a mountain at dawn"
    pos, neg = parse_llm_response(resp, "mountain")
    assert pos == "a mountain at dawn"
    assert neg  # default negative applied


def test_parse_missing_positive_falls_back_to_raw_prompt():
    resp = "Negative: blurry, distorted"
    pos, neg = parse_llm_response(resp, "a bird")
    assert pos == "a bird"
    assert neg == "blurry, distorted"


def test_run_returns_parsed_outputs():
    node = PSN_PromptEnhancer()
    resp = "Positive: a cat, detailed\nNegative: blurry"
    pos, neg = node.run("cat", "SDXL", 3, resp)
    assert pos == "a cat, detailed"
    assert neg == "blurry"


def test_run_rejects_bad_target_model():
    node = PSN_PromptEnhancer()
    with pytest.raises(ValueError):
        node.run("cat", "NotAModel", 3, "Positive: x\nNegative: y")


def test_run_with_empty_response_uses_raw_prompt():
    node = PSN_PromptEnhancer()
    pos, neg = node.run("a fox", "Flux", 2, "")
    assert pos == "a fox"
    assert neg
