"""Structured Character Prompt Builder.

Pure-logic ComfyUI custom node that assembles a detailed character prompt from
modular text blocks (identity, hair, outfit, accessories, pose, background,
style modifiers). It concatenates the provided fields in a fixed order, drops
empty/whitespace-only fields, joins the remainder with commas, and optionally
produces a standard negative prompt. A ``max_length`` input truncates the final
positive prompt to a safe length.

This module is pure Python standard library only. It performs no GPU/torch work,
no ComfyUI internals, no network, no file/OS access, and no eval/exec. It only
takes and returns plain values (strings, booleans, numbers).
"""

import re

CAT = "ParametricStudio/Character"

# Fixed assembly order for the positive prompt.
_FIELD_ORDER = (
    "identity",
    "hair_style",
    "hair_color",
    "outfit",
    "accessories",
    "pose",
    "background",
    "style_modifiers",
)

# Standard negative prompt fragments, grouped by character type.
_NEGATIVE_BASE = ("low quality", "blurry", "extra limbs", "deformed", "bad anatomy")
_NEGATIVE_BY_TYPE = {
    "portrait": ("watermark", "text", "signature", "cropped"),
    "character": ("duplicate", "extra fingers", "mutated hands"),
    "animal": ("human face", "anthropomorphic"),
}


def _clean_field(value):
    """Return a normalized, non-empty string for a single prompt field.

    Strips surrounding whitespace, collapses internal runs of whitespace to a
    single space, and returns an empty string when nothing meaningful remains.
    """
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_accessories(value):
    """Split a comma-separated accessories string into cleaned items."""
    if value is None:
        return []
    parts = str(value).split(",")
    items = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip()
        if cleaned:
            items.append(cleaned)
    return items


def _build_negative_prompt(character_type, include_negative):
    """Build the negative prompt string, or an empty string when disabled."""
    if not include_negative:
        return ""
    fragments = list(_NEGATIVE_BASE)
    key = (character_type or "").strip().lower()
    if key in _NEGATIVE_BY_TYPE:
        fragments.extend(_NEGATIVE_BY_TYPE[key])
    return ", ".join(fragments)


def _truncate(text, max_length):
    """Truncate ``text`` to ``max_length`` characters, avoiding a dangling comma."""
    if max_length is None or max_length <= 0:
        return text
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    # Avoid ending on a comma or partial word boundary.
    truncated = truncated.rstrip(", ")
    return truncated


class PSN_Character_Prompt_Builder:
    """Assemble a structured character prompt from modular text blocks."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "identity": ("STRING", {"default": "", "multiline": True}),
                "hair_style": ("STRING", {"default": "", "multiline": True}),
                "hair_color": ("STRING", {"default": "", "multiline": True}),
                "accessories": ("STRING", {"default": "", "multiline": True}),
                "pose": ("STRING", {"default": "", "multiline": True}),
                "outfit": ("STRING", {"default": "", "multiline": True}),
                "background": ("STRING", {"default": "", "multiline": True}),
                "style_modifiers": ("STRING", {"default": "", "multiline": True}),
                "include_negative": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "character_type": ("STRING", {"default": "character"}),
                "max_length": ("INT", {"default": 0, "min": 0, "max": 100000}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        identity,
        hair_style,
        hair_color,
        accessories,
        pose,
        outfit,
        background,
        style_modifiers,
        include_negative,
        character_type="character",
        max_length=0,
    ):
        raw = {
            "identity": identity,
            "hair_style": hair_style,
            "hair_color": hair_color,
            "outfit": outfit,
            "accessories": accessories,
            "pose": pose,
            "background": background,
            "style_modifiers": style_modifiers,
        }

        # Build the ordered list of cleaned fragments. Accessories are split so
        # that each item becomes its own comma-separated token.
        fragments = []
        for name in _FIELD_ORDER:
            value = raw[name]
            if name == "accessories":
                fragments.extend(_split_accessories(value))
            else:
                cleaned = _clean_field(value)
                if cleaned:
                    fragments.append(cleaned)

        positive_prompt = ", ".join(fragments)
        positive_prompt = _truncate(positive_prompt, max_length)

        negative_prompt = _build_negative_prompt(character_type, include_negative)

        return (positive_prompt, negative_prompt)


NODE_CLASS_MAPPINGS = {
    "PSN_Character_Prompt_Builder": PSN_Character_Prompt_Builder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Character_Prompt_Builder": "PSN Character Prompt Builder",
}
