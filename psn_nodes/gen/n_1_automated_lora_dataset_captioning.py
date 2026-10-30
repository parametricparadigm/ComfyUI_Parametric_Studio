"""ParametricStudio: Automated LoRA Dataset Captioning.

Implements the core, torch/stdlib-only parts of the spec:

* PSN_VLM_Caption_Generator: builds a style-specific system prompt for a VLM,
  extracts deterministic image statistics (mean brightness, contrast,
  dominant hue bucket) from the IMAGE tensor, and produces a caption plus a
  heuristic confidence score.  The actual VLM inference is NOT implemented
  (no transformers / llama-cpp-python available); the node accepts an optional
  ``llm_handle`` object that, if it exposes a ``generate(prompt, image_stats)``
  method, will be used to produce the raw text.  Otherwise a deterministic
  template caption is produced from the image statistics so the node remains
  fully testable on CPU.

* PSN_Caption_Auditor: validates a caption against banned/allowed term lists
  using plain string/regex matching.
"""

import re

import torch

CAT = "ParametricStudio/LLM Captioning"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_image_tensor(image):
    """Validate and return a float torch tensor of shape [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image must have shape [B, H, W, C], got %s" % (tuple(image.shape),))
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError("image channel count must be 1, 3 or 4, got %d" % image.shape[-1])
    if not torch.is_floating_point(image):
        raise TypeError("image must be a floating point tensor")
    if image.numel() == 0:
        raise ValueError("image tensor is empty")
    return image


def _image_stats(image):
    """Compute deterministic, cheap image statistics on CPU."""
    img = image.detach().to(torch.float32).cpu()
    rgb = img[..., :3]
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    mean_brightness = float(lum.mean().item())
    contrast = float(lum.std().item()) if lum.numel() > 1 else 0.0

    r = float(rgb[..., 0].mean().item())
    g = float(rgb[..., 1].mean().item())
    b = float(rgb[..., 2].mean().item())
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx - mn < 0.05:
        dominant_hue = "neutral"
    elif mx == r:
        dominant_hue = "red"
    elif mx == g:
        dominant_hue = "green"
    else:
        dominant_hue = "blue"

    return {
        "mean_brightness": mean_brightness,
        "contrast": contrast,
        "dominant_hue": dominant_hue,
        "width": int(image.shape[2]),
        "height": int(image.shape[1]),
        "batch": int(image.shape[0]),
    }


def _brightness_word(v):
    if v < 0.25:
        return "dark"
    if v < 0.5:
        return "dim"
    if v < 0.75:
        return "bright"
    return "very bright"


def _contrast_word(v):
    if v < 0.08:
        return "low contrast"
    if v < 0.2:
        return "medium contrast"
    return "high contrast"


def _build_system_prompt(caption_style, negative_prompt_hint):
    base = {
        "detailed": (
            "You are a precise image captioner for LoRA training datasets. "
            "Write a detailed, factual caption describing subject, setting, "
            "lighting, composition and style. Do not invent objects that are "
            "not visible."
        ),
        "concise": (
            "You are a concise image captioner. Describe the image in one "
            "short sentence, focusing on the main subject."
        ),
        "booru_tags": (
            "You are an image tagger. Output a comma-separated list of booru-style "
            "tags (lowercase, underscore-separated) describing the image. "
            "No full sentences."
        ),
        "natural_language": (
            "You are a natural-language image captioner. Write a fluent, "
            "human-like sentence or two describing the image."
        ),
    }
    prompt = base.get(caption_style, base["detailed"])
    if negative_prompt_hint and negative_prompt_hint.strip():
        prompt += " Avoid mentioning: %s." % negative_prompt_hint.strip()
    return prompt


def _template_caption(stats, caption_style):
    """Deterministic fallback caption built from image statistics."""
    bright = _brightness_word(stats["mean_brightness"])
    contrast = _contrast_word(stats["contrast"])
    hue = stats["dominant_hue"]
    size = "%dx%d" % (stats["width"], stats["height"])

    if caption_style == "booru_tags":
        tags = ["image", size, bright, contrast.replace(" ", "_")]
        if hue != "neutral":
            tags.append(hue + "_tone")
        return ", ".join(tags)

    if caption_style == "concise":
        return "A %s image with %s, %s tones." % (bright, contrast, hue)

    if caption_style == "natural_language":
        return (
            "This is a %s image (%s) with %s and %s color tones." % (
                bright, size, contrast, hue
            )
        )

    return (
        "A %s image of size %s. The overall lighting is %s with %s. "
        "The dominant color tone is %s. Composition and subject details "
        "would be provided by the VLM in a full deployment." % (
            bright, size, bright, contrast, hue
        )
    )


def _confidence_score(caption, caption_style):
    """Heuristic confidence in [0, 1] based on length and structure."""
    if not caption or not caption.strip():
        return 0.0
    text = caption.strip()
    n_chars = len(text)
    n_words = len(text.split())

    if n_chars < 10:
        base = 0.2
    elif n_chars < 40:
        base = 0.5
    elif n_chars < 120:
        base = 0.8
    else:
        base = 1.0

    if caption_style == "booru_tags":
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if parts:
            good = sum(1 for p in parts if re.fullmatch(r"[a-z0-9_]+", p) is not None)
            base = min(1.0, base * (good / len(parts)))
        else:
            base = 0.1
    else:
        if n_words < 2:
            base *= 0.5

    return round(max(0.0, min(1.0, base)), 4)


def _parse_caption(raw, caption_style):
    """Light parsing / normalisation of the raw VLM (or template) output."""
    if raw is None:
        return ""
    text = str(raw).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        text = text[1:-1].strip()
    if caption_style == "booru_tags":
        parts = []
        seen = set()
        for p in text.split(","):
            tag = re.sub(r"\s+", "_", p.strip().lower())
            tag = re.sub(r"[^a-z0-9_]", "", tag)
            if tag and tag not in seen:
                seen.add(tag)
                parts.append(tag)
        text = ", ".join(parts)
    return text


# ---------------------------------------------------------------------------
# Node 1: PSN_VLM_Caption_Generator
# ---------------------------------------------------------------------------


class PSN_VLM_Caption_Generator:
    """Generate a caption for an image using a VLM handle (or a deterministic
    template fallback when no handle is provided).

    NOTE: Real VLM inference (transformers / llama-cpp-python) is NOT
    implemented in this module.  If ``llm_handle`` is provided and exposes a
    ``generate(prompt, image_stats)`` callable, its return value is used as
    the raw caption text.  Otherwise a deterministic template caption is
    produced from image statistics so the node is fully testable on CPU.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "caption_style": (
                    ["detailed", "concise", "booru_tags", "natural_language"],
                ),
            },
            "optional": {
                "llm_handle": ("PSN_LLM_HANDLE",),
                "negative_prompt_hint": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("caption", "confidence_score")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, caption_style, llm_handle=None, negative_prompt_hint=""):
        img = _as_image_tensor(image)
        stats = _image_stats(img)
        system_prompt = _build_system_prompt(caption_style, negative_prompt_hint)

        raw = None
        if llm_handle is not None and hasattr(llm_handle, "generate"):
            try:
                raw = llm_handle.generate(system_prompt, stats)
            except Exception:
                raw = None

        if raw is None or not str(raw).strip():
            raw = _template_caption(stats, caption_style)

        caption = _parse_caption(raw, caption_style)
        confidence = _confidence_score(caption, caption_style)
        return (caption, confidence)


