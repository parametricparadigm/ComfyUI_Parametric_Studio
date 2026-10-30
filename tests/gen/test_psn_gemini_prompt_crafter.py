"""Tests for psn_nodes.gen.psn_gemini_prompt_crafter (pure logic, no network)."""

import json

from psn_nodes.gen.psn_gemini_prompt_crafter import (
    PSN_Gemini_Prompt_Crafter,
    psn_redact_api_key,
    psn_validate_style,
    psn_validate_target_word_count,
    psn_validate_user_prompt,
    psn_build_request_payload,
    psn_parse_response,
)


def _make_response(refined="A vivid photorealistic portrait of a cat.", tokens=42):
    return json.dumps({
        "candidates": [
            {"content": {"parts": [{"text": refined}]}}
        ],
        "usage_metadata": {"total_token_count": tokens},
    })


def test_psn_redact_api_key_valid_and_invalid():
    assert psn_redact_api_key("AIzaSyA1234567890abcdef") == "AIza****cdef"
    assert psn_redact_api_key("") == "<invalid>"
    assert psn_redact_api_key("not-a-key") == "<invalid>"
    assert psn_redact_api_key("sk-abc") == "sk****"
    assert psn_redact_api_key(None) == "<invalid>"


def test_psn_validate_style_ok_and_bad():
    ok, why = psn_validate_style("anime")
    assert ok is True and why == "ok"
    ok, why = psn_validate_style("watercolor")
    assert ok is False and "must be one of" in why
    ok, why = psn_validate_style(123)
    assert ok is False and "string" in why


def test_psn_validate_target_word_count_bounds():
    ok, why, val = psn_validate_target_word_count(80)
    assert ok is True and val == 80
    ok, why, _ = psn_validate_target_word_count(0)
    assert ok is False and ">= 1" in why
    ok, why, _ = psn_validate_target_word_count(501)
    assert ok is False and "<= 500" in why
    ok, why, _ = psn_validate_target_word_count(True)
    assert ok is False and "integer" in why


def test_psn_validate_user_prompt_edge_cases():
    ok, why = psn_validate_user_prompt("a cat")
    assert ok is True
    ok, why = psn_validate_user_prompt("   ")
    assert ok is False and "empty" in why
    ok, why = psn_validate_user_prompt("x" * 8001)
    assert ok is False and "too long" in why
    ok, why = psn_validate_user_prompt(42)
    assert ok is False and "string" in why


def test_psn_build_request_payload_shape():
    payload = psn_build_request_payload("a cat", "photorealistic", 80)
    assert payload["model"] == "gemini-1.5-flash"
    assert "photorealistic" in payload["system_instruction"]
    assert "80" in payload["system_instruction"]
    assert payload["contents"][0]["parts"][0]["text"] == "a cat"
    assert payload["generation_config"]["max_output_tokens"] == 320
    # api_key must never leak into the payload body
    assert "api_key" not in payload


def test_psn_parse_response_success():
    refined, tokens, err = psn_parse_response(_make_response("hello world", 17))
    assert err == ""
    assert refined == "hello world"
    assert tokens == 17


def test_psn_parse_response_bad_inputs():
    refined, tokens, err = psn_parse_response("")
    assert err != "" and refined == "" and tokens == 0
    refined, tokens, err = psn_parse_response("not json")
    assert "valid JSON" in err
    refined, tokens, err = psn_parse_response(json.dumps({"candidates": []}))
    assert "candidates" in err
    refined, tokens, err = psn_parse_response(json.dumps({"candidates": [{"content": {"parts": []}}]}))
    assert "no text" in err


def test_psn_node_run_happy_path():
    node = PSN_Gemini_Prompt_Crafter()
    resp = _make_response("A cinematic anime scene of a dragon.", 55)
    refined, tokens = node.run(
        api_key="AIzaSyValidKey1234567890",
        user_prompt="a dragon",
        style="anime",
        target_word_count=60,
        response_text=resp,
    )
    assert refined == "A cinematic anime scene of a dragon."
    assert tokens == 55


def test_psn_node_run_invalid_api_key():
    node = PSN_Gemini_Prompt_Crafter()
    refined, tokens = node.run(
        api_key="bad-key",
        user_prompt="a cat",
        style="anime",
        target_word_count=60,
        response_text=_make_response(),
    )
    assert refined.startswith("<error:")
    assert "api_key" in refined
    assert tokens == 0


def test_psn_node_run_bad_style_and_bad_response():
    node = PSN_Gemini_Prompt_Crafter()
    refined, tokens = node.run(
        api_key="AIzaSyValidKey1234567890",
        user_prompt="a cat",
        style="oil-painting",
        target_word_count=60,
        response_text=_make_response(),
    )
    assert refined.startswith("<error:")
    assert "style" in refined

    refined, tokens = node.run(
        api_key="AIzaSyValidKey1234567890",
        user_prompt="a cat",
        style="anime",
        target_word_count=60,
        response_text="garbage",
    )
    assert refined.startswith("<error:")
    assert "JSON" in refined
    assert tokens == 0
