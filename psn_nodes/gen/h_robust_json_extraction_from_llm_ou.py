"""Robust JSON extraction from LLM output.

Extracts the first valid JSON object (or array) from a raw LLM text response,
tolerating surrounding prose, code fences, nested braces, and escaped quotes.
"""

import json
import re

CAT = "ParametricStudio/Text"


def _scan_json(text, start):
    """Scan from `start` for a balanced JSON object or array.

    Returns (parsed_value, end_index) or (None, -1) if no valid JSON found.
    Handles nested braces/brackets and escaped quotes inside strings.
    """
    # Find the next '{' or '['
    i = start
    while i < len(text):
        ch = text[i]
        if ch in ('{', '['):
            break
        i += 1
    if i >= len(text):
        return None, -1

    open_ch = text[i]
    close_ch = '}' if open_ch == '{' else ']'
    depth = 0
    in_string = False
    escape = False
    j = i
    while j < len(text):
        c = text[j]
        if in_string:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    candidate = text[i:j + 1]
                    try:
                        return json.loads(candidate), j + 1
                    except (json.JSONDecodeError, ValueError):
                        # Not valid JSON; continue scanning after this open
                        return None, -1
        j += 1
    return None, -1


def extract_first_json(text):
    """Extract the first valid JSON object or array from raw LLM text.

    Handles:
    - JSON wrapped in markdown code fences ( ... )
    - Surrounding prose before/after the JSON
    - Nested braces and brackets
    - Escaped quotes inside strings
    - Multiple JSON objects (returns the first valid one)

    Returns (parsed_value, error_message). On success error_message is "".
    On failure parsed_value is None and error_message describes the problem.
    """
    if not isinstance(text, str):
        return None, "Input is not a string"
    if not text.strip():
        return None, "Input is empty"

    # Try to find JSON starting at each '{' or '[' position
    # First pass: try the whole text as-is (fast path)
    stripped = text.strip()
    if stripped.startswith('{') or stripped.startswith('['):
        val, _ = _scan_json(stripped, 0)
        if val is not None:
            return val, ""

    # Second pass: strip markdown code fences if present
    fence_match = re.search(r'(?:json)?\s*\n?(.*?)', text, re.DOTALL)
    if fence_match:
        inner = fence_match.group(1).strip()
        if inner.startswith('{') or inner.startswith('['):
            val, _ = _scan_json(inner, 0)
            if val is not None:
                return val, ""

    # Third pass: scan for any '{' or '[' in the text
    i = 0
    while i < len(text):
        if text[i] in ('{', '['):
            val, end = _scan_json(text, i)
            if val is not None:
                return val, ""
            # If _scan_json failed, skip past this opening char and try next
            i += 1
        else:
            i += 1

    return None, "No valid JSON object or array found in input"


class PSN_ExtractJsonFromLLM:
    """Extract the first valid JSON object/array from raw LLM text output.

    Handles markdown code fences, surrounding prose, nested braces,
    and escaped quotes. Returns the parsed JSON as a string and an
    error message (empty on success).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "llm_output": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_string", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, llm_output):
        val, err = extract_first_json(llm_output)
        if val is not None:
            json_str = json.dumps(val, ensure_ascii=False)
        else:
            json_str = ""
        return (json_str, err)


NODE_CLASS_MAPPINGS = {
    "PSN_ExtractJsonFromLLM": PSN_ExtractJsonFromLLM,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ExtractJsonFromLLM": "Extract JSON from LLM Output",
}
