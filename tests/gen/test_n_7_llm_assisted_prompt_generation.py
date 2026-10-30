"""
Tests for PSN_LLM_PromptExpander node.
"""

import json
import pytest
from psn_nodes.gen.n_7_llm_assisted_prompt_generation import (
    PSN_LLM_PromptExpander,
    _validate_model_path,
    _format_llm_payload,
    SYSTEM_PROMPT_TEMPLATE,
)


class TestValidateModelPath:
    def test_valid_model_path(self):
        is_valid, reason = _validate_model_path("models/llama/llama-3-8b-instruct.gguf")
        assert is_valid is True
        assert reason == "Valid"

    def test_valid_model_path_phi(self):
        is_valid, reason = _validate_model_path("models/phi/phi-2.gguf")
        assert is_valid is True
        assert reason == "Valid"

    def test_path_traversal_rejected(self):
        is_valid, reason = _validate_model_path("models/llama/../../etc/passwd")
        assert is_valid is False
        assert "Path traversal" in reason

    def test_absolute_path_rejected(self):
        is_valid, reason = _validate_model_path("/usr/local/models/llama.gguf")
        assert is_valid is False
        assert "Absolute paths" in reason

    def test_disallowed_prefix_rejected(self):
        is_valid, reason = _validate_model_path("models/gpt4/model.gguf")
        assert is_valid is False
        assert "does not match any allowed prefix" in reason

    def test_empty_path_rejected(self):
        is_valid, reason = _validate_model_path("")
        assert is_valid is False
        assert "empty" in reason.lower()

    def test_whitespace_only_path_rejected(self):
        is_valid, reason = _validate_model_path("   ")
        assert is_valid is False
        assert "empty" in reason.lower()


class TestFormatLlmPayload:
    def test_payload_structure(self):
        payload_str = _format_llm_payload("a cat", 0.7)
        payload = json.loads(payload_str)
        assert "system_prompt" in payload
        assert "user_prompt" in payload
        assert "temperature" in payload
        assert "max_tokens" in payload
        assert "stop" in payload

    def test_payload_values(self):
        payload_str = _format_llm_payload("a beautiful sunset", 0.5)
        payload = json.loads(payload_str)
        assert payload["user_prompt"] == "a beautiful sunset"
        assert payload["temperature"] == 0.5
        assert payload["system_prompt"] == SYSTEM_PROMPT_TEMPLATE
        assert payload["max_tokens"] == 512

    def test_payload_unicode(self):
        payload_str = _format_llm_payload("a cat with 🐱", 0.7)
        payload = json.loads(payload_str)
        assert payload["user_prompt"] == "a cat with 🐱"


class TestPSNLlmPromptExpander:
    def setup_method(self):
        self.node = PSN_LLM_PromptExpander()

    def test_valid_input_returns_payload(self):
        payload, is_valid, reason = self.node.run(
            raw_prompt="a cat",
            llm_model_path="models/llama/llama-3-8b-instruct.gguf",
            temperature=0.7,
        )
        assert is_valid is True
        assert reason == "Valid"
        parsed = json.loads(payload)
        assert parsed["user_prompt"] == "a cat"
        assert parsed["temperature"] == 0.7

    def test_invalid_model_path(self):
        payload, is_valid, reason = self.node.run(
            raw_prompt="a cat",
            llm_model_path="models/gpt4/model.gguf",
            temperature=0.7,
        )
        assert is_valid is False
        assert payload == ""
        assert "does not match" in reason

    def test_path_traversal_rejected(self):
        payload, is_valid, reason = self.node.run(
            raw_prompt="a cat",
            llm_model_path="models/llama/../../etc/passwd",
            temperature=0.7,
        )
        assert is_valid is False
        assert "Path traversal" in reason

    def test_temperature_out_of_range(self):
        payload, is_valid, reason = self.node.run(
            raw_prompt="a cat",
            llm_model_path="models/llama/llama-3-8b-instruct.gguf",
            temperature=3.0,
        )
        assert is_valid is False
        assert "Temperature" in reason

    def test_temperature_negative(self):
        payload, is_valid, reason = self.node.run(
            raw_prompt="a cat",
            llm_model_path="models/llama/llama-3-8b-instruct.gguf",
            temperature=-0.1,
        )
        assert is_valid is False
        assert "Temperature" in reason

    def test_empty_raw_prompt(self):
        payload, is_valid, reason = self.node.run(
            raw_prompt="",
            llm_model_path="models/llama/llama-3-8b-instruct.gguf",
            temperature=0.7,
        )
        # Empty prompt is still valid (LLM can handle it)
        assert is_valid is True
        parsed = json.loads(payload)
        assert parsed["user_prompt"] == ""

    def test_return_types_match(self):
        # Verify RETURN_TYPES and RETURN_NAMES are consistent
        assert len(PSN_LLM_PromptExpander.RETURN_TYPES) == 3
        assert len(PSN_LLM_PromptExpander.RETURN_NAMES) == 3
        assert PSN_LLM_PromptExpander.RETURN_TYPES[0] == "STRING"
        assert PSN_LLM_PromptExpander.RETURN_TYPES[1] == "BOOLEAN"
        assert PSN_LLM_PromptExpander.RETURN_TYPES[2] == "STRING"
        assert PSN_LLM_PromptExpander.RETURN_NAMES[0] == "expanded_prompt_payload"
        assert PSN_LLM_PromptExpander.RETURN_NAMES[1] == "is_valid"
        assert PSN_LLM_PromptExpander.RETURN_NAMES[2] == "reason"

    def test_input_types_structure(self):
        input_types = PSN_LLM_PromptExpander.INPUT_TYPES()
        assert "required" in input_types
        assert "raw_prompt" in input_types["required"]
        assert "llm_model_path" in input_types["required"]
        assert "temperature" in input_types["required"]
        assert input_types["required"]["temperature"][0] == "FLOAT"
        assert input_types["required"]["raw_prompt"][0] == "STRING"
