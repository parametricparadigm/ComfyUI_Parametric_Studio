"""ParametricStudio - Automated Prompt Refinement for Image Pipelines.

Two nodes:
  * PSN_Prompt_Enhancer  - expands a short prompt into a detailed, model-specific
    prompt.  The spec calls for a local LLM (llama.cpp) connection, which is NOT
    available in this sandbox (no network, no external packages).  Instead the
    node performs a deterministic, rule-based expansion that mimics what a
    prompt-engineering LLM would produce: it appends model-specific style
    descriptors, quality tags and lighting/composition terms scaled by the
    `verbosity` level, and derives a sensible negative prompt per target model.
  * PSN_Prompt_Validator - scans a prompt for banned tokens, removes them,
    reports what was removed, and trims the prompt to a CLIP token budget.

Only the Python standard library is used (re, collections).  No tensors are
involved, so torch is not needed here.
"""

import re
from collections import OrderedDict

CAT = "ParametricStudio/Prompt"

# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------

# Model-specific style vocabulary.  Each entry is a list of (tag, weight_hint)
# pairs ordered from most to least important.  The enhancer picks the first
# `verbosity` entries (plus a few always-on quality tags).
_MODEL_STYLES = {
    "SDXL": [
        ("masterpiece", "best quality"),
        ("ultra detailed", "8k uhd"),
        ("cinematic lighting", "volumetric light"),
        ("sharp focus", "intricate details"),
        ("award winning photography", "trending on artstation"),
    ],
    "Flux": [
        ("highly detailed", "photorealistic"),
        ("natural lighting", "soft shadows"),
        ("clean composition", "balanced framing"),
        ("subtle color grading", "film grain"),
        ("professional photography", "high dynamic range"),
    ],
    "SD1.5": [
        ("masterpiece", "best quality"),
        ("highly detailed", "detailed background"),
        ("dramatic lighting", "rim light"),
        ("sharp focus", "fine details"),
        ("digital art", "concept art"),
    ],
}

# Always appended quality tags (kept short so they never blow the token budget).
_QUALITY_TAGS = ("high quality", "well composed")

# Default negative prompts per target model.
_NEGATIVE_BASE = {
    "SDXL": "blurry, low quality, distorted, deformed, watermark, text, signature, worst quality, jpeg artifacts",
    "Flux": "blurry, low quality, overexposed, underexposed, watermark, text, signature, distorted anatomy",
    "SD1.5": "blurry, low quality, deformed, disfigured, bad anatomy, watermark, text, signature, extra limbs",
}

# Approximate CLIP token budget.  CLIP ViT-L/14 uses 77 tokens; we allow a
# slightly generous 75 so the prompt + trailing tokens fit.
CLIP_TOKEN_LIMIT = 75

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tokenize(text):
    """Very rough word tokenizer: split on whitespace and punctuation.

    This is intentionally simple (no external tokenizer dependency).  It is
    good enough to enforce a token budget and to find banned words.
    """
    if not text:
        return []
    return re.findall(r"[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*", text)


def _count_tokens(text):
    return len(_tokenize(text))


def _truncate_to_tokens(text, limit):
    """Return `text` truncated so that its token count is <= limit.

    We rebuild the string from the first `limit` tokens, preserving the
    original casing of each token where possible.
    """
    tokens = _tokenize(text)
    if len(tokens) <= limit:
        return text.strip()
    # Rebuild with original casing: walk the original string and keep the
    # first `limit` token matches.
    kept = []
    remaining = limit
    for m in re.finditer(r"[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*", text):
        if remaining <= 0:
            break
        kept.append(m.group(0))
        remaining -= 1
    return ", ".join(kept)


# ---------------------------------------------------------------------------
# Node 1: PSN_Prompt_Enhancer
# ---------------------------------------------------------------------------


class PSN_Prompt_Enhancer:
    """Expand a short prompt into a detailed, model-specific prompt.

    NOTE: The original spec calls for a local LLM (llama.cpp) connection.
    That is NOT implemented here because the sandbox has no network access
    and no external packages.  Instead a deterministic rule-based expansion
    is used: model-specific style descriptors are appended in order of
    importance, scaled by `verbosity`, plus a small set of quality tags.
    A sensible negative prompt is derived from the target model.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_prompt": ("STRING", {"default": "", "multiline": True}),
                "target_model": (list(_MODEL_STYLES.keys()),),
                "verbosity": ("INT", {"default": 3, "min": 1, "max": 5}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("enhanced_prompt", "negative_prompt")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_prompt, target_model, verbosity):
        # --- validate inputs ------------------------------------------------
        if not isinstance(raw_prompt, str):
            raise TypeError("raw_prompt must be a string")
        if target_model not in _MODEL_STYLES:
            raise ValueError(
                "target_model must be one of %s, got %r"
                % (list(_MODEL_STYLES.keys()), target_model)
            )
        verbosity = int(verbosity)
        if not 1 <= verbosity <= 5:
            raise ValueError("verbosity must be in 1..5, got %r" % (verbosity,))

        raw = raw_prompt.strip()
        if not raw:
            # Empty prompt: return a minimal placeholder so downstream nodes
            # still get a usable string.
            enhanced = ", ".join(_QUALITY_TAGS)
            negative = _NEGATIVE_BASE[target_model]
            return (enhanced, negative)

        # --- build the enhanced prompt --------------------------------------
        parts = [raw]
        styles = _MODEL_STYLES[target_model]
        # Pick up to `verbosity` style entries.
        for entry in styles[:verbosity]:
            parts.append(", ".join(entry))
        # Always add quality tags.
        parts.append(", ".join(_QUALITY_TAGS))

        enhanced = ", ".join(parts)
        # Enforce the CLIP token budget.
        enhanced = _truncate_to_tokens(enhanced, CLIP_TOKEN_LIMIT)

        negative = _NEGATIVE_BASE[target_model]
        return (enhanced, negative)


# ---------------------------------------------------------------------------
# Node 2: PSN_Prompt_Validator
# ---------------------------------------------------------------------------


class PSN_Prompt_Validator:
    """Check a prompt for banned tokens and structural issues.

    * Removes any token that appears in `ban_list` (comma-separated).
    * Reports which tokens were removed in `warnings`.
    * Trims the prompt to the CLIP token budget.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "ban_list": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("valid_prompt", "warnings")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, ban_list):
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if not isinstance(ban_list, str):
            raise TypeError("ban_list must be a string")

        # Parse the ban list into a set of lower-cased tokens.
        banned = set()
        for piece in ban_list.split(","):
            piece = piece.strip().lower()
            if piece:
                banned.add(piece)

        if not prompt.strip():
            return ("", "")

        # Walk the prompt, removing banned tokens.
        removed = []
        kept = []
        for m in re.finditer(r"[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*", prompt):
            tok = m.group(0)
            if tok.lower() in banned:
                removed.append(tok)
            else:
                kept.append(tok)

        # Rebuild the prompt from kept tokens, preserving original casing.
        valid = ", ".join(kept)

        # Enforce the CLIP token budget.
        valid = _truncate_to_tokens(valid, CLIP_TOKEN_LIMIT)

        # Build the warnings string.
        if removed:
            warnings = "Removed banned tokens: " + ", ".join(removed)
        else:
            warnings = ""

        return (valid, warnings)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Prompt_Enhancer": PSN_Prompt_Enhancer,
    "PSN_Prompt_Validator": PSN_Prompt_Validator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Prompt_Enhancer": "PSN Prompt Enhancer",
    "PSN_Prompt_Validator": "PSN Prompt Validator",
}
