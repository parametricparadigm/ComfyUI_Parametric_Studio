"""Interactive execution path selection and routing.

This module provides pure-logic nodes for choosing between different
execution paths (e.g. draft vs. high-quality) within a single workflow.
It does NOT execute any GPU/torch/ComfyUI internals, open sockets, or
perform file/network I/O. It only validates inputs, selects a path, and
routes a plain value to the chosen path.

Nodes:
  - PSN_PathSelector: validates a path name against an allow-list of
    available paths and outputs the selected path name.
  - PSN_PathRouter: routes a plain value to the node ID associated with
    the selected path via a path-to-node-ID mapping.
"""

import json

CAT = "ParametricStudio/Interactive"


def _parse_options(options):
    """Parse the options input into a list of non-empty string path names.

    Accepts either a Python list/tuple of strings, or a JSON text string
    containing a list of strings. Returns (list_of_names, error_message).
    On success error_message is None; on failure the list is empty.
    """
    if options is None:
        return [], "options must be a non-empty list of path names"

    if isinstance(options, str):
        text = options.strip()
        if not text:
            return [], "options string is empty"
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return [], "options string is not valid JSON"
        if not isinstance(parsed, list):
            return [], "options JSON must be a list"
        options = parsed

    if not isinstance(options, (list, tuple)):
        return [], "options must be a list of path names"

    if len(options) == 0:
        return [], "options list is empty"

    names = []
    for item in options:
        if not isinstance(item, str):
            return [], "each option must be a string"
        name = item.strip()
        if not name:
            return [], "option names must be non-empty"
        names.append(name)

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for name in names:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique, None


def _parse_path_map(path_map):
    """Parse the path_map input into a dict of {path_name: node_id}.

    Accepts either a Python dict, or a JSON text string containing an
    object. Returns (dict, error_message). On success error_message is
    None; on failure the dict is empty.
    """
    if path_map is None:
        return {}, "path_map must be a non-empty mapping"

    if isinstance(path_map, str):
        text = path_map.strip()
        if not text:
            return {}, "path_map string is empty"
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return {}, "path_map string is not valid JSON"
        if not isinstance(parsed, dict):
            return {}, "path_map JSON must be an object"
        path_map = parsed

    if not isinstance(path_map, dict):
        return {}, "path_map must be a mapping of path names to node IDs"

    if len(path_map) == 0:
        return {}, "path_map is empty"

    clean = {}
    for key, value in path_map.items():
        if not isinstance(key, str) or not key.strip():
            return {}, "path_map keys must be non-empty strings"
        if not isinstance(value, str) or not value.strip():
            return {}, "path_map values must be non-empty strings"
        clean[key.strip()] = value.strip()
    return clean, None


class PSN_PathSelector:
    """Button-based selection of an execution path from an allow-list.

    Validates that `path_name` is one of the available `options` and
    outputs the selected path name. If the name is not in the list, the
    first option is used as a safe default and a warning is reported.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path_name": ("STRING", {"default": "", "multiline": False}),
                "options": ("STRING", {"default": '["Draft", "High-Quality"]', "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("selected_path", "is_valid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, path_name, options):
        names, err = _parse_options(options)
        if err is not None:
            return ("", False, err)

        if not isinstance(path_name, str):
            path_name = str(path_name)
        chosen = path_name.strip()

        if chosen in names:
            return (chosen, True, "selected path is in the allow-list")

        # Fall back to the first option with a warning.
        fallback = names[0]
        return (fallback, False,
                "path_name not in options; defaulted to first option '%s'" % fallback)


class PSN_PathRouter:
    """Routes a plain value to the node ID for the selected path.

    Looks up `selected_path` in `path_map` and outputs the associated
    node ID along with the routed value. Only the selected path is
    routed; no other path is touched.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "selected_path": ("STRING", {"default": "", "multiline": False}),
                "path_map": ("STRING", {"default": '{"Draft": "node_draft", "High-Quality": "node_hq"}', "multiline": True}),
            },
            "optional": {
                "value": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("routed_node_id", "routed_data", "routed", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, selected_path, path_map, value=""):
        mapping, err = _parse_path_map(path_map)
        if err is not None:
            return ("", "", False, err)

        if not isinstance(selected_path, str):
            selected_path = str(selected_path)
        chosen = selected_path.strip()

        if not chosen:
            return ("", "", False, "selected_path is empty")

        if chosen not in mapping:
            return ("", "", False,
                    "selected_path '%s' not found in path_map" % chosen)

        node_id = mapping[chosen]
        routed_data = value if isinstance(value, str) else str(value)
        return (node_id, routed_data, True,
                "routed to node '%s' for path '%s'" % (node_id, chosen))


NODE_CLASS_MAPPINGS = {
    "PSN_PathSelector": PSN_PathSelector,
    "PSN_PathRouter": PSN_PathRouter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PathSelector": "PSN Path Selector",
    "PSN_PathRouter": "PSN Path Router",
}
