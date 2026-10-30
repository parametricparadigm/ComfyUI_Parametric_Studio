"""Parametric Studio validation layer for ComfyUI graphs.

Checks a graph (API-format dict) against a list of forbidden node
combinations before execution.  The graph is passed as a plain dict
so no network / file access is needed.
"""

import torch

CAT = "ParametricStudio/Validation"

# Default forbidden combinations: pairs of node class types that must
# never appear together in the same graph.
DEFAULT_FORBIDDEN = (
    ("WanSVI2Pro", "SeedVR2Upscale"),
    ("SCAILAnimate", "RealESRGANUpscale"),
    ("MMAudioGenerate", "Qwen3TTS"),
)


def _parse_rules(rules):
    """Parse a comma-separated string of 'A|B' pairs into a list of tuples."""
    out = []
    for part in rules.split(","):
        part = part.strip()
        if not part:
            continue
        if "|" in part:
            a, b = part.split("|", 1)
            a, b = a.strip(), b.strip()
            if a and b:
                out.append((a, b))
        else:
            out.append((part,))
    return out


def _node_classes(graph):
    """Extract the set of node class types from an API-format graph dict."""
    classes = set()
    nodes = graph.get("nodes", graph)
    if isinstance(nodes, dict):
        for nid, nd in nodes.items():
            if isinstance(nd, dict):
                cls = nd.get("class_type") or nd.get("type")
                if cls:
                    classes.add(cls)
    elif isinstance(nodes, list):
        for nd in nodes:
            if isinstance(nd, dict):
                cls = nd.get("class_type") or nd.get("type")
                if cls:
                    classes.add(cls)
    return classes


def check_graph(graph, rules):
    """Return (ok, violations) where violations is a list of (rule, present) tuples."""
    classes = _node_classes(graph)
    violations = []
    for rule in rules:
        present = [c for c in rule if c in classes]
        if len(present) == len(rule):
            violations.append((rule, present))
    ok = len(violations) == 0
    return ok, violations


class PSN_GraphValidationLayer:
    """Validate a ComfyUI graph against forbidden node combinations.

    Input: a graph dict (API format) and a rules string.
    Output: a boolean (ok) and a string describing violations.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"default": "{}"}),
                "rules": ("STRING", {"default": "WanSVI2Pro|SeedVR2Upscale,SCAILAnimate|RealESRGANUpscale"}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("ok", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json, rules):
        import json

        try:
            graph = json.loads(graph_json)
        except (json.JSONDecodeError, TypeError):
            return (False, "ERROR: graph_json is not valid JSON")

        if not isinstance(graph, dict):
            return (False, "ERROR: graph must be a JSON object")

        rule_list = _parse_rules(rules)
        if not rule_list:
            return (True, "No rules specified; graph passes.")

        ok, violations = check_graph(graph, rule_list)
        if ok:
            return (True, "PASS: no forbidden combinations found.")

        lines = ["FAIL: forbidden combinations detected:"]
        for rule, present in violations:
            lines.append("  - " + " + ".join(present))
        return (False, "\n".join(lines))


NODE_CLASS_MAPPINGS = {
    "PSN_GraphValidationLayer": PSN_GraphValidationLayer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_GraphValidationLayer": "Graph Validation Layer",
}