# ---------------------------------------------------------------------------
# Node 2: PSN_Caption_Auditor
# ---------------------------------------------------------------------------


def _split_terms(s):
    if not s:
        return []
    return [t.strip().lower() for t in str(s).split(",") if t.strip()]


class PSN_Caption_Auditor:
    """Validate a caption against banned and allowed term lists.

    * ``banned_terms``: comma-separated list; if any appear (case-insensitive
      substring match) the caption is invalid.
    * ``allowed_terms``: comma-separated list; if non-empty, at least one of
      these terms must appear in the caption for it to be valid.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "caption": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "allowed_terms": ("STRING", {"default": "", "multiline": True}),
                "banned_terms": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_valid", "correction_suggestion")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, caption, allowed_terms="", banned_terms=""):
        if caption is None:
            caption = ""
        text = str(caption)
        low = text.lower()

        banned = _split_terms(banned_terms)
        allowed = _split_terms(allowed_terms)

        problems = []

        found_banned = []
        for term in banned:
            if term and term in low:
                found_banned.append(term)
        if found_banned:
            problems.append("banned terms present: %s" % ", ".join(found_banned))

        if allowed:
            present = [t for t in allowed if t in low]
            if not present:
                problems.append(
                    "none of the allowed terms present: %s" % ", ".join(allowed)
                )

        if not text.strip():
            problems.append("caption is empty")

        is_valid = len(problems) == 0

        if is_valid:
            suggestion = ""
        else:
            parts = []
            for term in found_banned:
                parts.append("remove '%s'" % term)
            if allowed and not any(t in low for t in allowed):
                parts.append("include at least one of: %s" % ", ".join(allowed))
            if not text.strip():
                parts.append("provide a non-empty caption")
            suggestion = "; ".join(parts) if parts else "; ".join(problems)

        return (is_valid, suggestion)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_VLM_Caption_Generator": PSN_VLM_Caption_Generator,
    "PSN_Caption_Auditor": PSN_Caption_Auditor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VLM_Caption_Generator": "VLM Caption Generator",
    "PSN_Caption_Auditor": "Caption Auditor",
}
