"""PSN Batch Prompt Iteration Engine.

Pure-logic, secure-by-design implementation of a batch prompt iteration engine.

Because this module must not perform any file or OS access, the file-loading
node accepts the *text content* of a CSV or JSON document (as a plain string)
rather than a file path. The parsing logic (CSV/JSON -> list of prompt
strings) is fully implemented and unit-testable. The iterator node maintains
per-instance state to step through the prompt list.

No torch, no ComfyUI imports, no network, no subprocess, no file I/O.
"""

import csv
import io
import json

CAT = "ParametricStudio/Batch"


class PSN_Batch_Prompt_Loader:
    """Parse a CSV or JSON text payload into a list of prompt strings.

    Accepts the raw text of a CSV or JSON file (not a file path) so that no
    file-system access is required. For CSV, the first column is used as the
    prompt. For JSON, the payload must be a list of strings or a list of
    objects with a "prompt" key.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "payload": ("STRING", {"default": "", "multiline": True}),
                "format": (["csv", "json"],),
                "delimiter": ("STRING", {"default": ","}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt_list_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, payload, format, delimiter):
        if format == "csv":
            prompts = self._parse_csv(payload, delimiter)
        elif format == "json":
            prompts = self._parse_json(payload)
        else:
            raise ValueError("format must be 'csv' or 'json'")
        return (json.dumps(prompts),)

    @staticmethod
    def _parse_csv(text, delimiter):
        if not text or not text.strip():
            return []
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        prompts = []
        for row in reader:
            if not row:
                continue
            cell = row[0].strip()
            if cell:
                prompts.append(cell)
        return prompts

    @staticmethod
    def _parse_json(text):
        if not text or not text.strip():
            return []
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("JSON payload must be a list")
        prompts = []
        for item in data:
            if isinstance(item, str):
                prompts.append(item)
            elif isinstance(item, dict) and "prompt" in item:
                prompts.append(str(item["prompt"]))
            else:
                raise ValueError(
                    "Each JSON item must be a string or an object with a 'prompt' key"
                )
        return prompts


class PSN_Batch_Iterator:
    """Step through a list of prompts, returning the current prompt and
    whether the batch is complete.

    Maintains an internal index per node instance. When auto_advance is True,
    the index increments after each call. When auto_advance is False, the
    index stays at the provided (or current) position.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_list_json": ("STRING", {"default": "[]", "multiline": True}),
                "auto_advance": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "index": ("INT", {"default": 0, "min": 0, "max": 100000}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "BOOLEAN")
    RETURN_NAMES = ("current_prompt", "next_index", "is_done")
    FUNCTION = "run"
    CATEGORY = CAT

    def __init__(self):
        self._index = 0

    def run(self, prompt_list_json, auto_advance, index=None):
        prompts = json.loads(prompt_list_json) if prompt_list_json else []
        if not isinstance(prompts, list):
            raise ValueError("prompt_list_json must decode to a list")

        if index is not None:
            self._index = max(0, min(index, len(prompts)))
        else:
            self._index = max(0, min(self._index, len(prompts)))

        if self._index >= len(prompts):
            return ("", self._index, True)

        current = str(prompts[self._index])
        if auto_advance:
            self._index += 1
        next_idx = self._index
        is_done = next_idx >= len(prompts)
        return (current, next_idx, is_done)


NODE_CLASS_MAPPINGS = {
    "PSN_Batch_Prompt_Loader": PSN_Batch_Prompt_Loader,
    "PSN_Batch_Iterator": PSN_Batch_Iterator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Batch_Prompt_Loader": "PSN Batch Prompt Loader",
    "PSN_Batch_Iterator": "PSN Batch Iterator",
}
