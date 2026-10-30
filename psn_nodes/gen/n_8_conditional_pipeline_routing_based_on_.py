"""Conditional pipeline routing based on input type.

This module provides two closely related pure-logic nodes:

1. PSN_Type_Inspector: inspects a plain Python value and reports a
   normalized type label (IMAGE, VIDEO, TEXT, NUMBER, LIST, DICT,
   BOOLEAN, NONE, UNKNOWN) plus a shape list (empty for scalars).

2. PSN_Pipeline_Router: looks up the type label in a JSON route map
   and returns the routed payload (the original data, or a fallback
   when the type is not mapped) together with the chosen route id.

No torch, no ComfyUI imports, no network, no file/OS access. All
functions take plain values (numbers, strings, JSON text) and return
plain values.
"""

import json

CAT = "ParametricStudio/ConditionalRouting"

# Canonical type labels used by the inspector and the router.
TYPE_IMAGE = "IMAGE"
TYPE_VIDEO = "VIDEO"
TYPE_TEXT = "TEXT"
TYPE_NUMBER = "NUMBER"
TYPE_LIST = "LIST"
TYPE_DICT = "DICT"
TYPE_BOOLEAN = "BOOLEAN"
TYPE_NONE = "NONE"
TYPE_UNKNOWN = "UNKNOWN"

# Route ids used by the router.
ROUTE_DEFAULT = "default"
ROUTE_FALLBACK = "fallback"

# Allowed keys in a route map.
ALLOWED_ROUTE_KEYS = (
    TYPE_IMAGE,
    TYPE_VIDEO,
    TYPE_TEXT,
    TYPE_NUMBER,
    TYPE_LIST,
    TYPE_DICT,
    TYPE_BOOLEAN,
    TYPE_NONE,
    "default",
)


def psn_inspect_type(data):
    """Return (type_label, shape) for a plain Python value.

    shape is a list of ints describing the outermost dimensions when
    the value is a list/tuple; empty list for scalars.
    """
    if data is None:
        return (TYPE_NONE, [])
    if isinstance(data, bool):
        return (TYPE_BOOLEAN, [])
    if isinstance(data, (int, float)):
        return (TYPE_NUMBER, [])
    if isinstance(data, str):
        return (TYPE_TEXT, [])
    if isinstance(data, (list, tuple)):
        # Heuristic: a list of dicts is treated as VIDEO (frames),
        # a list of numbers is treated as IMAGE (single frame pixels),
        # otherwise a generic LIST.
        if len(data) > 0:
            first = data[0]
            if isinstance(first, dict):
                return (TYPE_VIDEO, [len(data)])
            if isinstance(first, (int, float)):
                return (TYPE_IMAGE, [len(data)])
        return (TYPE_LIST, [len(data)])
    if isinstance(data, dict):
        return (TYPE_DICT, [len(data)])
    return (TYPE_UNKNOWN, [])


def psn_validate_route_map(route_map_text):
    """Parse and validate a JSON route map.

    Returns (ok, route_dict, error_message).
    route_dict maps type labels (or 'default') to a route id string.
    """
    if not isinstance(route_map_text, str):
        return (False, {}, "route_map must be a JSON string")
    try:
        parsed = json.loads(route_map_text)
    except (json.JSONDecodeError, ValueError) as exc:
        return (False, {}, "invalid JSON: %s" % exc)
    if not isinstance(parsed, dict):
        return (False, {}, "route_map must be a JSON object")
    for key, value in parsed.items():
        if key not in ALLOWED_ROUTE_KEYS:
            return (False, {}, "unknown route key: %s" % key)
        if not isinstance(value, str):
            return (False, {}, "route value for %s must be a string" % key)
    return (True, parsed, "")


def psn_route(data_type, data, route_map_text):
    """Route data based on its type label.

    Returns (routed_data, route_id, error_message).
    error_message is empty on success.
    """
    ok, route_dict, err = psn_validate_route_map(route_map_text)
    if not ok:
        return (None, ROUTE_FALLBACK, err)
    if data_type in route_dict:
        return (data, route_dict[data_type], "")
    if ROUTE_DEFAULT in route_dict:
        return (data, route_dict[ROUTE_DEFAULT], "")
    return (data, ROUTE_FALLBACK, "")


class PSN_Type_Inspector:
    """Inspect a plain Python value and report its type label and shape."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": ("ANY",),
            }
        }

    RETURN_TYPES = ("STRING", "LIST")
    RETURN_NAMES = ("data_type", "shape")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, data):
        label, shape = psn_inspect_type(data)
        return (label, shape)


class PSN_Pipeline_Router:
    """Route data to a pipeline based on its type label and a JSON route map."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data_type": ("STRING", {"default": TYPE_UNKNOWN}),
                "data": ("ANY",),
                "route_map": ("STRING", {"default": "{}"}),
            }
        }

    RETURN_TYPES = ("ANY", "STRING")
    RETURN_NAMES = ("routed_data", "route_id")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, data_type, data, route_map):
        routed, route_id, _err = psn_route(data_type, data, route_map)
        return (routed, route_id)


NODE_CLASS_MAPPINGS = {
    "PSN_Type_Inspector": PSN_Type_Inspector,
    "PSN_Pipeline_Router": PSN_Pipeline_Router,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Type_Inspector": "PSN Type Inspector",
    "PSN_Pipeline_Router": "PSN Pipeline Router",
}
