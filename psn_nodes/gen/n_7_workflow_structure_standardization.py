"""ParametricStudio - Workflow Structure Standardization.

Two pre-execution nodes that operate on ComfyUI API-format graph JSON strings:

* PSN_Graph_Standardizer - rewrites node titles into a strict
  Loader / Controller / Sampler naming convention (LDR_, CTL_, SMP_) and
  emits a validation report about connectivity.
* PSN_Node_Inspector - renders a text tree and a Graphviz DOT string of the
  node dependency graph.

Only the Python standard library is used (json, collections).  No tensors are
involved: both nodes are pure text/logic helpers that run before execution.
"""

import json
from collections import defaultdict, deque

CAT = "ParametricStudio/Workflow"

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Heuristic classification of a node type into one of the three buckets.
# Order matters: first matching rule wins.
_LOADER_HINTS = (
    "load", "loader", "loadimage", "loadvideo", "load3d", "loadaudio",
    "loadclip", "loadstyle", "loadlora", "loadcheckpoint", "loadvae",
    "loadclipvision", "loadstylemodel", "loadunet", "loaddiffusionmodel",
    "loadlatent", "loadmask", "loadreference", "loadpreset", "load",
)
_SAMPLER_HINTS = (
    "sampler", "kSampler", "k_sampler", "basic", "dpmpp", "euler",
    "heun", "uni_pc", "res_multistep", "sampler_custom", "sampler",
)


def _classify(node_type):
    """Return 'LDR', 'CTL' or 'SMP' for a ComfyUI node type string."""
    t = (node_type or "").lower()
    for hint in _LOADER_HINTS:
        if hint in t:
            return "LDR"
    for hint in _SAMPLER_HINTS:
        if hint in t:
            return "SMP"
    return "CTL"


def _parse_graph(graph_json):
    """Parse an API-format graph JSON string.

    Accepts either a full API payload (``{"prompt": {...}, ...}``) or a bare
    node map ``{node_id: node_dict, ...}``.  Returns ``(nodes, errors)`` where
    ``nodes`` is a dict ``{node_id: node_dict}`` (never the input object) and
    ``errors`` is a list of human readable strings.
    """
    errors = []
    if not isinstance(graph_json, str):
        return {}, ["graph_json must be a string"]
    try:
        data = json.loads(graph_json)
    except json.JSONDecodeError as exc:
        return {}, ["invalid JSON: %s" % exc]
    if not isinstance(data, dict):
        return {}, ["top-level JSON must be an object"]
    if "prompt" in data and isinstance(data["prompt"], dict):
        raw = data["prompt"]
    else:
        raw = data
    nodes = {}
    for nid, node in raw.items():
        if not isinstance(node, dict):
            errors.append("node %r is not an object" % nid)
            continue
        if "class_type" not in node:
            errors.append("node %r missing class_type" % nid)
            continue
        nodes[str(nid)] = dict(node)
    return nodes, errors


def _edges(nodes):
    """Return a list of (src_id, dst_id) edges derived from input links.

    An input link is ``[src_id, src_slot, dst_slot]`` (or a plain int meaning
    a constant).  We only follow string ids that actually exist in the graph.
    """
    edges = []
    for nid, node in nodes.items():
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        for _name, link in inputs.items():
            if isinstance(link, (list, tuple)) and len(link) >= 2 and isinstance(link[0], str):
                if link[0] in nodes:
                    edges.append((link[0], nid))
    return edges


def _topo_order(nodes, edges):
    """Kahn topological sort; returns (order, cycle_nodes)."""
    indeg = {nid: 0 for nid in nodes}
    adj = defaultdict(list)
    for src, dst in edges:
        adj[src].append(dst)
        indeg[dst] = indeg.get(dst, 0) + 1
    queue = deque(sorted(nid for nid, d in indeg.items() if d == 0))
    order = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for nxt in sorted(adj.get(nid, [])):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    cycle = sorted(set(nodes) - set(order))
    return order, cycle


# ---------------------------------------------------------------------------
# Node 1: PSN_Graph_Standardizer
# ---------------------------------------------------------------------------

