"""Parametric Studio - graph inspection node.

Provides a ComfyUI node that inspects a workflow graph (a JSON-like dict of
nodes) and raises an error if any NSFW LoRA is detected, enforcing a strict
content-safety boundary for SFW / kid-friendly workflows.

The inspection is pure Python (no network, no file access): it walks the
graph, finds LoRA-loading nodes, extracts the LoRA model names, and matches
them against a configurable blocklist of NSFW indicators.
"""

import re

CAT = "ParametricStudio/Safety"

# Default indicators that mark a LoRA as NSFW. Matching is case-insensitive
# substring matching against the LoRA model name (and any extra metadata).
DEFAULT_NSFW_MARKERS = (
    "nsfw",
    "explicit",
    "porn",
    "xxx",
    "hentai",
    "nude",
    "naked",
    "undress",
    "undressing",
    "bare",
    "lewd",
    "smut",
    "erotic",
    "adult",
    "18+",
    "r18",
)

# Node class types that load a LoRA in ComfyUI. The LoRA name is read from
# the "lora_name" input by default; a few variants are handled explicitly.
_LORA_NODE_TYPES = (
    "LoraLoader",
    "LoraLoaderModelOnly",
    "LoraLoaderModelOnlyAndClip",
    "LoadLoRAs",
    "LoraLoaderAdvanced",
)

# Input keys that may carry the LoRA model name, in priority order.
_LORA_NAME_KEYS = ("lora_name", "lora", "model_name", "name")


def _as_text(value):
    """Coerce a graph value to a lower-cased string for matching."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, (list, tuple)):
        return " ".join(_as_text(v) for v in value)
    return str(value).lower()


def _extract_lora_names(graph):
    """Return a list of (node_id, lora_name) for every LoRA-loading node.

    `graph` is a dict mapping node id -> node dict, where each node dict has
    at least a "class_type" and an "inputs" mapping. Non-dict entries are
    skipped defensively.
    """
    found = []
    if not isinstance(graph, dict):
        return found
    for node_id, node in graph.items():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type")
        if class_type not in _LORA_NODE_TYPES:
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        name = None
        for key in _LORA_NAME_KEYS:
            if key in inputs and inputs[key] is not None:
                name = inputs[key]
                break
        if name is None:
            continue
        found.append((str(node_id), _as_text(name)))
    return found


def check_graph(graph, markers=None):
    """Inspect `graph` and raise ValueError if any NSFW LoRA is detected.

    Returns a dict with the inspection report:
      {"checked": int, "loras": [(node_id, name), ...], "blocked": [names]}
    """
    if markers is None:
        markers = DEFAULT_NSFW_MARKERS
    marker_list = [m.lower() for m in markers if isinstance(m, str) and m]
    loras = _extract_lora_names(graph)
    blocked = []
    for _node_id, name in loras:
        if any(m in name for m in marker_list):
            blocked.append(name)
    if blocked:
        raise ValueError(
            "NSFW LoRA detected in graph: " + ", ".join(sorted(set(blocked)))
        )
    return {"checked": len(loras), "loras": loras, "blocked": blocked}


def _graph_from_text(text):
    """Parse a JSON workflow graph from a text string.

    Returns (graph, error). On success error is None; on failure graph is
    None and error is a human-readable message.
    """
    import json

    if not isinstance(text, str):
        return None, "graph text must be a string"
    stripped = text.strip()
    if not stripped:
        return None, "graph text is empty"
    try:
        data = json.loads(stripped)
    except Exception as exc:  # noqa: BLE001 - report any parse failure
        return None, "invalid JSON: %s" % exc
    if not isinstance(data, dict):
        return None, "graph must be a JSON object mapping node ids to nodes"
    return data, None


class PSN_GraphNSFWGuard:
    """Raise an error if any NSFW LoRA is detected in the workflow graph.

    Feed the workflow graph as a JSON string (the same shape ComfyUI uses for
    /prompt). The node inspects every LoRA-loading node and blocks the run if
    a LoRA name matches a configurable NSFW marker list.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"multiline": 12, "default": "{}"}),
            },
            "optional": {
                "nsfw_markers": (
                    "STRING",
                    {
                        "multiline": 4,
                        "default": ",".join(DEFAULT_NSFW_MARKERS),
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("report", "lora_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json, nsfw_markers=None):
        graph, err = _graph_from_text(graph_json)
        if err is not None:
            raise ValueError(err)
        markers = None
        if nsfw_markers is not None and str(nsfw_markers).strip():
            markers = [m.strip() for m in str(nsfw_markers).split(",") if m.strip()]
        report = check_graph(graph, markers=markers)
        lines = ["NSFW guard: OK", "LoRA nodes checked: %d" % report["checked"]]
        for node_id, name in report["loras"]:
            lines.append("  node %s -> %s" % (node_id, name))
        return ("\n".join(lines), report["checked"])


NODE_CLASS_MAPPINGS = {
    "PSN_GraphNSFWGuard": PSN_GraphNSFWGuard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_GraphNSFWGuard": "Graph NSFW Guard (block NSFW LoRAs)",
}
