"""PSN_Prompt_Adherence_Checker: Verifies that a generated prompt matches intended style/content constraints before execution.

This module implements the pure-logic, secure-by-design part of the spec. It does NOT open sockets, call LLMs, or perform any network/file I/O.
Instead, it provides:
1. A safe constraint parser/validator (JSON text -> normalized dict with allow-listed keys).
2. A deterministic local adherence checker (must_include / must_exclude / min_length / max_length) that produces a boolean verdict and a human-readable violation report.
3. A node wrapper that accepts plain values (strings, JSON text) and returns (BOOLEAN, STRING).

The `llm_handle` input is accepted for interface compatibility but is NOT used for any network call; the node performs local deterministic checks only.
"""

import json
import re

# Allowed top-level keys in the constraints JSON
_ALLOWED_CONSTRAINT_KEYS = {"must_include", "must_exclude", "min_length", "max_length"}
# Allowed types for each key
_ALLOWED_KEY_TYPES = {
    "must_include": list,
    "must_exclude": list,
    "min_length": int,
    "max_length": int,
}

def _psn_validate_constraints(constraints_json: str) -> dict:
    """Parse and validate a constraints JSON string. Returns a normalized dict.
    Raises ValueError on invalid JSON or disallowed keys/types."""
    if not isinstance(constraints_json, str):
        raise ValueError("constraints must be a JSON string")
    try:
        data = json.loads(constraints_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in constraints: {e}")
    if not isinstance(data, dict):
        raise ValueError("constraints JSON must be an object")
    normalized = {}
    for key, value in data.items():
        if key not in _ALLOWED_CONSTRAINT_KEYS:
            raise ValueError(f"Disallowed constraint key: {key!r}")
        expected_type = _ALLOWED_KEY_TYPES[key]
        if not isinstance(value, expected_type):
            raise ValueError(f"Constraint {key!r} must be of type {expected_type.__name__}")
        if key in ("must_include", "must_exclude"):
            if not all(isinstance(item, str) for item in value):
                raise ValueError(f"Constraint {key!r} must be a list of strings")
            normalized[key] = [item.lower() for item in value]
        else:
            if value < 0:
                raise ValueError(f"Constraint {key!r} must be non-negative")
            normalized[key] = value
    return normalized

def _psn_check_adherence(prompt: str, constraints: dict) -> tuple:
    """Deterministically check prompt against constraints.
    Returns (is_compliant: bool, violation_report: str)."""
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    violations = []
    prompt_lower = prompt.lower()
    if "must_include" in constraints:
        for term in constraints["must_include"]:
            if term and term not in prompt_lower:
                violations.append(f"Missing required term: {term!r}")
    if "must_exclude" in constraints:
        for term in constraints["must_exclude"]:
            if term and term in prompt_lower:
                violations.append(f"Contains forbidden term: {term!r}")
    if "min_length" in constraints:
        if len(prompt) < constraints["min_length"]:
            violations.append(f"Prompt length {len(prompt)} is below minimum {constraints['min_length']}")
    if "max_length" in constraints:
        if len(prompt) > constraints["max_length"]:
            violations.append(f"Prompt length {len(prompt)} exceeds maximum {constraints['max_length']}")
    if violations:
        report = "Violations found:\n" + "\n".join(f"- {v}" for v in violations)
        return (False, report)
    return (True, "No violations detected.")

class PSN_Prompt_Adherence_Checker:
    """Verifies that a generated prompt matches intended style/content constraints before execution.
    Uses deterministic local checks (no LLM/network). The llm_handle input is accepted for interface
    compatibility but is not used for any external call."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "constraints": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "llm_handle": ("PSN_LLM_HANDLE",),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_compliant", "violation_report")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Adherence"

    def run(self, prompt: str, constraints: str, llm_handle=None):
        """Run the adherence check. Returns (is_compliant, violation_report)."""
        normalized = _psn_validate_constraints(constraints)
        is_compliant, report = _psn_check_adherence(prompt, normalized)
        return (is_compliant, report)

NODE_CLASS_MAPPINGS = {
    "PSN_Prompt_Adherence_Checker": PSN_Prompt_Adherence_Checker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Prompt_Adherence_Checker": "PSN Prompt Adherence Checker",
}
