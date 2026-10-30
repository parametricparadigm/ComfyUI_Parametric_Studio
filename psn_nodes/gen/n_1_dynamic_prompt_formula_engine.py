"""
PSN Dynamic Prompt Formula Engine

This module provides pure-logic nodes for structured prompt generation using
hierarchical definitions (TOML) and dynamic style switching.

Because this environment restricts file/OS access and external dependencies,
the `PSN_TOML_Prompt_Loader` node accepts TOML content as a STRING (the text
of the TOML file) rather than a file path. It parses the TOML using the
standard library `tomllib` (Python 3.11+) or a minimal internal fallback
parser for simple TOML structures.

The `PSN_Style_Library_Switcher` node selects a style block from the parsed
structure and flattens it into a final prompt string.

No network, file, or GPU operations are performed.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Try to import tomllib (Python 3.11+), otherwise use a minimal fallback
try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    HAS_TOMLLIB = False

CAT = "ParametricStudio/Prompt"


def _parse_simple_toml(text: str) -> Dict[str, Any]:
    """
    Minimal TOML parser for simple structures (key = value, [section], [[array]]).
    Supports strings, numbers, booleans, and basic arrays.
    This is a fallback for Python < 3.11 or when tomllib is unavailable.
    """
    result: Dict[str, Any] = {}
    current_section: Optional[str] = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#"):
            continue
        # Check for section header
        if line.startswith("[["):
            # Array of tables - simplified: treat as list of dicts
            end = line.find("]]")
            if end != -1:
                section_name = line[2:end].strip()
                if section_name not in result:
                    result[section_name] = []
                # Start a new dict for this array element
                current_section = section_name
                current_dict: Dict[str, Any] = {}
                # Collect keys until next [[ or [ or end
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith("[[") or next_line.startswith("["):
                        break
                    if not next_line or next_line.startswith("#"):
                        i += 1
                        continue
                    if "=" in next_line:
                        key, val = next_line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        current_dict[key] = _parse_toml_value(val)
                    i += 1
                result[section_name].append(current_dict)
                current_section = None
                continue
        elif line.startswith("["):
            end = line.find("]")
            if end != -1:
                section_name = line[1:end].strip()
                # Handle nested sections like [a.b]
                parts = section_name.split(".")
                current = result
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current_section = section_name
                continue
        # Key = value
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if current_section is not None:
                # Navigate to current section
                parts = current_section.split(".")
                current = result
                for part in parts:
                    if part in current and isinstance(current[part], dict):
                        current = current[part]
                    else:
                        break
                current[key] = _parse_toml_value(val)
            else:
                result[key] = _parse_toml_value(val)
    return result


def _parse_toml_value(val: str) -> Any:
    """Parse a TOML value string into a Python object."""
    val = val.strip()
    # Boolean
    if val == "true":
        return True
    if val == "false":
        return False
    # String
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    # Array
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        # Split by comma, handling nested brackets
        items = []
        depth = 0
        current = ""
        for ch in inner:
            if ch == "[":
                depth += 1
                current += ch
            elif ch == "]":
                depth -= 1
                current += ch
            elif ch == "," and depth == 0:
                items.append(current.strip())
                current = ""
            else:
                current += ch
        if current.strip():
            items.append(current.strip())
        return [_parse_toml_value(item) for item in items]
    # Number
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        pass
    # Fallback: return as string
    return val


def _parse_toml(text: str) -> Dict[str, Any]:
    """Parse TOML text using tomllib if available, otherwise fallback parser."""
    if HAS_TOMLLIB:
        try:
            return tomllib.loads(text)
        except Exception:
            pass
    return _parse_simple_toml(text)


def _merge_context(structure: Dict[str, Any], context_vars: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge context_vars into the structure, with context_vars taking precedence."""
    if not context_vars:
        return structure
    merged = dict(structure)
    for key, value in context_vars.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_context(merged[key], value)
        else:
            merged[key] = value
    return merged


def _flatten_structure(data: Any, delimiter: str = ", ") -> str:
    """Flatten a nested structure into a string using the given delimiter."""
    if isinstance(data, str):
        return data
    if isinstance(data, (int, float, bool)):
        return str(data)
    if isinstance(data, list):
        parts = []
        for item in data:
            flattened = _flatten_structure(item, delimiter)
            if flattened:
                parts.append(flattened)
        return delimiter.join(parts)
    if isinstance(data, dict):
        parts = []
        for key, value in data.items():
            flattened = _flatten_structure(value, delimiter)
            if flattened:
                parts.append(f"{key}: {flattened}")
        return delimiter.join(parts)
    return str(data)


class PSN_TOML_Prompt_Loader:
    """
    Loads and parses TOML content defining hierarchical prompt components.
    Merges optional context_vars into the structure.
    
    Note: Accepts TOML content as a STRING (not a file path) due to
    security restrictions on file access.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "toml_content": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "context_vars": ("DICT", {"default": {}}),
            }
        }
    
    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("prompt_structure",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, toml_content: str, context_vars: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any]]:
        """Parse TOML content and merge context variables."""
        if not toml_content or not toml_content.strip():
            return ({},)
        
        try:
            structure = _parse_toml(toml_content)
        except Exception as e:
            # Return empty dict on parse error
            return ({},)
        
        if context_vars:
            structure = _merge_context(structure, context_vars)
        
        return (structure,)


class PSN_Style_Library_Switcher:
    """
    Selects a specific style block from the loaded prompt structure based on
    style_key. If the key is missing, uses fallback_style. Flattens the
    selected structure into a final prompt string.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_structure": ("DICT", {"default": {}}),
                "style_key": ("STRING", {"default": "default"}),
                "fallback_style": ("STRING", {"default": "default"}),
            },
            "optional": {
                "delimiter": ("STRING", {"default": ", "}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("resolved_prompt",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, prompt_structure: Dict[str, Any], style_key: str, fallback_style: str, delimiter: str = ", ") -> Tuple[str]:
        """Select style block and flatten into prompt string."""
        if not prompt_structure:
            return ("",)
        
        # Try to find the style_key in the structure
        selected = None
        if style_key and style_key in prompt_structure:
            selected = prompt_structure[style_key]
        elif fallback_style and fallback_style in prompt_structure:
            selected = prompt_structure[fallback_style]
        
        if selected is None:
            return ("",)
        
        resolved = _flatten_structure(selected, delimiter)
        return (resolved,)


NODE_CLASS_MAPPINGS = {
    "PSN_TOML_Prompt_Loader": PSN_TOML_Prompt_Loader,
    "PSN_Style_Library_Switcher": PSN_Style_Library_Switcher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TOML_Prompt_Loader": "PSN TOML Prompt Loader",
    "PSN_Style_Library_Switcher": "PSN Style Library Switcher",
}
