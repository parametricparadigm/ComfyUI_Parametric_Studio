"""PSN OCR-based prompt extraction from tutorial screenshots (pure-logic core).

This module implements the *secure, pure-Python* portion of the
"OCR-Based Prompt Extraction from Tutorials" spec.

Because real OCR (Chandra / PaddleOCR / EasyOCR) requires GPU models and
third-party packages, and because ComfyUI's IMAGE/MASK tensors are not
available here, the OCR *extraction* node is implemented as a **deterministic
mock** that:
  * validates the engine / language configuration,
  * accepts a plain-text stand-in for the screenshot's OCR output,
  * returns that text plus a small, well-formed region-mask payload.

The *prompt cleaner* node is fully functional pure string logic: it strips
common UI noise, splits prompt / negative-prompt / settings sections, and
emits a JSON document suitable for import into a prompt library.

No network, file, OS, subprocess, eval/exec, or torch/comfy imports are used.
All functions take plain values (strings, numbers, booleans, JSON text).
"""

import json
import re

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/OCR"

# --- configuration ---------------------------------------------------------

OCR_ENGINES = ("Chandra", "PaddleOCR", "EasyOCR")
OCR_LANGUAGES = ("en", "zh", "multi")

# Common UI / chrome text that should be dropped from a tutorial screenshot.
# Matched case-insensitively as whole tokens.
_UI_TOKENS = (
    "submit", "cancel", "ok", "okay", "close", "back", "next", "previous",
    "save", "save as", "open", "file", "edit", "view", "help",
    "apply", "reset", "done", "confirm", "yes", "no", "browse", "upload",
    "download", "search", "menu", "home", "login", "sign in", "sign out",
    "logout", "preferences", "options", "more", "less",
    "minimize", "maximize", "restore", "close window", "x", "x close",
)

# Section markers used to split a tutorial's text into structured parts.
# Each marker is a regex pattern (case-insensitive).
_NEGATIVE_MARKERS = (
    r"negative\s*prompt\s*:",
    r"negative\s*:",
    r"neg\s*prompt\s*:",
    r"neg\s*:",
)
_SETTINGS_MARKERS = (
    r"settings\s*:",
    r"parameters\s*:",
    r"cfg\s*:",
    r"steps\s*:",
    r"sampler\s*:",
    r"seed\s*:",
    r"resolution\s*:",
    r"aspect\s*ratio\s*:",
    r"model\s*:",
    r"lora\s*:",
)


def _validate_engine(engine):
    """Return (ok, reason) for an OCR engine name."""
    if not isinstance(engine, str):
        return False, "ocr_engine must be a string"
    if engine not in OCR_ENGINES:
        return False, "ocr_engine must be one of %s" % (", ".join(OCR_ENGINES))
    return True, "ok"


def _validate_language(language):
    """Return (ok, reason) for an OCR language code."""
    if not isinstance(language, str):
        return False, "language must be a string"
    if language not in OCR_LANGUAGES:
        return False, "language must be one of %s" % (", ".join(OCR_LANGUAGES))
    return True, "ok"


def _build_region_mask(text, language):
    """Build a small, deterministic region-mask payload from OCR text.

    Returns a JSON string describing one region per non-empty line. This is a
    stand-in for a real MASK tensor; it is pure data and safe to inspect.
    """
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    regions = []
    for idx, line in enumerate(lines):
        regions.append({
            "id": idx,
            "text": line.strip(),
            "box": [0, idx * 24, max(1, len(line.strip())), 24],
            "confidence": 0.9,
        })
    return json.dumps({"language": language, "regions": regions})


def _strip_ui(text):
    """Remove common UI tokens from text, line by line."""
    if not isinstance(text, str):
        return ""
    out_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered in _UI_TOKENS:
            continue
        # Drop leading/trailing UI tokens embedded in a line.
        tokens = line.split()
        kept = [t for t in tokens if t.lower().strip(".,;:!?") not in _UI_TOKENS]
        if kept:
            out_lines.append(" ".join(kept))
    return "\n".join(out_lines)


