"""ParametricStudio - Automated Scene Prompt Compiler.

Converts plain-language scene descriptions plus layout / camera data into a
clean, comma-separated tag prompt suitable for video models.

Deterministic, pure-Python (re + string + json). No network, no subprocess.
"""

import json
import re
import string

CAT = "ParametricStudio/Scene"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Common filler words that carry no visual meaning for a tag prompt.
_FILLER_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "of", "is",
    "are", "was", "were", "be", "being", "with", "for", "from", "by", "as",
    "it", "its", "this", "that", "these", "those", "he", "she", "they", "we",
    "i", "you", "his", "her", "their", "our", "your", "my", "me", "him",
    "them", "us", "who", "whom", "which", "what", "when", "where", "how",
    "can", "could", "will", "would", "shall", "should", "may", "might",
    "must", "do", "does", "did", "done", "having", "has", "have", "had",
    "there", "here", "then", "than", "so", "if", "not", "no", "yes",
    "very", "really", "just", "quite", "rather", "somewhat", "slightly",
    "into", "onto", "upon", "over", "under", "through", "across", "along",
    "around", "behind", "before", "after", "between", "among", "within",
    "without", "toward", "towards", "against", "up", "down", "out", "off",
    "again", "further", "once", "now", "also", "too", "only", "own",
    "same", "such", "both", "each", "few", "more", "most", "other", "some",
    "any", "all", "am", "been", "get", "got", "make", "made",
    "take", "took", "go", "went", "come", "came", "see", "saw",
    "say", "said", "tell", "told", "know", "knew", "think",
    "thought", "want", "wanted", "need", "needed", "use", "used", "let",
    "left", "put", "seem", "seemed", "feel", "felt", "find", "found",
    "give", "gave", "keep", "kept", "begin", "began",
    "start", "started", "end", "ended", "move", "moved",
    "run", "ran", "turn", "turned", "turning",
}

# Spatial keywords that map to canonical tag phrases.
_SPATIAL_MAP = {
    "center": "center frame",
    "centre": "center frame",
    "middle": "center frame",
    "left": "left of frame",
    "right": "right of frame",
    "top": "top of frame",
    "bottom": "bottom of frame",
    "foreground": "foreground",
    "background": "background",
    "midground": "midground",
    "close-up": "close-up shot",
    "close up": "close-up shot",
    "wide": "wide shot",
    "medium": "medium shot",
    "long shot": "long shot",
    "extreme close-up": "extreme close-up shot",
    "extreme close up": "extreme close-up shot",
    "over-the-shoulder": "over-the-shoulder shot",
    "over the shoulder": "over-the-shoulder shot",
    "low angle": "low angle shot",
    "high angle": "high angle shot",
    "eye level": "eye level shot",
    "aerial": "aerial shot",
    "drone": "drone shot",
    "pov": "pov shot",
    "point of view": "pov shot",
}

# Camera-move keywords -> canonical tag phrases.
_CAMERA_MAP = {
    "static": "static shot",
    "static shot": "static shot",
    "locked off": "static shot",
    "locked-off": "static shot",
    "pan": "pan shot",
    "pan left": "pan left shot",
    "pan right": "pan right shot",
    "pan up": "pan up shot",
    "pan down": "pan down shot",
    "tilt": "tilt shot",
    "tilt up": "tilt up shot",
    "tilt down": "tilt down shot",
    "dolly in": "dolly in shot",
    "dolly out": "dolly out shot",
    "dolly left": "dolly left shot",
    "dolly right": "dolly right shot",
    "tracking": "tracking shot",
    "tracking shot": "tracking shot",
    "crane": "crane shot",
    "crane up": "crane up shot",
    "crane down": "crane down shot",
    "zoom in": "zoom in shot",
    "zoom out": "zoom out shot",
    "handheld": "handheld shot",
    "steadicam": "steadicam shot",
    "orbit": "orbit shot",
    "orbit left": "orbit left shot",
    "orbit right": "orbit right shot",
    "whip pan": "whip pan shot",
    "crash zoom": "crash zoom shot",
    "slow motion": "slow motion",
    "time lapse": "time lapse",
    "timelapse": "time lapse",
    "hyperlapse": "hyperlapse",
}

# Quality / style boosters appended at the end (kept short to avoid bloat).
_QUALITY_TAGS = ("cinematic", "high detail", "sharp focus")

# Maximum number of tags in the final prompt (bloat guard).
_MAX_TAGS = 40


def _clean_tag(tag):
    """Lowercase, strip punctuation, collapse whitespace."""
    tag = tag.strip().lower()
    tag = tag.strip(string.punctuation)
    tag = re.sub(r"\s+", " ", tag)
    return tag


