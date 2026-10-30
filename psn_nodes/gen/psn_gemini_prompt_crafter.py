"""PSN_Gemini_Prompt_Crafter: pure-logic prompt refinement scaffolding.

This module implements the secure, offline portion of a Gemini prompt
refiner. It does NOT call the Gemini API, open sockets, or perform any
network I/O. Instead it:

  * validates and redacts the API key (allow-listed prefix check + masking),
  * builds a deterministic, well-formed request payload (system instruction
    + user prompt + style + target word count),
  * parses a *provided* JSON response text (as if it had come back from the
    API) into a refined prompt string and an integer token usage count,
  * enforces a content-policy allow-list on the style and a word-count cap.

The node therefore takes plain values (strings, ints) and returns plain
values (strings, ints). The actual HTTP call to Gemini is intentionally
left to the host environment; this node is the safe-by-design logic layer.
"""

import json
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STYLES = ("photorealistic", "anime", "3d")

# Allowed API key prefixes (allow-list). Real keys are long; we only check
# that the key *starts* with one of these prefixes so we can redact safely.
_ALLOWED_KEY_PREFIXES = ("AIza", "sk-", "gsk_")

# Hard cap on target word count to bound cost / latency.
_MAX_TARGET_WORDS = 500
_MIN_TARGET_WORDS = 1

# Maximum length of the user prompt we will accept (chars).
_MAX_PROMPT_CHARS = 8000

# Maximum length of the refined prompt we will accept from the response.
_MAX_REFINED_CHARS = 16000

# System instruction template. {style} and {target_word_count} are filled in.
_SYSTEM_INSTRUCTION = (
    "You are a prompt engineer. Rewrite the user's prompt so that it is "
    "clear, vivid, and well suited to a {style} image generation model. "
    "Keep the core subject and intent. Aim for roughly {target_word_count} "
    "words. Do not add disallowed or policy-violating content. "
    "Respond with ONLY the refined prompt text, no preamble."
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def psn_redact_api_key(api_key):
    """Return a redacted form of the API key.

    If the key is empty or does not start with an allowed prefix, return
    the literal string "<invalid>". Otherwise return the first 4 chars,
    then "****", then the last 4 chars (if the key is long enough).
    """
    if not isinstance(api_key, str) or not api_key:
        return "<invalid>"
    key = api_key.strip()
    if not key:
        return "<invalid>"
    if not any(key.startswith(p) for p in _ALLOWED_KEY_PREFIXES):
        return "<invalid>"
    if len(key) <= 8:
        return key[:2] + "****"
    return key[:4] + "****" + key[-4:]


def psn_validate_style(style):
    """Return (ok, reason). style must be one of the allowed styles."""
    if not isinstance(style, str):
        return False, "style must be a string"
    if style not in _STYLES:
        return False, "style must be one of: " + ", ".join(_STYLES)
    return True, "ok"


def psn_validate_target_word_count(target_word_count):
    """Return (ok, reason, clamped_value)."""
    if not isinstance(target_word_count, int) or isinstance(target_word_count, bool):
        return False, "target_word_count must be an integer", 0
    if target_word_count < _MIN_TARGET_WORDS:
        return False, "target_word_count must be >= 1", 0
    if target_word_count > _MAX_TARGET_WORDS:
        return False, "target_word_count must be <= %d" % _MAX_TARGET_WORDS, 0
    return True, "ok", target_word_count


def psn_validate_user_prompt(user_prompt):
    """Return (ok, reason)."""
    if not isinstance(user_prompt, str):
        return False, "user_prompt must be a string"
    if not user_prompt.strip():
        return False, "user_prompt must not be empty"
    if len(user_prompt) > _MAX_PROMPT_CHARS:
        return False, "user_prompt too long (max %d chars)" % _MAX_PROMPT_CHARS
    return True, "ok"


def psn_build_request_payload(user_prompt, style, target_word_count):
    """Build the JSON-serialisable request payload that *would* be sent.

    Returns a dict. The api_key is intentionally NOT included in the
    payload body (it would go in an Authorization header, which we do not
    construct here).
    """
    system_instruction = _SYSTEM_INSTRUCTION.format(
        style=style, target_word_count=target_word_count
    )
    return {
        "model": "gemini-1.5-flash",
        "system_instruction": system_instruction,
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generation_config": {
            "max_output_tokens": max(64, target_word_count * 4),
            "temperature": 0.7,
        },
    }


def psn_parse_response(response_text):
    """Parse a Gemini-style JSON response into (refined_prompt, token_usage).

    Accepts the JSON text of a response that contains a top-level
    "candidates" list with at least one candidate whose "content.parts"
    list contains a "text" field, and a top-level "usage_metadata" object
    with "total_token_count".

    Returns (refined_prompt, token_usage, error). On success error is "".
    """
    if not isinstance(response_text, str) or not response_text.strip():
        return "", 0, "response_text must be a non-empty string"
    try:
        data = json.loads(response_text)
    except (ValueError, TypeError):
        return "", 0, "response_text is not valid JSON"
    if not isinstance(data, dict):
        return "", 0, "response JSON must be an object"

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return "", 0, "response missing non-empty 'candidates' list"

    refined = ""
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        content = cand.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                refined = part["text"].strip()
                break
        if refined:
            break

    if not refined:
        return "", 0, "no text found in response candidates"

    if len(refined) > _MAX_REFINED_CHARS:
        refined = refined[:_MAX_REFINED_CHARS]

    usage = data.get("usage_metadata")
    token_usage = 0
    if isinstance(usage, dict):
        ttc = usage.get("total_token_count")
        if isinstance(ttc, int) and not isinstance(ttc, bool) and ttc >= 0:
            token_usage = ttc

    return refined, token_usage, ""


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

class PSN_Gemini_Prompt_Crafter:
    """Refine/expand a user prompt for image generation (offline logic layer).

    This node validates inputs, builds the request payload, and parses a
    *provided* response JSON text. It performs no network I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "user_prompt": ("STRING", {"default": "", "multiline": True}),
                "style": (list(_STYLES),),
                "target_word_count": ("INT", {"default": 80, "min": _MIN_TARGET_WORDS, "max": _MAX_TARGET_WORDS, "step": 1}),
            },
            "optional": {
                "response_text": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("refined_prompt", "token_usage")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Gemini"

    def run(self, api_key, user_prompt, style, target_word_count, response_text=""):
        # Validate API key (redact; we never use it for I/O here).
        redacted = psn_redact_api_key(api_key)
        if redacted == "<invalid>":
            return ("<error: invalid or missing api_key>", 0)

        ok, why = psn_validate_user_prompt(user_prompt)
        if not ok:
            return ("<error: " + why + ">", 0)

        ok, why = psn_validate_style(style)
        if not ok:
            return ("<error: " + why + ">", 0)

        ok, why, _ = psn_validate_target_word_count(target_word_count)
        if not ok:
            return ("<error: " + why + ">", 0)

        # Build the payload (not sent anywhere).
        _payload = psn_build_request_payload(user_prompt, style, target_word_count)

        # Parse the provided response text.
        refined, token_usage, err = psn_parse_response(response_text)
        if err:
            return ("<error: " + err + ">", 0)

        return (refined, token_usage)


NODE_CLASS_MAPPINGS = {
    "PSN_Gemini_Prompt_Crafter": PSN_Gemini_Prompt_Crafter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Gemini_Prompt_Crafter": "Gemini Prompt Crafter (PSN)",
}
