"""
PSN_LLM_Prompt_Refiner

This module implements the pure-logic, secure-by-design portion of an LLM-assisted
prompt refinement node. It does NOT perform any network I/O, file access, or
subprocess execution. Instead, it provides:

1. Request payload formatting for local LLM servers (OpenAI-compatible, Ollama).
2. API key redaction to prevent secrets from leaking into logs or outputs.
3. Response parsing and validation.
4. Config validation for endpoint URLs and API formats.

The actual HTTP call is left to the host environment (e.g., ComfyUI with a
network-enabled plugin). This node returns the formatted request payload and
parsed response so that a separate transport layer can execute the call.

Inputs:
    raw_prompt (STRING): The user's original prompt.
    llm_endpoint (STRING): The URL of the LLM API endpoint.
    api_key (STRING): The API key (will be redacted in outputs).
    system_prompt (STRING): The system prompt instructing the LLM to refine.
    api_format (STRING): One of "openai" (any OpenAI-compatible local server), "ollama".

Outputs:
    refined_prompt (STRING): The refined prompt (empty string if no response provided).
    request_payload (STRING): JSON-formatted request payload for the LLM API.
    redacted_api_key (STRING): The API key with sensitive characters masked.
    error_message (STRING): Any validation or parsing error, empty if none.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# Allowed API formats
_API_FORMATS = ("openai", "ollama")   # "openai" = any OpenAI-compatible server (vLLM, llama.cpp, llama-swap); hosted Anthropic support lives in the Extended edition

# Allowed endpoint schemes
_ALLOWED_SCHEMES = ("https", "http")

# Maximum length for raw prompt to prevent abuse
_MAX_PROMPT_LENGTH = 10000

# Maximum length for system prompt
_MAX_SYSTEM_PROMPT_LENGTH = 5000


def _validate_endpoint(endpoint: str) -> Tuple[bool, str]:
    """Validate that the endpoint URL is well-formed and uses an allowed scheme."""
    if not endpoint or not isinstance(endpoint, str):
        return False, "Endpoint must be a non-empty string."
    endpoint = endpoint.strip()
    if not endpoint:
        return False, "Endpoint must be a non-empty string."
    # Simple URL validation without importing urllib to keep it pure stdlib
    # Check for scheme
    match = re.match(r"^(https?|http)://", endpoint, re.IGNORECASE)
    if not match:
        return False, "Endpoint must start with http:// or https://."
    scheme = match.group(1).lower()
    if scheme not in _ALLOWED_SCHEMES:
        return False, f"Endpoint scheme '{scheme}' not allowed. Use http or https."
    # Basic check that there's a host after the scheme
    rest = endpoint[len(match.group(0)):]
    host = re.split(r"[/:?#]", rest, 1)[0].lower()
    if host not in ("127.0.0.1", "localhost", "[::1]") and os.environ.get("PSN_EDITION") != "extended":
        return False, f"Host '{host}' is not on this machine: the Open edition only uses local models (PSN_EDITION=extended allows others)."
    if not rest:
        return False, "Endpoint must include a host."
    return True, ""


def _redact_api_key(api_key: str) -> str:
    """Redact an API key, showing only the first 4 and last 4 characters."""
    if not api_key or not isinstance(api_key, str):
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]


def _build_openai_payload(raw_prompt: str, system_prompt: str, model: str = "qwen38-27b-fp8") -> Dict[str, Any]:
    """Build an OpenAI-compatible chat completion request payload."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": raw_prompt})
    return {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }



def _build_ollama_payload(raw_prompt: str, system_prompt: str, model: str = "llama3") -> Dict[str, Any]:
    """Build an Ollama /api/chat request payload."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": raw_prompt})
    return {
        "model": model,
        "messages": messages,
        "stream": False,
    }


def _parse_openai_response(response_json: Dict[str, Any]) -> Tuple[str, str]:
    """Parse an OpenAI-compatible chat completion response. Returns (refined_prompt, error)."""
    try:
        choices = response_json.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            return "", "No choices in response."
        message = choices[0].get("message")
        if not message or not isinstance(message, dict):
            return "", "No message in choice."
        content = message.get("content")
        if not content or not isinstance(content, str):
            return "", "No content in message."
        return content.strip(), ""
    except (AttributeError, TypeError, IndexError) as e:
        return "", f"Failed to parse OpenAI response: {e}"



def _parse_ollama_response(response_json: Dict[str, Any]) -> Tuple[str, str]:
    """Parse an Ollama /api/chat response. Returns (refined_prompt, error)."""
    try:
        message = response_json.get("message")
        if not message or not isinstance(message, dict):
            return "", "No message in response."
        content = message.get("content")
        if not content or not isinstance(content, str):
            return "", "No content in message."
        return content.strip(), ""
    except (AttributeError, TypeError, IndexError) as e:
        return "", f"Failed to parse Ollama response: {e}"


def _build_payload(api_format: str, raw_prompt: str, system_prompt: str) -> Tuple[Dict[str, Any], str]:
    """Build the appropriate request payload based on API format. Returns (payload, error)."""
    if api_format == "openai":
        return _build_openai_payload(raw_prompt, system_prompt), ""
    elif api_format == "ollama":
        return _build_ollama_payload(raw_prompt, system_prompt), ""
    else:
        return {}, f"Unknown API format: '{api_format}'. Use one of: {', '.join(_API_FORMATS)}."


def _parse_response(api_format: str, response_json: Dict[str, Any]) -> Tuple[str, str]:
    """Parse the LLM response based on API format. Returns (refined_prompt, error)."""
    if api_format == "openai":
        return _parse_openai_response(response_json)
    elif api_format == "ollama":
        return _parse_ollama_response(response_json)
    else:
        return "", f"Unknown API format: '{api_format}'."


class PSN_LLM_Prompt_Refiner:
    """
    Formats an LLM request payload for prompt refinement and parses the response.
    Does not perform network I/O. Returns the request payload as JSON and the
    parsed refined prompt if a response is provided.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_prompt": ("STRING", {"default": "", "multiline": True}),
                "llm_endpoint": ("STRING", {"default": "http://127.0.0.1:8002/v1/chat/completions"}),
                "api_key": ("STRING", {"default": "", "password": True}),
                "system_prompt": ("STRING", {"default": "You are a prompt engineer. Refine and expand the user's prompt to be more detailed and descriptive for an image generation model.", "multiline": True}),
                "api_format": (list(_API_FORMATS), {"default": "openai"}),
            },
            "optional": {
                "llm_response": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("refined_prompt", "request_payload", "redacted_api_key", "error_message")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/LLM"

    def run(
        self,
        raw_prompt: str,
        llm_endpoint: str,
        api_key: str,
        system_prompt: str,
        api_format: str,
        llm_response: str = "",
    ) -> Tuple[str, str, str, str]:
        """
        Validate inputs, build the request payload, and parse the response if provided.
        Returns (refined_prompt, request_payload_json, redacted_api_key, error_message).
        """
        # Validate raw_prompt
        if not isinstance(raw_prompt, str):
            return "", "", "", "raw_prompt must be a string."
        if len(raw_prompt) > _MAX_PROMPT_LENGTH:
            return "", "", "", f"raw_prompt exceeds maximum length of {_MAX_PROMPT_LENGTH} characters."

        # Validate system_prompt
        if not isinstance(system_prompt, str):
            return "", "", "", "system_prompt must be a string."
        if len(system_prompt) > _MAX_SYSTEM_PROMPT_LENGTH:
            return "", "", "", f"system_prompt exceeds maximum length of {_MAX_SYSTEM_PROMPT_LENGTH} characters."

        # Validate endpoint
        endpoint_valid, endpoint_error = _validate_endpoint(llm_endpoint)
        if not endpoint_valid:
            return "", "", "", endpoint_error

        # Validate api_format
        if api_format not in _API_FORMATS:
            return "", "", "", f"api_format must be one of: {', '.join(_API_FORMATS)}."

        # Redact API key
        redacted_key = _redact_api_key(api_key)

        # Build payload
        payload, payload_error = _build_payload(api_format, raw_prompt, system_prompt)
        if payload_error:
            return "", "", redacted_key, payload_error

        # Serialize payload to JSON
        try:
            payload_json = json.dumps(payload, indent=2)
        except (TypeError, ValueError) as e:
            return "", "", redacted_key, f"Failed to serialize payload: {e}"

        # Parse response if provided
        refined_prompt = ""
        parse_error = ""
        if llm_response and llm_response.strip():
            try:
                response_json = json.loads(llm_response)
            except json.JSONDecodeError as e:
                return "", payload_json, redacted_key, f"Failed to parse llm_response as JSON: {e}"
            refined_prompt, parse_error = _parse_response(api_format, response_json)
            if parse_error:
                return "", payload_json, redacted_key, parse_error

        return refined_prompt, payload_json, redacted_key, ""


NODE_CLASS_MAPPINGS = {
    "PSN_LLM_Prompt_Refiner": PSN_LLM_Prompt_Refiner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_Prompt_Refiner": "LLM Prompt Refiner",
}
