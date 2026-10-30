"""PSN_Prompt_Enhancer (pure-logic core).

This module implements the deterministic, secure-by-design parts of a prompt
enhancer node: system-prompt construction, verbosity clamping, and parsing of a
model response into a positive/negative prompt pair.

The actual LLM inference (the llama.cpp / llama-server HTTP call) is NOT
performed here. Per the project rules this module uses only the Python standard
library and performs no network, file, or subprocess I/O. The `run` function
therefore accepts an already-fetched `llm_response` string (plain text) and
returns the parsed outputs. A real ComfyUI node would obtain `llm_response`
from the `llama.cpp` connection and pass it in.
"""

import re

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Text"

_TARGET_MODELS = ("SDXL", "Flux", "SD1.5")
_VERBOSITY_MIN = 1
_VERBOSITY_MAX = 5

# Style guidance appended to the system prompt per target model.
_MODEL_GUIDANCE = {
    "SDXL": "photorealistic, high detail, 8k, sharp focus, professional lighting",
    "Flux": "cinematic, ultra detailed, coherent composition, natural color grading",
    "SD1.5": "high quality, detailed, well composed, clean lines",
}

# Fallbacks used when the model response is missing or malformed.
_FALLBACK_NEGATIVE = "blurry, low quality, distorted, watermark, text, extra limbs"


def build_system_prompt(target_model, verbosity):
    """Return the system prompt that instructs the LLM to act as a prompt
    engineer for ``target_model`` at the given ``verbosity``.

    ``verbosity`` is clamped to the 1..5 range. Raises ``ValueError`` if
    ``target_model`` is not one of the supported models.
    """
    if target_model not in _TARGET_MODELS:
        raise ValueError("Unsupported target_model: %r" % (target_model,))
    v = _clamp_verbosity(verbosity)
    guidance = _MODEL_GUIDANCE[target_model]
    return (
        "You are a prompt engineer for the {model} image model. "
        "Expand the user's short prompt into a detailed, well-structured prompt. "
        "Respond with exactly two lines: "
        "line 1 starts with 'Positive:' and contains the enhanced prompt; "
        "line 2 starts with 'Negative:' and contains a suggested negative prompt. "
        "Target verbosity level {v} (1=concise, 5=very detailed). "
        "Style emphasis: {guidance}."
    ).format(model=target_model, v=v, guidance=guidance)


def _clamp_verbosity(verbosity):
    """Clamp ``verbosity`` into the inclusive 1..5 range, returning an int."""
    try:
        v = int(verbosity)
    except (TypeError, ValueError):
        v = _VERBOSITY_MIN
    if v < _VERBOSITY_MIN:
        v = _VERBOSITY_MIN
    elif v > _VERBOSITY_MAX:
        v = _VERBOSITY_MAX
    return v


def parse_llm_response(llm_response, raw_prompt):
    """Parse an LLM response into ``(positive, negative)``.

    The expected format is two lines, the first beginning with ``Positive:``
    and the second with ``Negative:``. Parsing is tolerant of surrounding
    whitespace and of the labels being in any case. If the response is empty,
    missing, or does not contain a positive line, the original ``raw_prompt``
    is returned as the positive prompt and a default negative prompt is used.
    """
    if not llm_response or not str(llm_response).strip():
        return (str(raw_prompt).strip(), _FALLBACK_NEGATIVE)

    text = str(llm_response)
    positive = None
    negative = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower.startswith("positive:"):
            positive = stripped[len("positive:"):].strip()
        elif lower.startswith("negative:"):
            negative = stripped[len("negative:"):].strip()

    if positive is None or not positive:
        positive = str(raw_prompt).strip()
    if negative is None or not negative:
        negative = _FALLBACK_NEGATIVE

    return (positive, negative)


class PSN_PromptEnhancer:
    """Expand a short prompt into a detailed, model-specific prompt.

    Pure-logic core: builds the system prompt and parses a supplied LLM
    response. No network or LLM inference is performed in this module.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_prompt": ("STRING", {"default": "", "multiline": True}),
                "target_model": (list(_TARGET_MODELS),),
                "verbosity": ("INT", {"default": 3, "min": _VERBOSITY_MIN, "max": _VERBOSITY_MAX, "step": 1}),
                # The fetched LLM response (plain text). In a full node this
                # would be produced by the llama.cpp connection node.
                "llm_response": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("enhanced_prompt", "negative_prompt")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_prompt, target_model, verbosity, llm_response):
        # Validate the target model (raises ValueError on bad input).
        build_system_prompt(target_model, verbosity)
        positive, negative = parse_llm_response(llm_response, raw_prompt)
        return (positive, negative)


NODE_CLASS_MAPPINGS = {"PSN_PromptEnhancer": PSN_PromptEnhancer}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_PromptEnhancer": "PSN Prompt Enhancer"}
