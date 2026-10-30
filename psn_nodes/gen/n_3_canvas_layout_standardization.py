"""Canvas Layout Standardization (pure-logic, secure-by-design).

This module implements the *logic* of the "Canvas Layout Standardization"
spec as plain, dependency-free Python.  It does NOT talk to ComfyUI, the
frontend, a GPU, the network, or the file system.  Instead it:

  * validates inputs against strict allow-lists,
  * builds a deterministic, JSON-serializable ``layout_config`` payload that a
    frontend *could* apply (grouping, theme, wireless routing), and
  * models a "wireless" logical connection that passes data from a source to a
    target without any visual wire.

All public entry points are ordinary functions / node wrappers that take plain
values (strings, numbers, booleans, lists, dicts) and return plain values.
No sockets, no subprocess, no file/OS access, no eval/exec, no dunder tricks.
"""

import json

# ---------------------------------------------------------------------------
# Allow-lists (single source of truth for validation)
# ---------------------------------------------------------------------------

THEMES = ("Dark", "Light", "Studio")
GROUPING_RULES = ("By Type", "By Function")
# Canonical node "types" used when grouping "By Type".
NODE_TYPES = ("Model", "Conditioning", "Latent", "Sampler", "Decode", "Other")
# Canonical node "functions" used when grouping "By Function".
NODE_FUNCTIONS = ("Input", "Process", "Output", "Other")

# A node id must be a non-empty string of letters/digits/underscore/dash,
# starting with a letter.  This keeps ids safe and predictable.
_ID_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


# ---------------------------------------------------------------------------
# Small, pure helpers
# ---------------------------------------------------------------------------

def _is_valid_id(value):
    """Return True if ``value`` is a well-formed node/graph id string."""
    if not isinstance(value, str):
        return False
    if not value:
        return False
    if not value[0].isalpha():
        return False
    return all(ch in _ID_ALLOWED for ch in value)


def _coerce_nodes(node_list):
    """Normalize a raw node list into a list of dicts with id/type/function.

    Accepts either:
      * a list of dicts with keys ``id`` (and optional ``type``/``function``), or
      * a list of plain strings (treated as ids with type/function "Other").

    Returns a list of normalized dicts.  Raises ``ValueError`` on bad ids.
    """
    if node_list is None:
        return []
    if not isinstance(node_list, (list, tuple)):
        raise ValueError("node_list must be a list of node ids or node dicts")

    normalized = []
    for index, item in enumerate(node_list):
        if isinstance(item, str):
            node_id = item
            node_type = "Other"
            node_function = "Other"
        elif isinstance(item, dict):
            node_id = item.get("id")
            node_type = item.get("type", "Other")
            node_function = item.get("function", "Other")
        else:
            raise ValueError(
                "node_list entries must be strings or dicts, got %r" % (type(item),)
            )

        if not _is_valid_id(node_id):
            raise ValueError("invalid node id at index %d: %r" % (index, node_id))

        if node_type not in NODE_TYPES:
            node_type = "Other"
        if node_function not in NODE_FUNCTIONS:
            node_function = "Other"

        normalized.append(
            {"id": node_id, "type": node_type, "function": node_function}
        )
    return normalized


def _group_nodes(nodes, rule):
    """Group normalized nodes by the given rule.

    Returns a dict mapping group-name -> list of node ids (stable order).
    """
    if rule == "By Type":
        key = "type"
    elif rule == "By Function":
        key = "function"
    else:
        raise ValueError("unknown grouping rule: %r" % (rule,))

    groups = {}
    for node in nodes:
        groups.setdefault(node[key], []).append(node["id"])
    return groups


def _build_layout_config(graph_id, theme, grouping_rule, nodes):
    """Assemble the deterministic layout configuration payload."""
    if not _is_valid_id(graph_id):
        raise ValueError("invalid graph_id: %r" % (graph_id,))
    if theme not in THEMES:
        raise ValueError("unknown theme: %r" % (theme,))
    if grouping_rule not in GROUPING_RULES:
        raise ValueError("unknown grouping_rule: %r" % (grouping_rule,))

    normalized = _coerce_nodes(nodes)
    groups = _group_nodes(normalized, grouping_rule)

    # Deterministic ordering of group keys for stable output.
    ordered_groups = {key: groups[key] for key in sorted(groups)}

    config = {
        "graph_id": graph_id,
        "theme": theme,
        "grouping_rule": grouping_rule,
        "wireless_routing": True,
        "node_count": len(normalized),
        "groups": ordered_groups,
        "commands": [
            {"op": "apply_theme", "theme": theme},
            {"op": "group_nodes", "rule": grouping_rule, "groups": ordered_groups},
            {"op": "enable_wireless_routing", "enabled": True},
        ],
    }
    return config


def _route_wireless(source_node_id, target_node_id, wireless, payload=None):
    """Model a (possibly wireless) logical connection.

    Returns a dict describing the routed data.  When ``wireless`` is True the
    connection is logical-only (no visual wire); when False it is a normal
    wired connection.  Data is passed through unchanged.
    """
    if not _is_valid_id(source_node_id):
        raise ValueError("invalid source_node_id: %r" % (source_node_id,))
    if not _is_valid_id(target_node_id):
        raise ValueError("invalid target_node_id: %r" % (target_node_id,))
    if not isinstance(wireless, bool):
        raise ValueError("wireless must be a boolean")

    return {
        "source": source_node_id,
        "target": target_node_id,
        "wireless": wireless,
        "visual_wire": not wireless,
        "data": payload,
    }


# ---------------------------------------------------------------------------
# ComfyUI-style node wrappers
# ---------------------------------------------------------------------------

class PSN_LayoutEnforcer:
    """Generate a deterministic layout configuration for a graph.

    Pure logic only: validates inputs and returns a JSON-serializable config
    dict.  It does not rearrange anything itself; the returned payload is what
    a frontend would apply.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_id": ("STRING", {"default": "graph_1"}),
                "theme": (list(THEMES),),
                "grouping_rule": (list(GROUPING_RULES),),
            },
            "optional": {
                # A list of node ids (strings) or node dicts.
                "nodes": ("LIST", {"default": []}),
            },
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("layout_config",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Canvas"

    def run(self, graph_id, theme, grouping_rule, nodes=None):
        config = _build_layout_config(graph_id, theme, grouping_rule, nodes)
        return (config,)


class PSN_WirelessRouter:
    """Pass data from a source node to a target node, optionally wirelessly.

    Pure logic only: validates ids and returns a routed-data dict.  No actual
    connection is created; this models the logical data flow.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_node_id": ("STRING", {"default": "node_a"}),
                "target_node_id": ("STRING", {"default": "node_b"}),
                "wireless": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "payload": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("routed_data",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Canvas"

    def run(self, source_node_id, target_node_id, wireless, payload=None):
        routed = _route_wireless(
            source_node_id, target_node_id, wireless, payload
        )
        return (routed,)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_LayoutEnforcer": PSN_LayoutEnforcer,
    "PSN_WirelessRouter": PSN_WirelessRouter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LayoutEnforcer": "PSN Layout Enforcer",
    "PSN_WirelessRouter": "PSN Wireless Router",
}
