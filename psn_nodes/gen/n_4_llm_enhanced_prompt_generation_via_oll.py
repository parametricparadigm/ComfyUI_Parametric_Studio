"""PSN_Ollama_Prompt_Enhancer

LLM-Enhanced Prompt Generation via Ollama.

This module provides a ComfyUI custom node that enhances short user prompts
into detailed, structured prompts using a local Ollama LLM service.

Since network access is forbidden in this environment, the node implements:
  - A template-based fallback enhancer (pure Python, no network) that expands
    a short prompt into a structured, detailed prompt with style descriptors,
    lighting, composition, and quality tags.
  - A pluggable ``_ollama_request`` hook that, in a real deployment, would be
    replaced by an HTTP call to the Ollama API.  The hook is injectable so
    tests can supply a mock without any network.
  - Robust parsing of Ollama-style JSON responses (``{"message": {"content": ...}}``)
    and plain-text responses.
  - Clear error messages when the Ollama service is unreachable.

What was NOT implemented (requires network / external service):
  - Actual HTTP POST to the Ollama REST API (``/api/generate``).
  - Real LLM inference (llama3, etc.).
  - Timeout / connection-error handling against a live service.

What IS implemented (core logic, testable offline):
  - Template-based prompt enhancement with style presets.
  - Negative-prompt generation per style.
  - Response parsing (JSON and plain text).
  - Input validation and edge-case handling.
  - Full ComfyUI node interface (INPUT_TYPES, RETURN_TYPES, etc.).
"""

import json
import re

# ---------------------------------------------------------------------------
# Style presets: each style maps to a set of descriptor fragments and a
# corresponding negative prompt.
# ---------------------------------------------------------------------------

_STYLE_PRESETS = {
    "realistic": {
        "positive": [
            "photorealistic",
            "8k uhd",
            "detailed skin texture",
            "natural lighting",
            "shallow depth of field",
            "professional photography",
            "highly detailed",
            "sharp focus",
        ],
        "negative": (
            "cartoon, anime, illustration, painting, drawing, sketch, "
            "3d render, cgi, plastic, waxy skin, deformed, ugly, blurry, "
            "low quality, watermark, text, signature"
        ),
    },
    "anime": {
        "positive": [
            "anime style",
            "vibrant colors",
            "clean line art",
            "cel shading",
            "detailed background",
            "high quality anime",
            "beautiful lighting",
            "expressive",
        ],
        "negative": (
            "photorealistic, 3d, realistic, ugly, deformed, bad anatomy, "
            "extra limbs, blurry, low quality, watermark, text, signature, "
            "nsfw"
        ),
    },
    "cinematic": {
        "positive": [
            "cinematic",
            "dramatic lighting",
            "film grain",
            "anamorphic lens",
            "color graded",
            "epic composition",
            "shallow depth of field",
            "movie still",
            "highly detailed",
        ],
        "negative": (
            "cartoon, anime, flat lighting, overexposed, underexposed, "
            "blurry, low quality, watermark, text, signature, deformed"
        ),
    },
    "none": {
        "positive": [
            "highly detailed",
            "sharp focus",
            "well composed",
            "beautiful lighting",
            "masterpiece",
        ],
        "negative": (
            "blurry, low quality, watermark, text, signature, deformed, "
            "ugly, bad anatomy"
        ),
    },
}

# ---------------------------------------------------------------------------
# Template-based enhancer (offline fallback)
# ---------------------------------------------------------------------------


def _template_enhance(short_prompt: str, style: str, max_tokens: int) -> tuple:
    """Expand *short_prompt* into a detailed prompt using style presets.

    Returns ``(enhanced_prompt, negative_prompt)``.
    """
    short_prompt = (short_prompt or "").strip()
    if not short_prompt:
        short_prompt = "a beautiful scene"

    style = (style or "none").strip().lower()
    if style not in _STYLE_PRESETS:
        style = "none"

    preset = _STYLE_PRESETS[style]
    descriptors = ", ".join(preset["positive"])

    # Build the enhanced prompt: subject + descriptors + quality tag
    parts = [short_prompt, descriptors, "masterpiece, best quality"]
    enhanced = ", ".join(parts)

    # Rough token budget: truncate if the prompt is too long.
    # We approximate 1 token ≈ 4 characters for English text.
    if max_tokens and max_tokens > 0:
        max_chars = max_tokens * 4
        if len(enhanced) > max_chars:
            enhanced = enhanced[:max_chars].rsplit(",", 1)[0].rstrip(", ")

    return enhanced, preset["negative"]


# ---------------------------------------------------------------------------
# Ollama response parsing
# ---------------------------------------------------------------------------