class PSN_Graph_Standardizer:
    """Rewrite an API graph into the Loader-Controller-Sampler naming pattern.

    Every node title becomes ``<PREFIX>_<original_title>`` where PREFIX is
    LDR / CTL / SMP based on the node's class_type.  Node ids are preserved
    so existing links keep working; only titles and the report change.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("standardized_graph", "validation_report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json):
        nodes, errors = _parse_graph(graph_json)
        if not nodes and errors:
            report = "FAILED: " + "; ".join(errors)
            return (graph_json if isinstance(graph_json, str) else "", report)

        edges = _edges(nodes)
        order, cycle = _topo_order(nodes, edges)

        # Build the standardized graph: same ids, prefixed titles.
        out_nodes = {}
        renamed = []
        for nid in order:
            node = dict(nodes[nid])
            ntype = node.get("class_type", "")
            prefix = _classify(ntype)
            old_title = node.get("title") or ntype
            new_title = "%s_%s" % (prefix, old_title)
            node["title"] = new_title
            out_nodes[nid] = node
            renamed.append((nid, old_title, new_title))
        # Any nodes stuck in a cycle are still emitted (after the ordered ones)
        for nid in cycle:
            node = dict(nodes[nid])
            ntype = node.get("class_type", "")
            prefix = _classify(ntype)
            old_title = node.get("title") or ntype
            node["title"] = "%s_%s" % (prefix, old_title)
            out_nodes[nid] = node
            renamed.append((nid, old_title, node["title"]))

        standardized = json.dumps({"prompt": out_nodes}, indent=2, sort_keys=True)

        # Validation report
        lines = []
        lines.append("nodes: %d" % len(nodes))
        lines.append("edges: %d" % len(edges))
        lines.append("order: %s" % (" -> ".join(order) if order else "(empty)"))
        if cycle:
            lines.append("CYCLE detected in: %s" % ", ".join(cycle))
        else:
            lines.append("acyclic: yes")
        # dangling inputs: link to a node id that does not exist
        dangling = []
        for nid, node in nodes.items():
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for name, link in inputs.items():
                if isinstance(link, (list, tuple)) and len(link) >= 2 and isinstance(link[0], str):
                    if link[0] not in nodes:
                        dangling.append("%s.%s -> %s" % (nid, name, link[0]))
        if dangling:
            lines.append("dangling inputs: %s" % "; ".join(dangling))
        else:
            lines.append("dangling inputs: none")
        if errors:
            lines.append("parse warnings: %s" % "; ".join(errors))
        lines.append("renames:")
        for nid, old, new in renamed:
            lines.append("  %s: %s -> %s" % (nid, old, new))
        report = "\n".join(lines)
        return (standardized, report)


# ---------------------------------------------------------------------------
# Node 2: PSN_Node_Inspector
# ---------------------------------------------------------------------------

class PSN_Node_Inspector:
    """Render a text tree and a Graphviz DOT string of the node graph."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("tree_string", "dot_graph")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json):
        nodes, errors = _parse_graph(graph_json)
        if not nodes:
            msg = "empty graph" if not errors else "; ".join(errors)
            return ("# %s" % msg, "digraph G { }\n")

        edges = _edges(nodes)
        order, cycle = _topo_order(nodes, edges)
        if cycle:
            order = order + cycle

        # ---- text tree ----------------------------------------------------
        children = defaultdict(list)
        for src, dst in edges:
            children[src].append(dst)
        for k in children:
            children[k].sort()
        roots = [nid for nid in order if not any(dst == nid for _s, dst in edges)]
        if not roots:
            roots = [order[0]]

        lines = []
        seen = set()

        def _walk(nid, depth, path):
            if nid in seen or nid in path:
                return
            seen.add(nid)
            node = nodes[nid]
            label = "%s [%s]" % (node.get("title") or node.get("class_type", "?"), node.get("class_type", "?"))
            lines.append("  " * depth + ("- " if depth else "* ") + label)
            for child in children.get(nid, []):
                _walk(child, depth + 1, path | {nid})

        for r in roots:
            _walk(r, 0, set())
        # any node not reached (e.g. inside a cycle) gets appended
        for nid in order:
            if nid not in seen:
                node = nodes[nid]
                lines.append("* %s [%s] (unreached)" % (node.get("title") or node.get("class_type", "?"), node.get("class_type", "?")))
        tree = "\n".join(lines)

        # ---- DOT ----------------------------------------------------------
        dot = ["digraph G {"]
        dot.append('  rankdir=LR;')
        for nid in order:
            node = nodes[nid]
            title = (node.get("title") or node.get("class_type", "?")).replace('"', "'")
            ctype = node.get("class_type", "?").replace('"', "'")
            dot.append('  "%s" [label="%s\\n%s" shape=box];' % (nid, title, ctype))
        for src, dst in edges:
            dot.append('  "%s" -> "%s";' % (src, dst))
        dot.append("}")
        dot_str = "\n".join(dot)
        return (tree, dot_str)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Graph_Standardizer": PSN_Graph_Standardizer,
    "PSN_Node_Inspector": PSN_Node_Inspector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Graph_Standardizer": "PSN Graph Standardizer",
    "PSN_Node_Inspector": "PSN Node Inspector",
}
