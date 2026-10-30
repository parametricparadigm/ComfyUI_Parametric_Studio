"""
PSN String Preprocessing Pipeline

This module provides pure-logic string cleaning and normalization nodes for ComfyUI.
It does not use torch, ComfyUI internals, network, file I/O, or subprocess.
It only uses the Python standard library (unicodedata, re).

Nodes:
- PSN_String_Cleaner: Applies cleaning operations (whitespace removal, lowercasing, punctuation removal).
- PSN_String_Normalizer: Normalizes Unicode text to a specified form (NFC, NFD, NFKC, NFKD).
"""

import unicodedata
import re

CAT = "ParametricStudio/String"

# Pre-compiled regex for punctuation removal
_PUNCTUATION_RE = re.compile(r'[^\w\s]', re.UNICODE)

# Allowed normalization forms
_NORMALIZATION_FORMS = ["NFC", "NFD", "NFKC", "NFKD"]


class PSN_String_Cleaner:
    """
    Cleans and normalizes user input text by applying specified operations:
    - remove_whitespace: Collapses multiple whitespace characters into a single space and strips leading/trailing whitespace.
    - lowercase: Converts the text to lowercase.
    - remove_punctuation: Removes all punctuation characters.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True}),
                "remove_whitespace": ("BOOLEAN", {"default": True}),
                "lowercase": ("BOOLEAN", {"default": False}),
                "remove_punctuation": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("cleaned_text",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, text, remove_whitespace, lowercase, remove_punctuation):
        result = text

        if remove_whitespace:
            # Collapse all whitespace sequences into a single space, then strip
            result = re.sub(r'\s+', ' ', result).strip()

        if lowercase:
            result = result.lower()

        if remove_punctuation:
            # Remove all non-word, non-whitespace characters
            result = _PUNCTUATION_RE.sub('', result)
            # After removing punctuation, there might be double spaces, so collapse again if whitespace removal was requested
            if remove_whitespace:
                result = re.sub(r'\s+', ' ', result).strip()

        return (result,)


class PSN_String_Normalizer:
    """
    Normalizes Unicode text to a specified normalization form:
    - NFC: Canonical Composition with Canonical Ordering
    - NFD: Canonical Decomposition with Canonical Ordering
    - NFKC: Compatibility Composition with Canonical Ordering
    - NFKD: Compatibility Decomposition with Canonical Ordering
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True}),
                "normalization_form": (_NORMALIZATION_FORMS,),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("normalized_text",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, text, normalization_form):
        if normalization_form not in _NORMALIZATION_FORMS:
            raise ValueError(f"Invalid normalization form: {normalization_form}. Must be one of {_NORMALIZATION_FORMS}")
        
        normalized = unicodedata.normalize(normalization_form, text)
        return (normalized,)


NODE_CLASS_MAPPINGS = {
    "PSN_String_Cleaner": PSN_String_Cleaner,
    "PSN_String_Normalizer": PSN_String_Normalizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_String_Cleaner": "PSN String Cleaner",
    "PSN_String_Normalizer": "PSN String Normalizer",
}
