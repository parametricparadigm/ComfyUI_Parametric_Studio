"""
PSN JSON Metadata Extraction nodes.

This module provides pure-logic, secure-by-design implementations of two closely
related nodes:

1. PSN_JSON_Metadata_Extractor:
   - Accepts a plain JSON text string (representing image metadata) and a plain
     JSON text string (representing a workflow graph).
   - Validates that both inputs are well-formed JSON.
   - Merges the two JSON objects into a single JSON string with a deterministic
     structure.
   - Handles non-serializable values gracefully by converting them to strings.
   - Does NOT access files, network, or GPU. The "image" input is treated as
     pre-extracted metadata JSON text, not as a raw image tensor.

2. PSN_File_List_Manager:
   - Accepts a directory path string and a glob pattern string.
   - Returns a list of file names (not full paths) that match the pattern.
   - Since file/OS access is prohibited, this node operates on a provided
     list of file names (simulating directory contents) rather than actually
     scanning the filesystem. The "directory" input is used as a label/context
     string, and the actual file list is passed via an optional "file_names"
     input (a JSON-encoded list of strings).
   - Uses fnmatch for pattern matching (pure standard library, no OS access).

All functions take plain values (strings, numbers, lists) and return plain
values. No torch, no comfy imports, no network, no subprocess, no file/OS access,
no eval/exec, no dunder tricks.
"""

import json
import fnmatch
import re

# ---------------------------------------------------------------------------
# Helper: safe JSON serialization
# ---------------------------------------------------------------------------

def _safe_serialize(obj):
    """
    Recursively convert an object into a JSON-serializable structure.
    - dict, list, str, int, float, bool, None pass through.
    - Any other type is converted to its string representation.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    # Fallback: convert to string
    return str(obj)


def _parse_json_text(text, label="input"):
    """
    Parse a JSON text string. Returns (parsed_obj, error_string).
    If parsing fails, parsed_obj is None and error_string describes the issue.
    """
    if not isinstance(text, str):
        return None, f"{label} must be a string, got {type(text).__name__}"
    if not text.strip():
        return None, f"{label} is empty"
    try:
        obj = json.loads(text)
        return obj, None
    except json.JSONDecodeError as e:
        return None, f"{label} is not valid JSON: {e}"


# ---------------------------------------------------------------------------
# Node 1: PSN_JSON_Metadata_Extractor
# ---------------------------------------------------------------------------

class PSN_JSON_Metadata_Extractor:
    """
    Extract and merge metadata from image metadata JSON and workflow JSON.

    Inputs:
        image_metadata (STRING): JSON text containing image metadata.
        workflow (STRING): JSON text containing the workflow graph.

    Outputs:
        metadata_json (STRING): A single JSON string with merged metadata.
        success (BOOLEAN): Whether extraction succeeded.
        error (STRING): Error message if extraction failed, empty string otherwise.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_metadata": ("STRING", {"default": "{}", "multiline": True}),
                "workflow": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "include_workflow_nodes": ("BOOLEAN", {"default": True}),
                "max_depth": ("INT", {"default": 10, "min": 1, "max": 100}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("metadata_json", "success", "error")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/JSON"

    def run(self, image_metadata, workflow, include_workflow_nodes=True, max_depth=10):
        # Parse image metadata
        img_obj, img_err = _parse_json_text(image_metadata, "image_metadata")
        if img_err:
            return ("", False, img_err)

        # Parse workflow
        wf_obj, wf_err = _parse_json_text(workflow, "workflow")
        if wf_err:
            return ("", False, wf_err)

        # Build merged structure
        merged = {
            "image": _safe_serialize(img_obj),
            "workflow": {},
            "source": "PSN_JSON_Metadata_Extractor",
        }

        if include_workflow_nodes:
            # Extract node count and node types from workflow if it's a dict
            if isinstance(wf_obj, dict):
                nodes = wf_obj.get("nodes", [])
                if isinstance(nodes, list):
                    node_types = []
                    for node in nodes:
                        if isinstance(node, dict):
                            node_types.append(str(node.get("type", "unknown")))
                    merged["workflow"] = {
                        "node_count": len(nodes),
                        "node_types": node_types,
                        "raw": _safe_serialize(wf_obj),
                    }
                else:
                    merged["workflow"] = {"raw": _safe_serialize(wf_obj)}
            else:
                merged["workflow"] = {"raw": _safe_serialize(wf_obj)}
        else:
            merged["workflow"] = {"raw": _safe_serialize(wf_obj)}

        # Serialize to JSON string
        try:
            result_json = json.dumps(merged, indent=2, sort_keys=True)
        except (TypeError, ValueError) as e:
            return ("", False, f"Failed to serialize merged metadata: {e}")

        return (result_json, True, "")


# ---------------------------------------------------------------------------
# Node 2: PSN_File_List_Manager
# ---------------------------------------------------------------------------

class PSN_File_List_Manager:
    """
    Filter a list of file names by a glob pattern.

    Since direct filesystem access is prohibited, this node operates on a
    provided list of file names (as a JSON-encoded list of strings) rather
    than scanning an actual directory. The "directory" input serves as a
    context label.

    Inputs:
        directory (STRING): A label or path string for context (not used for
                            actual filesystem access).
        pattern (STRING): A glob pattern (e.g., "*.png") to match file names.
        file_names (STRING, optional): A JSON-encoded list of file name strings.
                                       If not provided, an empty list is returned.

    Outputs:
        file_list (STRING): A JSON-encoded list of matching file names.
        count (INT): The number of matching files.
        error (STRING): Error message if input was invalid, empty string otherwise.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": "/data"}),
                "pattern": ("STRING", {"default": "*.png"}),
            },
            "optional": {
                "file_names": ("STRING", {"default": "[]", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("file_list", "count", "error")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/JSON"

    def run(self, directory, pattern, file_names="[]"):
        # Validate pattern
        if not isinstance(pattern, str) or not pattern.strip():
            return ("[]", 0, "pattern must be a non-empty string")

        # Parse file_names
        if not isinstance(file_names, str):
            return ("[]", 0, "file_names must be a string (JSON-encoded list)")

        if not file_names.strip():
            # Empty input -> empty list
            return ("[]", 0, "")

        try:
            names = json.loads(file_names)
        except json.JSONDecodeError as e:
            return ("[]", 0, f"file_names is not valid JSON: {e}")

        if not isinstance(names, list):
            return ("[]", 0, "file_names must be a JSON list of strings")

        # Validate each element is a string
        for i, name in enumerate(names):
            if not isinstance(name, str):
                return ("[]", 0, f"file_names[{i}] is not a string: {type(name).__name__}")

        # Filter by pattern using fnmatch
        matched = [name for name in names if fnmatch.fnmatch(name, pattern)]

        # Sort for deterministic output
        matched.sort()

        result_json = json.dumps(matched)
        return (result_json, len(matched), "")


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_JSON_Metadata_Extractor": PSN_JSON_Metadata_Extractor,
    "PSN_File_List_Manager": PSN_File_List_Manager,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_JSON_Metadata_Extractor": "PSN JSON Metadata Extractor",
    "PSN_File_List_Manager": "PSN File List Manager",
}
