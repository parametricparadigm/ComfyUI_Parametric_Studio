"""ParametricStudio read-only fetch_info pattern.

Introspect ComfyUI node definitions from a running instance without
modifying server state. The node accepts a pre-fetched ``object_info``
payload (the JSON that a ComfyUI server returns from the read-only
``/object_info`` endpoint) and reports, for a list of node classes,
whether each class is exposed, what input types it declares, and which
of the caller's expected input names are missing.

The pattern is strictly read-only: no jobs are queued, no server state
is touched, and the input payload is never mutated. In a real ComfyUI
workflow the payload would be produced by a separate fetch step (e.g.
a GET to ``/object_info/<class>``); here the node consumes the payload
directly so the logic is testable offline with plain Python dicts.
"""

import json

CAT = "ParametricStudio/Introspection"


def _spec_of(raw):
    """Extract (type_name, options, config) from one input spec.

    ComfyUI ``/object_info`` input entries look like::

        ["FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}]
        ["INT"]
        ["CLIP", "CONDITIONING"]   # multi-type: list of type names

    Returns a 3-tuple ``(type_name, options, config)`` where
    ``type_name`` is a string (comma-joined for multi-type),
    ``options`` is a list of option keys, and ``config`` is the raw
    config dict (empty dict if absent).
    """
    if not isinstance(raw, (list, tuple)) or len(raw) == 0:
        return ("", [], {})
    first = raw[0]
    if isinstance(first, str):
        type_name = first
    elif isinstance(first, (list, tuple)):
        type_name = ",".join(str(t) for t in first)
    else:
        type_name = str(first)
    # If the first element is a string and there are additional string
    # elements (multi-type spec like ["CLIP", "CONDITIONING"]), join them.
    if isinstance(first, str) and len(raw) > 1 and all(isinstance(x, str) for x in raw[1:]):
        type_name = ",".join(str(x) for x in raw)
    options = []
    config = {}
    if len(raw) > 1 and isinstance(raw[1], dict):
        config = dict(raw[1])
        options = sorted(config.keys())
    return (type_name, options, config)


def _check_graph(graph, info):
    """Compare an API-format graph against an ``object_info`` dict.

    ``graph`` is a dict mapping node-id strings to node dicts with at
    least ``"class_type"`` and ``"inputs"`` keys. ``info`` maps class
    names to their ``/object_info`` entry (a dict with ``"input"``
    containing ``"required"`` and/or ``"optional"`` sub-dicts).

    Returns a list of human-readable problem strings (empty = clean).
    """
    problems = []
    if not isinstance(graph, dict):
        return ["graph is not a dict"]
    for nid, node in graph.items():
        if not isinstance(node, dict):
            problems.append("node %s: not a dict" % nid)
            continue
        cls = node.get("class_type")
        if not cls:
            problems.append("node %s: missing class_type" % nid)
            continue
        if cls not in info:
            problems.append("node %s: class %s not found in object_info" % (nid, cls))
            continue
        entry = info[cls]
        if not isinstance(entry, dict):
            problems.append("node %s: object_info entry for %s is not a dict" % (nid, cls))
            continue
        input_spec = entry.get("input", {})
        if not isinstance(input_spec, dict):
            problems.append("node %s: 'input' key for %s is not a dict" % (nid, cls))
            continue
        required = input_spec.get("required", {})
        optional = input_spec.get("optional", {})
        known = set(required.keys()) | set(optional.keys())
        node_inputs = node.get("inputs", {})
        if not isinstance(node_inputs, dict):
            problems.append("node %s: 'inputs' is not a dict" % nid)
            continue
        for iname in node_inputs:
            if iname not in known:
                problems.append(
                    "node %s: input %r not declared by class %s" % (nid, iname, cls)
                )
    return problems


class PSN_FetchInfoIntrospect:
    """Read-only introspection of ComfyUI node definitions.

    Accepts a JSON string (or pre-parsed dict) of an ``/object_info``
    payload plus a comma-separated list of class names to check, and
    returns a JSON report describing each class's declared inputs and
    any problems found. The payload is never mutated.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "object_info_json": ("STRING", {"default": "{}"}),
                "classes": ("STRING", {"default": ""}),
            },
            "optional": {
                "graph_json": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("report_json", "problems")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, object_info_json, classes, graph_json=""):
        # --- parse object_info payload (read-only) ---
        if isinstance(object_info_json, dict):
            info = object_info_json
        else:
            try:
                info = json.loads(object_info_json)
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("object_info_json is not valid JSON: %s" % exc)
        if not isinstance(info, dict):
            raise ValueError("object_info payload must be a JSON object")

        # --- parse optional graph payload ---
        graph = None
        if graph_json:
            try:
                graph = json.loads(graph_json)
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("graph_json is not valid JSON: %s" % exc)
            if not isinstance(graph, dict):
                raise ValueError("graph_json must be a JSON object")

        # --- build per-class report ---
        wanted = [c.strip() for c in classes.split(",") if c.strip()]
        report = {}
        for cls in wanted:
            if cls not in info:
                report[cls] = {"found": False, "inputs": {}}
                continue
            entry = info[cls]
            if not isinstance(entry, dict):
                report[cls] = {"found": True, "inputs": {}, "error": "entry is not a dict"}
                continue
            input_spec = entry.get("input", {})
            if not isinstance(input_spec, dict):
                report[cls] = {"found": True, "inputs": {}, "error": "'input' is not a dict"}
                continue
            inputs_out = {}
            for section in ("required", "optional"):
                sec = input_spec.get(section, {})
                if not isinstance(sec, dict):
                    continue
                for iname, raw in sec.items():
                    tname, opts, cfg = _spec_of(raw)
                    inputs_out[iname] = {
                        "type": tname,
                        "options": opts,
                        "section": section,
                    }
            report[cls] = {"found": True, "inputs": inputs_out}

        # --- optional graph check ---
        problems = []
        if graph is not None:
            problems = _check_graph(graph, info)

        report_json = json.dumps(report, sort_keys=True)
        problems_str = "; ".join(problems) if problems else ""
        return (report_json, problems_str)


NODE_CLASS_MAPPINGS = {
    "PSN_FetchInfoIntrospect": PSN_FetchInfoIntrospect,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FetchInfoIntrospect": "Fetch Info Introspect (read-only)",
}
