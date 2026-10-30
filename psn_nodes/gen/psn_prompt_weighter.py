"""PSN_Prompt_Weighter: adds weight syntax to prompt terms from a JSON weights dictionary.

Pure-logic node: takes a base prompt string and a JSON string mapping terms to numeric
weights, and returns a new prompt where each term is replaced by "term:weight" syntax.
No file, network, subprocess, or ComfyUI/torch dependencies.
"""

import json
import re

CAT = "ParametricStudio/Prompt"


def _parse_weights(weights_json):
    """Parse and validate the weights JSON string.

    Returns a dict of {term: weight} or raises ValueError on bad input.
    """
    if not isinstance(weights_json, str):
        raise ValueError("weights must be a JSON string")
    try:
        data = json.loads(weights_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in weights: {e}")
    if not isinstance(data, dict):
        raise ValueError("weights JSON must be a dictionary")
    result = {}
    for key, val in data.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("weight keys must be non-empty strings")
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"weight for '{key}' must be a number")
        if val <= 0:
            raise ValueError(f"weight for '{key}' must be positive, got {val}")
        result[key] = float(val)
    return result


def _format_weight(w):
    """Format a float weight for prompt syntax, trimming trailing zeros."""
    if w == int(w):
        return str(int(w))
    s = f"{w:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _apply_weights(prompt, weights):
    """Replace terms in prompt with weighted syntax.

    Uses word-boundary matching so that "cat" in "category" is not replaced.
    Longer terms are processed first to avoid partial replacements.
    """
    if not prompt or not weights:
        return prompt
    # Sort by length descending so longer terms are matched first
    sorted_terms = sorted(weights.keys(), key=len, reverse=True)
    result = prompt
    for term in sorted_terms:
        w = weights[term]
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(term) + r'\b'
        replacement = f"{term}:{_format_weight(w)}"
        result = re.sub(pattern, replacement, result)
    return result


class PSN_PromptWeighter:
    """Adds weight syntax to prompt terms based on a JSON weights dictionary."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "weights": ("STRING", {"default": "{}", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("weighted_prompt",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, weights):
        parsed = _parse_weights(weights)
        weighted = _apply_weights(prompt, parsed)
        return (weighted,)


NODE_CLASS_MAPPINGS = {
    "PSN_PromptWeighter": PSN_PromptWeighter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PromptWeighter": "PSN Prompt Weighter",
}
