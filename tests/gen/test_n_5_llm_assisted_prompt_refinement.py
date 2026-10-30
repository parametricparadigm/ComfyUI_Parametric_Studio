"""
Tests for PSN_LLM_Prompt_Refiner node.
"""

import json
import pytest

from psn_nodes.gen.n_5_llm_assisted_prompt_refinement import (
    PSN_LLM_Prompt_Refiner,
    _validate_endpoint,
    _redact_api_key,
    _build_openai_payload,
    _build_ollama_payload,
    _parse_openai_response,
    _parse_ollama_response,
)


class TestValidateEndpoint:
    def test_valid_https_endpoint(self):
        valid, error = _validate_endpoint("http://127.0.0.1:8002/v1/chat/completions")
        assert valid is True
        assert error == ""

    def test_valid_http_endpoint(self):
        valid, error = _validate_endpoint("http://localhost:11434/api/chat")
        assert valid is True
        assert error == ""

    def test_invalid_scheme(self):
        valid, error = _validate_endpoint("ftp://example.com")
        assert valid is False
        assert "http" in error.lower()

    def test_empty_endpoint(self):
        valid, error = _validate_endpoint("")
        assert valid is False

    def test_no_scheme(self):
        valid, error = _validate_endpoint("127.0.0.1:8002/v1")
        assert valid is False


class TestRedactApiKey:
    def test_long_key(self):
        key = "sk-1234567890abcdef"
        redacted = _redact_api_key(key)
        assert redacted.startswith("sk-1")
        assert redacted.endswith("cdef")
        assert "*" in redacted
        assert "1234567890" not in redacted

    def test_short_key(self):
        key = "abc"
        redacted = _redact_api_key(key)
        assert redacted == "***"

    def test_empty_key(self):
        assert _redact_api_key("") == ""

    def test_none_key(self):
        assert _redact_api_key(None) == ""


class TestBuildPayloads:
    def test_openai_payload(self):
        payload = _build_openai_payload("a cat", "Refine this prompt.")
        assert payload["model"] == "qwen38-27b-fp8"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "Refine this prompt."
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "a cat"

    def test_ollama_payload(self):
        payload = _build_ollama_payload("a bird", "Refine this prompt.")
        assert payload["model"] == "llama3"
        assert payload["stream"] is False
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"


class TestParseResponses:
    def test_openai_response(self):
        response = {
            "choices": [
                {"message": {"role": "assistant", "content": "A detailed cat prompt"}}
            ]
        }
        refined, error = _parse_openai_response(response)
        assert refined == "A detailed cat prompt"
        assert error == ""

    def test_ollama_response(self):
        response = {
            "message": {"role": "assistant", "content": "A detailed bird prompt"}
        }
        refined, error = _parse_ollama_response(response)
        assert refined == "A detailed bird prompt"
        assert error == ""

    def test_openai_response_no_choices(self):
        refined, error = _parse_openai_response({"choices": []})
        assert refined == ""
        assert "No choices" in error


class TestNodeRun:
    def setup_method(self):
        self.node = PSN_LLM_Prompt_Refiner()

    def test_basic_openai_flow(self):
        response_json = json.dumps({
            "choices": [
                {"message": {"role": "assistant", "content": "A majestic cat sitting on a windowsill"}}
            ]
        })
        refined, payload_json, redacted_key, error = self.node.run(
            raw_prompt="a cat",
            llm_endpoint="http://127.0.0.1:8002/v1/chat/completions",
            api_key="sk-1234567890abcdef",
            system_prompt="Refine this prompt.",
            api_format="openai",
            llm_response=response_json,
        )
        assert refined == "A majestic cat sitting on a windowsill"
        assert error == ""
        assert redacted_key.startswith("sk-1")
        payload = json.loads(payload_json)
        assert payload["messages"][1]["content"] == "a cat"

    def test_invalid_endpoint(self):
        refined, payload_json, redacted_key, error = self.node.run(
            raw_prompt="a cat",
            llm_endpoint="ftp://bad.example.com",
            api_key="sk-1234567890abcdef",
            system_prompt="Refine this prompt.",
            api_format="openai",
        )
        assert refined == ""
        assert "http" in error.lower()

    def test_invalid_api_format(self):
        refined, payload_json, redacted_key, error = self.node.run(
            raw_prompt="a cat",
            llm_endpoint="http://127.0.0.1:8002/v1/chat/completions",
            api_key="sk-1234567890abcdef",
            system_prompt="Refine this prompt.",
            api_format="invalid_format",
        )
        assert refined == ""
        assert "api_format must be one of" in error

    def test_no_response_provided(self):
        refined, payload_json, redacted_key, error = self.node.run(
            raw_prompt="a cat",
            llm_endpoint="http://127.0.0.1:8002/v1/chat/completions",
            api_key="sk-1234567890abcdef",
            system_prompt="Refine this prompt.",
            api_format="openai",
        )
        assert refined == ""
        assert error == ""
        assert payload_json != ""

    def test_invalid_json_response(self):
        refined, payload_json, redacted_key, error = self.node.run(
            raw_prompt="a cat",
            llm_endpoint="http://127.0.0.1:8002/v1/chat/completions",
            api_key="sk-1234567890abcdef",
            system_prompt="Refine this prompt.",
            api_format="openai",
            llm_response="not valid json",
        )
        assert refined == ""
        assert "Failed to parse llm_response as JSON" in error

    def test_oversized_prompt(self):
        long_prompt = "a" * 10001
        refined, payload_json, redacted_key, error = self.node.run(
            raw_prompt=long_prompt,
            llm_endpoint="http://127.0.0.1:8002/v1/chat/completions",
            api_key="sk-1234567890abcdef",
            system_prompt="Refine this prompt.",
            api_format="openai",
        )
        assert refined == ""
        assert "exceeds maximum length" in error

    def test_ollama_flow(self):
        response_json = json.dumps({
            "message": {"role": "assistant", "content": "A detailed bird prompt"}
        })
        refined, payload_json, redacted_key, error = self.node.run(
            raw_prompt="a bird",
            llm_endpoint="http://localhost:11434/api/chat",
            api_key="",
            system_prompt="Refine this prompt.",
            api_format="ollama",
            llm_response=response_json,
        )
        assert refined == "A detailed bird prompt"
        assert error == ""
        payload = json.loads(payload_json)
        assert payload["stream"] is False


def test_open_edition_refuses_remote_hosts(monkeypatch):
    monkeypatch.delenv("PSN_EDITION", raising=False)
    ok, err = _validate_endpoint("https://api.example.com/v1/chat/completions")
    assert not ok and "not on this machine" in err
    monkeypatch.setenv("PSN_EDITION", "extended")
    assert _validate_endpoint("https://api.example.com/v1/chat/completions")[0]
