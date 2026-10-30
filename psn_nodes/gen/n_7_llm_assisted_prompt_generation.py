"""
PSN_LLM_PromptExpander

This module provides a pure-logic, secure-by-design implementation of the
"LLM-Assisted Prompt Generation" node. Because the actual LLM inference
requires GPU/torch/llama.cpp (which are prohibited in this environment),
this node implements ONLY the message/payload formatting, config validation,
and allow-list checks.

It formats the system prompt and user prompt into a structured payload that
would be sent to a local LLM. It also validates the model path against an
allow-list to prevent path traversal or unauthorized model loading.

The node returns the formatted payload (as a JSON string) and a boolean
indicating whether the configuration is valid. In a real ComfyUI environment,
a separate backend service would consume this payload to perform the actual
LLM inference.
"""

import json
import re
from psn import expr, orchestration

CAT = "ParametricStudio/LLM"

# Allow-list of valid model path prefixes (relative to a models directory)
ALLOWED_MODEL_PREFIXES = (
    "models/llama/",
    "models/llama3/",
    "models/phi/",
)

# System prompt template for the LLM
SYSTEM_PROMPT_TEMPLATE = (
    "You are a prompt engineering assistant. Your task is to expand and beautify "
    "the user's prompt for use in an image generation model. "
    "Make it more detailed, descriptive, and aesthetically pleasing. "
    "Do not add any text outside of the expanded prompt. "
    "Return only the expanded prompt."
)


def _validate_model_path(model_path: str) -> tuple[bool, str]:
    """
    Validate that the model path is safe and within the allow-list.
    Returns (is_valid, reason).
    """
    if not model_path or not isinstance(model_path, str):
        return False, "Model path must be a non-empty string"

    # Strip whitespace
    model_path = model_path.strip()

    if not model_path:
        return False, "Model path is empty"

    # Check for path traversal
    if ".." in model_path:
        return False, "Path traversal detected"

    # Check for absolute paths (not allowed)
    if model_path.startswith("/") or model_path.startswith("\\"):
        return False, "Absolute paths are not allowed"

    # Check against allow-list
    for prefix in ALLOWED_MODEL_PREFIXES:
        if model_path.startswith(prefix):
            return True, "Valid"

    return False, f"Model path does not match any allowed prefix: {ALLOWED_MODEL_PREFIXES}"


def _format_llm_payload(raw_prompt: str, temperature: float) -> str:
    """
    Format the LLM payload as a JSON string.
    """
    payload = {
        "system_prompt": SYSTEM_PROMPT_TEMPLATE,
        "user_prompt": raw_prompt,
        "temperature": temperature,
        "max_tokens": 512,
        "stop": ["\n\n"],
    }
    return json.dumps(payload, ensure_ascii=False)


class PSN_LLM_PromptExpander:
    """
    Formats a prompt expansion request for a local LLM.
    Validates the model path and temperature, then returns a JSON payload
    that would be sent to the LLM backend.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_prompt": ("STRING", {"default": "", "multiline": True}),
                "llm_model_path": ("STRING", {"default": "models/llama/llama-3-8b-instruct.gguf"}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("expanded_prompt_payload", "is_valid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_prompt: str, llm_model_path: str, temperature: float):
        """
        Validate inputs and format the LLM payload.
        Returns:
            - expanded_prompt_payload: JSON string with the formatted request
            - is_valid: Boolean indicating if the configuration is valid
            - reason: String explaining validation result
        """
        # Validate model path
        is_valid, reason = _validate_model_path(llm_model_path)
        if not is_valid:
            return ("", False, reason)

        # Validate temperature
        if not isinstance(temperature, (int, float)):
            return ("", False, "Temperature must be a number")
        if temperature < 0.0 or temperature > 2.0:
            return ("", False, "Temperature must be between 0.0 and 2.0")

        # Validate raw prompt
        if not isinstance(raw_prompt, str):
            return ("", False, "Raw prompt must be a string")

        # Format the payload
        payload = _format_llm_payload(raw_prompt, float(temperature))

        return (payload, True, "Valid")


NODE_CLASS_MAPPINGS = {
    "PSN_LLM_PromptExpander": PSN_LLM_PromptExpander,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_PromptExpander": "LLM Prompt Expander",
}
