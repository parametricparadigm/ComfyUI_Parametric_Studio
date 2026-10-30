"""PSN_Node_Inspector: pure-logic inspector for ComfyUI-style graph JSON.

This module implements a single custom node, PSN_NodeInspector, that takes a
graph JSON string (a mapping of node id -> node definition with an optional
"inputs" mapping of name -> [source_node_id, output_index]) and produces:

  * tree_string : a human-readable indented tree of nodes and their inputs
  * dot_graph   : a Graphviz DOT string representing the node connections

It uses only the Python standard library (json, collections). It performs no
file, network, subprocess, or GPU work. It is safe-by-design: it validates the
input, rejects non-dict payloads, and caps the number of nodes rendered to
avoid unbounded output on very large graphs.
"""

import json
from collections import OrderedDict

CAT = "ParametricStudio/Debug"

# Safety cap on how many nodes we will render, to keep output bounded.
_MAX_NODES = 5000


def _parse_graph(graph_json):
    """Parse and validate the graph JSON.

    Returns (nodes, error). `nodes` is an OrderedDict mapping str(node_id) ->
    node dict, or None on error. `error` is a human-readable string or None.
    """
    if not isinstance(graph_json, str):
        return None, "graph_json must be a string"
    text = graph_json.strip()
    if not text:
        return None, "graph_json is empty"
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        return None, "invalid JSON: %s" % exc
    if not isinstance(data, dict):
        return None, "graph JSON must be an object mapping node id -> node"
    if len(data) > _MAX_NODES:
        return None, "graph too large: %d nodes exceeds cap of %d" % (len(data), _MAX_NODES)
    nodes = OrderedDict()
    for key, value in data.items():
        node_id = str(key)
        if not isinstance(value, dict):
            return None, "node %r must be an object" % node_id
        nodes[node_id] = value
    return nodes, None


def _node_label(node_id, node):
    """Build a short label for a node from its 'type' or 'class_type' field."""
    for field in ("type", "class_type", "title", "name"):
        val = node.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "node"


def _input_refs(node):
    """Return a list of (input_name, source_node_id) for a node's inputs.

    ComfyUI graph format: inputs is a mapping of name -> [source_id, output_index].
    We accept that shape; other shapes are ignored gracefully.
    """
    refs = []
    inputs = node.get("inputs")
    if not isinstance(inputs, dict):
        return refs
    for name, ref in inputs.items():
        if isinstance(ref, list) and len(ref) >= 1:
            src = ref[0]
            if src is not None:
                refs.append((str(name), str(src)))
    return refs


def build_tree_string(nodes):
    """Build an indented text tree of nodes and their input dependencies."""
    lines = []
    lines.append("Node Graph (%d nodes)" % len(nodes))
    for node_id, node in nodes.items():
        label = _node_label(node_id, node)
        lines.append("- [%s] %s" % (node_id, label))
        refs = _input_refs(node)
        if not refs:
            lines.append("    (no inputs)")
        else:
            for name, src in refs:
                lines.append("    - %s <- %s" % (name, src))
    return "\n".join(lines)


def build_dot_graph(nodes):
    """Build a Graphviz DOT string for the node connections.

    Edges point from the source node to the consuming node:
      "source_id" -> "consumer_id" [label="input_name"];
    """
    lines = []
    lines.append("digraph ComfyUI {")
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=box, style=rounded];")
    for node_id, node in nodes.items():
        label = _node_label(node_id, node)
        safe_label = label.replace('"', '\\"')
        lines.append('  "%s" [label="%s"];' % (node_id, safe_label))
    for node_id, node in nodes.items():
        for name, src in _input_refs(node):
            lines.append('  "%s" -> "%s" [label="%s"];' % (src, node_id, name))
    lines.append("}")
    return "\n".join(lines)


class PSN_NodeInspector:
    """Visualizes the node hierarchy and dependencies for debugging.

    Takes a graph JSON string and outputs a text tree and a Graphviz DOT
    string. Pure logic only; no GPU, network, or file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("tree_string", "dot_graph")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json):
        nodes, error = _parse_graph(graph_json)
        if error is not None:
            tree = "ERROR: %s" % error
            dot = "digraph ComfyUI {\n  label=\"ERROR: %s\";\n}" % error.replace('"', '\\"')
            return (tree, dot)
        tree = build_tree_string(nodes)
        dot = build_dot_graph(nodes)
        return (tree, dot)


NODE_CLASS_MAPPINGS = {
    "PSN_NodeInspector": PSN_NodeInspector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NodeInspector": "PSN Node Inspector",
}
