"""
PSN Dynamic Pipeline Parameter Injection

This module provides pure-logic nodes for dynamic parameter injection into
ComfyUI API graphs. It implements:

1. PSN_JSON_Config_Loader: Parses JSON text (or a JSON string) and extracts
   values via a dot-separated key path. No file I/O is performed; the caller
   must supply the JSON content as a string.

2. PSN_Param_Injector: Takes a graph dictionary (API prompt structure) and
   overwrites a specific parameter on a target node with a provided value.

Security notes:
- No file system access, no network, no subprocess, no eval/exec.
- JSON parsing uses the standard library json module only.
- Key path traversal is limited to dot-separated keys within the provided dict.
- The injector only modifies the in-memory dict; it never writes to disk.
"""

import json
import copy

CAT = "ParametricStudio/Injection"


def _resolve_key_path(data, key_path):
    """
    Resolve a dot-separated key path within a nested dictionary.
    Returns (found: bool, value, reason: str).
    """
    if not key_path or not key_path.strip():
        return (True, data, "no key_path provided, returning full dict")

    parts = key_path.strip().split(".")
    current = data
    for i, part in enumerate(parts):
        if not isinstance(current, dict):
            return (False, None, "key_path segment '{}' at depth {} is not a dict".format(part, i))
        if part not in current:
            return (False, None, "key '{}' not found at depth {}".format(part, i))
        current = current[part]
    return (True, current, "resolved key_path '{}'".format(key_path))


class PSN_JSON_Config_Loader:
    """
    Parses a JSON string into a Python dictionary and optionally extracts
    a nested value via a dot-separated key path.

    Inputs:
        json_text (STRING): The JSON content as a string.
        key_path (STRING, optional): Dot-separated path to a nested value,
                                     e.g. "model.sdxl.steps".

    Outputs:
        config_dict (DICT): The parsed JSON dict, or the extracted value
                            if key_path is provided and valid.
        success (BOOLEAN): Whether parsing and extraction succeeded.
        reason (STRING): Human-readable explanation of success or failure.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_text": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "key_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("DICT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("config_dict", "success", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, json_text, key_path=""):
        if not isinstance(json_text, str):
            return ({}, False, "json_text must be a string")

        if not json_text.strip():
            return ({}, False, "json_text is empty")

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as e:
            return ({}, False, "JSON parse error: {}".format(str(e)))

        if not isinstance(parsed, dict):
            return ({}, False, "Top-level JSON value is not a dict (got {})".format(type(parsed).__name__))

        if key_path and key_path.strip():
            found, value, reason = _resolve_key_path(parsed, key_path)
            if not found:
                return ({}, False, reason)
            # Return the extracted value wrapped in a dict for consistent output type
            return ({}, True, reason) if not isinstance(value, dict) else (value, True, reason)

        return (parsed, True, "parsed full JSON dict")


class PSN_Param_Injector:
    """
    Injects a value into a specific parameter of a target node within a
    ComfyUI API graph dictionary.

    The graph is expected to be a dict mapping node IDs (strings) to node
    dicts, where each node dict has an "inputs" sub-dict.

    Inputs:
        graph (DICT): The current API graph structure.
        target_node_id (STRING): The ID of the node to modify.
        param_name (STRING): The name of the input parameter to overwrite.
        value (ANY): The value to inject.

    Outputs:
        updated_graph (DICT): A deep copy of the graph with the parameter set.
        success (BOOLEAN): Whether the injection succeeded.
        reason (STRING): Human-readable explanation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph": ("DICT",),
                "target_node_id": ("STRING", {"default": ""}),
                "param_name": ("STRING", {"default": ""}),
                "value": ("ANY",),
            },
        }

    RETURN_TYPES = ("DICT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("updated_graph", "success", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph, target_node_id, param_name, value):
        if not isinstance(graph, dict):
            return ({}, False, "graph must be a dict")

        if not target_node_id or not target_node_id.strip():
            return (copy.deepcopy(graph), False, "target_node_id is empty")

        if not param_name or not param_name.strip():
            return (copy.deepcopy(graph), False, "param_name is empty")

        node_id = target_node_id.strip()
        param = param_name.strip()

        if node_id not in graph:
            return (copy.deepcopy(graph), False, "target node '{}' not found in graph".format(node_id))

        node = graph[node_id]
        if not isinstance(node, dict):
            return (copy.deepcopy(graph), False, "node '{}' is not a dict".format(node_id))

        if "inputs" not in node or not isinstance(node["inputs"], dict):
            return (copy.deepcopy(graph), False, "node '{}' has no 'inputs' dict".format(node_id))

        updated = copy.deepcopy(graph)
        updated[node_id]["inputs"][param] = value
        return (updated, True, "injected '{}' into node '{}'".format(param, node_id))


NODE_CLASS_MAPPINGS = {
    "PSN_JSON_Config_Loader": PSN_JSON_Config_Loader,
    "PSN_Param_Injector": PSN_Param_Injector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_JSON_Config_Loader": "PSN JSON Config Loader",
    "PSN_Param_Injector": "PSN Param Injector",
}