def _match_marker(line, markers):
    """Try to match any marker regex against the line.

    Returns (matched, remainder) where remainder is the text after the marker.
    """
    for pattern in markers:
        m = re.search(pattern, line, re.IGNORECASE)
        if m:
            remainder = line[m.end():].strip(" :")
            return True, remainder
    return False, ""


def _split_sections(text):
    """Split cleaned text into (prompt, negative_prompt, settings)."""
    if not isinstance(text, str):
        return "", "", ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    prompt_parts = []
    negative_parts = []
    settings_parts = []
    current = "prompt"

    for line in lines:
        matched, remainder = _match_marker(line, _NEGATIVE_MARKERS)
        if matched:
            current = "negative"
            if remainder:
                negative_parts.append(remainder)
            continue

        matched, remainder = _match_marker(line, _SETTINGS_MARKERS)
        if matched:
            current = "settings"
            if remainder:
                settings_parts.append(remainder)
            continue

        if current == "prompt":
            prompt_parts.append(line)
        elif current == "negative":
            negative_parts.append(line)
        else:
            settings_parts.append(line)

    return (
        " ".join(prompt_parts).strip(),
        " ".join(negative_parts).strip(),
        " ".join(settings_parts).strip(),
    )


def _build_structured(prompt, negative, settings):
    """Build the structured JSON document for the prompt library."""
    doc = {
        "prompt": prompt,
        "negative_prompt": negative,
        "settings": settings,
    }
    return json.dumps(doc, ensure_ascii=False)


# --- nodes -----------------------------------------------------------------

class PSN_Tutorial_OCR_Extractor:
    """Mock OCR extractor: validates config and returns raw text + region mask.

    Real OCR is GPU/third-party; this node performs the pure-logic part only:
    configuration validation and a deterministic region-mask payload.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("STRING", {"default": "", "multiline": True,
                                     "tooltip": "Plain-text stand-in for the screenshot OCR output."}),
                "ocr_engine": (list(OCR_ENGINES),),
                "language": (list(OCR_LANGUAGES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("raw_text", "text_regions")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, ocr_engine, language):
        ok_engine, why_engine = _validate_engine(ocr_engine)
        ok_lang, why_lang = _validate_language(language)
        if not ok_engine:
            return ("", json.dumps({"error": why_engine}))
        if not ok_lang:
            return ("", json.dumps({"error": why_lang}))
        text = image if isinstance(image, str) else ""
        mask = _build_region_mask(text, language)
        return (text, mask)


class PSN_Prompt_Cleaner:
    """Clean OCR text: strip UI noise, split sections, emit library JSON."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_text": ("STRING", {"default": "", "multiline": True}),
                "remove_ui_elements": ("BOOLEAN", {"default": True}),
                "format_for_library": ("BOOLEAN", {"default": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("cleaned_prompt", "structured_data")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_text, remove_ui_elements, format_for_library):
        text = raw_text if isinstance(raw_text, str) else ""
        if remove_ui_elements:
            text = _strip_ui(text)
        prompt, negative, settings = _split_sections(text)
        cleaned = prompt
        if format_for_library:
            structured = _build_structured(prompt, negative, settings)
        else:
            structured = json.dumps({"prompt": prompt,
                                     "negative_prompt": negative,
                                     "settings": settings},
                                    ensure_ascii=False)
        return (cleaned, structured)


NODE_CLASS_MAPPINGS = {
    "PSN_Tutorial_OCR_Extractor": PSN_Tutorial_OCR_Extractor,
    "PSN_Prompt_Cleaner": PSN_Prompt_Cleaner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Tutorial_OCR_Extractor": "PSN Tutorial OCR Extractor",
    "PSN_Prompt_Cleaner": "PSN Prompt Cleaner",
}