def _split_tags(text):
    """Split a comma / semicolon / pipe separated string into raw tags."""
    if not text or not isinstance(text, str):
        return []
    parts = re.split(r"[,;|/]+", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_subject_tags(raw_description):
    """Turn a plain-language description into a list of subject tags."""
    if not raw_description or not isinstance(raw_description, str):
        return []
    text = raw_description.strip().lower()
    chunks = re.split(r"[,;|/]+|\band\b|\bwith\b", text)
    tags = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        words = chunk.split()
        kept = [w for w in words if w not in _FILLER_WORDS and len(w) > 1]
        if kept:
            tags.append(" ".join(kept))
    return tags


def _extract_spatial_tags(layout_json):
    """Parse layout JSON (or plain text) and return spatial tag phrases."""
    if not layout_json or not isinstance(layout_json, str):
        return []
    text = layout_json.strip()
    data = None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        data = None

    raw_terms = []
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, str):
                raw_terms.append(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        raw_terms.append(item)
        for key in data:
            if key.lower() in _SPATIAL_MAP:
                raw_terms.append(key)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                raw_terms.append(item)
    else:
        raw_terms = [text]

    tags = []
    for term in raw_terms:
        term_lower = term.strip().lower()
        if not term_lower:
            continue
        if term_lower in _SPATIAL_MAP:
            tags.append(_SPATIAL_MAP[term_lower])
            continue
        matched = False
        for key, phrase in _SPATIAL_MAP.items():
            if key in term_lower:
                tags.append(phrase)
                matched = True
                break
        if not matched:
            tags.append(_clean_tag(term_lower))
    return tags


def _extract_camera_tags(camera_prompt_fragment):
    """Map camera-move text to canonical camera tag phrases."""
    if not camera_prompt_fragment or not isinstance(camera_prompt_fragment, str):
        return []
    text = camera_prompt_fragment.strip().lower()
    if not text:
        return []
    chunks = re.split(r"[,;|/]+|\band\b", text)
    tags = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk in _CAMERA_MAP:
            tags.append(_CAMERA_MAP[chunk])
            continue
        matched = False
        for key, phrase in _CAMERA_MAP.items():
            if key in chunk:
                tags.append(phrase)
                matched = True
                break
        if not matched:
            tags.append(_clean_tag(chunk))
    return tags


def _dedupe_preserve_order(tags):
    """Remove duplicate tags (case-insensitive) preserving first occurrence."""
    seen = set()
    out = []
    for t in tags:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def _truncate_tags(tags, max_tags=_MAX_TAGS):
    """Keep at most max_tags tags (bloat guard)."""
    return tags[:max_tags]


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_ScenePromptCompiler:
    """Compile raw scene description + layout + camera data into a tag prompt."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_description": ("STRING", {"default": "", "multiline": True}),
                "layout_json": ("STRING", {"default": "", "multiline": True}),
                "camera_prompt_fragment": ("STRING", {"default": "", "multiline": True}),
                "negative_prompt": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "quality_tags": ("STRING", {"default": ",".join(_QUALITY_TAGS), "multiline": True}),
                "max_tags": ("INT", {"default": _MAX_TAGS, "min": 1, "max": 200}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "negative_prompt")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_description, layout_json, camera_prompt_fragment,
            negative_prompt, quality_tags=None, max_tags=None):
        if max_tags is None:
            max_tags = _MAX_TAGS
        if quality_tags is None:
            quality_tags = ",".join(_QUALITY_TAGS)

        subject_tags = _extract_subject_tags(raw_description)
        spatial_tags = _extract_spatial_tags(layout_json)
        camera_tags = _extract_camera_tags(camera_prompt_fragment)

        quality_list = _split_tags(quality_tags)
        quality_list = [_clean_tag(q) for q in quality_list if _clean_tag(q)]

        all_tags = subject_tags + spatial_tags + camera_tags + quality_list
        all_tags = _dedupe_preserve_order(all_tags)
        all_tags = _truncate_tags(all_tags, max_tags)

        final_prompt = ", ".join(all_tags)

        neg_tags = _split_tags(negative_prompt)
        neg_tags = [_clean_tag(n) for n in neg_tags if _clean_tag(n)]
        neg_tags = _dedupe_preserve_order(neg_tags)
        cleaned_negative = ", ".join(neg_tags)

        return (final_prompt, cleaned_negative)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ScenePromptCompiler": PSN_ScenePromptCompiler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ScenePromptCompiler": "Scene Prompt Compiler (ParametricStudio)",
}
