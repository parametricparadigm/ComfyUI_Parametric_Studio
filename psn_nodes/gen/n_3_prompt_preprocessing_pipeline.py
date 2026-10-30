import re
import json

CAT = "ParametricStudio/Prompt"


class PSN_PromptCleaner:
    """Clean, normalize, and transform a raw prompt string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_prompt": ("STRING", {"default": "", "multiline": True}),
                "normalize_case": ("BOOLEAN", {"default": True}),
                "remove_punctuation": ("BOOLEAN", {"default": True}),
                "max_length": ("INT", {"default": 512, "min": 1, "max": 10000}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("clean_prompt", "char_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_prompt, normalize_case, remove_punctuation, max_length):
        if raw_prompt is None:
            raw_prompt = ""
        text = str(raw_prompt)

        # Collapse whitespace (newlines, tabs, multiple spaces)
        text = re.sub(r"\s+", " ", text).strip()

        if normalize_case:
            text = text.lower()

        if remove_punctuation:
            # Remove common punctuation but keep spaces
            text = re.sub(r"[\.,;:!?'\"\-\(\)\[\]\{\}/\\@#$%^&*+=~`|]", "", text)
            # Collapse any whitespace created by removal
            text = re.sub(r"\s+", " ", text).strip()

        if len(text) > max_length:
            text = text[:max_length]

        return (text, len(text))


class PSN_PromptSplitter:
    """Split a prompt into parts by a delimiter, returning a JSON array of strings."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "delimiter": ("STRING", {"default": ","}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("parts",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, delimiter):
        if prompt is None:
            prompt = ""
        if delimiter is None or delimiter == "":
            raise ValueError("delimiter must be a non-empty string")

        text = str(prompt)
        parts = text.split(delimiter)
        # Strip whitespace from each part
        parts = [p.strip() for p in parts]
        # Remove empty strings
        parts = [p for p in parts if p]

        return (json.dumps(parts),)


NODE_CLASS_MAPPINGS = {
    "PSN_PromptCleaner": PSN_PromptCleaner,
    "PSN_PromptSplitter": PSN_PromptSplitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PromptCleaner": "Prompt Cleaner",
    "PSN_PromptSplitter": "Prompt Splitter",
}