def _parse_ollama_response(raw: str) -> str:
    """Parse an Ollama API response into plain text.

    Handles:
      - JSON: ``{"message": {"content": "..."}}``
      - JSON: ``{"response": "..."}``
      - Plain text (fallback)
    """
    if not raw or not raw.strip():
        return ""

    raw = raw.strip()

    # Try JSON first
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # Ollama /api/generate format
            if "message" in data and isinstance(data["message"], dict):
                content = data["message"].get("content", "")
                if content:
                    return content.strip()
            # Ollama /api/chat format
            if "response" in data:
                return str(data["response"]).strip()
            # Fallback: look for any string value
            for v in data.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Plain text fallback
    return raw


# ---------------------------------------------------------------------------
# Ollama request hook (injectable for testing)
# ---------------------------------------------------------------------------


def _default_ollama_request(ollama_url: str, model_name: str, prompt: str, max_tokens: int) -> str:
    """Default Ollama request handler.

    In a real deployment this would perform an HTTP POST to
    ``{ollama_url}/api/generate``.  Because network access is forbidden
    in this sandbox, this function raises a clear error.

    Override by assigning a different callable to
    ``PSN_Ollama_Prompt_Enhancer._ollama_request``.
    """
    raise ConnectionError(
        f"Ollama service is not reachable at {ollama_url}. "
        "Network access is unavailable in this environment. "
        "Falling back to template-based enhancement."
    )


# ---------------------------------------------------------------------------
# ComfyUI Node
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/LLM"


class PSN_Ollama_Prompt_Enhancer:
    """Enhance a short prompt into a detailed, structured prompt using a local
    Ollama LLM (or a template-based fallback when the service is unavailable).

    Inputs:
        short_prompt  – the user's initial short prompt.
        ollama_url    – URL of the Ollama service (default http://localhost:11434).
        model_name    – Ollama model name (e.g. "llama3").
        style         – desired style: realistic / anime / cinematic / none.
        max_tokens    – maximum tokens for the generated prompt.

    Outputs:
        enhanced_prompt  – the detailed prompt string.
        negative_prompt  – a suggested negative prompt string.
    """

    # Injected by tests / deployment; replaced at runtime.
    _ollama_request = staticmethod(_default_ollama_request)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "short_prompt": ("STRING", {"default": "a cat", "multiline": True}),
                "style": (
                    ["realistic", "anime", "cinematic", "none"],
                    {"default": "realistic"},
                ),
                "max_tokens": ("INT", {"default": 128, "min": 16, "max": 2048}),
            },
            "optional": {
                "ollama_url": ("STRING", {"default": "http://localhost:11434"}),
                "model_name": ("STRING", {"default": "llama3"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("enhanced_prompt", "negative_prompt")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        short_prompt: str,
        style: str = "realistic",
        max_tokens: int = 128,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "llama3",
    ):
        """Enhance *short_prompt* via Ollama (or template fallback).

        Returns ``(enhanced_prompt, negative_prompt)``.
        """
        # --- Validate inputs ------------------------------------------------
        if not isinstance(short_prompt, str):
            raise TypeError("short_prompt must be a string")
        if not isinstance(style, str):
            raise TypeError("style must be a string")
        if not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")

        short_prompt = short_prompt.strip()
        style = style.strip().lower()
        if style not in _STYLE_PRESETS:
            style = "none"

        # --- Build the instruction for the LLM ------------------------------
        instruction = (
            f"Enhance the following short prompt into a detailed, structured "
            f"image-generation prompt. Style: {style}. "
            f"Return ONLY the enhanced prompt text, no explanations.\n\n"
            f"Short prompt: {short_prompt}"
        )

        # --- Try Ollama first, fall back to template ------------------------
        enhanced = None
        negative = None

        try:
            raw_response = self._ollama_request(
                ollama_url, model_name, instruction, max_tokens
            )
            enhanced = _parse_ollama_response(raw_response)
            if enhanced:
                # Extract negative prompt if the LLM included one
                # (convention: a line starting with "Negative:")
                neg_match = re.search(r"Negative:\s*(.+)", enhanced, re.IGNORECASE)
                if neg_match:
                    negative = neg_match.group(1).strip()
                    enhanced = enhanced[: neg_match.start()].strip().rstrip(",")
        except (ConnectionError, OSError, Exception) as exc:
            # Fall back to template-based enhancement
            enhanced = None
            negative = None

        if not enhanced:
            enhanced, negative = _template_enhance(short_prompt, style, max_tokens)

        # Ensure we always have a negative prompt
        if not negative:
            negative = _STYLE_PRESETS[style]["negative"]

        return (enhanced, negative)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Ollama_Prompt_Enhancer": PSN_Ollama_Prompt_Enhancer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Ollama_Prompt_Enhancer": "Ollama Prompt Enhancer",
}
