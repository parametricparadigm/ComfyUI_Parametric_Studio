"""Parametric Studio: per-model-family workflow validation node.

Implements a ComfyUI custom node that validates API-format workflow graphs
against a model-family node definition dictionary. Supports two modes:

* offline: compare the graph against a static object-info dictionary
  (the same shape as ComfyUI's /object_info endpoint response).
* live: the node itself cannot open sockets (ComfyUI custom nodes run
  in-process and this module is deliberately network-free), so the live
  mode accepts a pre-fetched object-info dictionary (e.g. captured by a
  read-only GET to /object_info) and validates against it. The helper
  ``build_live_request`` returns the exact GET URL a caller should use.

The node is read-only: it never mutates its inputs and never queues jobs.
"""

import json

import torch

CAT = "ParametricStudio/Validation"


def _s(x):
    """Unwrap a ComfyUI LATENT dict to its samples tensor."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Wrap a samples tensor back into a ComfyUI LATENT dict (new dict)."""
    return {"samples": samples}


def spec_of(raw):
    """Extract (type_name, options, config) from a raw input spec entry.

    ComfyUI object_info input specs look like:
        "required": {"width": ["INT", {"default": 512, "min": 1}], ...}
        "optional": {"cfg": ["FLOAT", {}], ...}
    Each value is either a list [type, config] or a plain type string.
    """
    if isinstance(raw, str):
        return raw, [], {}
    if isinstance(raw, (list, tuple)):
        if len(raw) == 0:
            return "", [], {}
        type_name = raw[0] if isinstance(raw[0], str) else ""
        config = raw[1] if len(raw) > 1 and isinstance(raw[1], dict) else {}
        options = []
        if isinstance(config, dict):
            for key in ("default", "min", "max", "step", "options"):
                if key in config:
                    options.append(key)
        return type_name, options, config
    return "", [], {}


def check_graph(graph, object_info):
    """Compare a single API-format graph against an object_info dictionary.

    ``graph`` is an API-format workflow dict: {"1": {"class_type": ..., "inputs": {...}}, ...}
    ``object_info`` is a dict mapping class_type -> {"input": {"required": {...}, "optional": {...}}, ...}

    Returns a list of problem strings (empty list means the graph is valid).
    Never mutates its inputs.
    """
    problems = []
    if not isinstance(graph, dict):
        return ["graph is not a dict"]
    if not isinstance(object_info, dict):
        return ["object_info is not a dict"]

    for node_id, node in graph.items():
        if not isinstance(node, dict):
            problems.append("node %s: not a dict" % node_id)
            continue
        class_type = node.get("class_type")
        if not isinstance(class_type, str) or not class_type:
            problems.append("node %s: missing class_type" % node_id)
            continue
        if class_type not in object_info:
            problems.append("node %s: unknown class %s" % (node_id, class_type))
            continue
        info = object_info[class_type]
        if not isinstance(info, dict):
            problems.append("node %s: bad object_info entry for %s" % (node_id, class_type))
            continue
        inputs_spec = info.get("input", {})
        if not isinstance(inputs_spec, dict):
            problems.append("node %s: bad input spec for %s" % (node_id, class_type))
            continue
        required = inputs_spec.get("required", {})
        optional = inputs_spec.get("optional", {})
        if not isinstance(required, dict):
            required = {}
        if not isinstance(optional, dict):
            optional = {}

        node_inputs = node.get("inputs", {})
        if not isinstance(node_inputs, dict):
            node_inputs = {}

        # Every required input must be present in the node's inputs.
        for req_name in required:
            if req_name not in node_inputs:
                problems.append("node %s (%s): missing required input %s" % (node_id, class_type, req_name))

        # Every provided input must be known (required or optional).
        for given_name in node_inputs:
            if given_name not in required and given_name not in optional:
                problems.append("node %s (%s): unknown input %s" % (node_id, class_type, given_name))

        # Type-check provided inputs against the spec where possible.
        for given_name, given_val in node_inputs.items():
            spec = required.get(given_name, optional.get(given_name))
            if spec is None:
                continue
            type_name, _opts, _cfg = spec_of(spec)
            if not type_name:
                continue
            # Link inputs like ["1", 0] are references; skip type check.
            if isinstance(given_val, (list, tuple)) and len(given_val) == 2 and isinstance(given_val[0], str):
                continue
            if not _type_matches(type_name, given_val):
                problems.append("node %s (%s): input %s has wrong type (expected %s)" % (node_id, class_type, given_name, type_name))

    return problems


def _type_matches(type_name, value):
    """Loose type check of a graph input value against a ComfyUI type name."""
    if type_name in ("INT", "FLOAT"):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "STRING":
        return isinstance(value, str)
    if type_name in ("BOOLEAN", "BOOL"):
        return isinstance(value, bool)
    if type_name in ("IMAGE", "MASK", "LATENT"):
        # These are usually links in API format; if a literal is given it
        # should be a tensor (offline mode may embed small tensors).
        return isinstance(value, torch.Tensor)
    if type_name == "COMBO":
        return isinstance(value, str)
    # Unknown type: accept anything.
    return True


def build_live_request(port, class_types):
    """Return the GET URL(s) a caller should use to fetch /object_info.

    This module never opens sockets itself; it only describes the request.
    ``port`` is an int, ``class_types`` is an iterable of class names.
    Returns a list of URL strings (one per class, plus a full-info URL).
    """
    if not isinstance(port, int) or isinstance(port, bool):
        raise TypeError("port must be an int")
    if port < 1 or port > 65535:
        raise ValueError("port out of range")
    urls = ["http://127.0.0.1:%d/object_info" % port]
    for ct in class_types:
        if not isinstance(ct, str) or not ct:
            raise TypeError("class types must be non-empty strings")
        urls.append("http://127.0.0.1:%d/object_info/%s" % (port, ct))
    return urls


def validate_family(graphs, object_info, family_name):
    """Validate a dict of graphs for one model family.

    ``graphs``: {graph_name: graph_dict}
    ``object_info``: object_info dictionary
    ``family_name``: label for reporting

    Returns (problems_list, summary_dict). Never mutates inputs.
    """
    all_problems = []
    per_graph = {}
    for name, graph in graphs.items():
        probs = check_graph(graph, object_info)
        per_graph[name] = probs
        for p in probs:
            all_problems.append("[%s] %s: %s" % (family_name, name, p))
    summary = {
        "family": family_name,
        "graphs_checked": len(graphs),
        "graphs_ok": sum(1 for v in per_graph.values() if not v),
        "total_problems": len(all_problems),
    }
    return all_problems, summary


class PSN_FamilyWorkflowValidator:
    """Validate API-format workflow graphs against a model-family object_info dict.

    Modes:
      * offline: pass a static object_info dictionary (JSON string or dict).
      * live: pass a pre-fetched object_info dictionary captured from a
        running ComfyUI instance via GET /object_info (this node does not
        open sockets itself; use build_live_request to get the URLs).

    Inputs:
      graph_json: JSON string of an API-format workflow graph.
      object_info_json: JSON string of the object_info dictionary.
      family_name: label for the model family (e.g. "FLUX", "HunyuanVideo").
      mode: "offline" or "live" (both validate against the provided dict;
            "live" additionally returns the GET URLs that would be used).
      port: port number, used only in live mode to build request URLs.

    Outputs:
      problems: STRING, newline-joined list of problems (empty if valid).
      summary: STRING, JSON summary of the validation.
      valid: BOOLEAN, True if no problems were found.
      request_urls: STRING, JSON list of GET URLs (live mode) or "[]".
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"default": "{}"}),
                "object_info_json": ("STRING", {"default": "{}"}),
                "family_name": ("STRING", {"default": "FLUX"}),
                "mode": (["offline", "live"], {"default": "offline"}),
            },
            "optional": {
                "port": ("INT", {"default": 8188, "min": 1, "max": 65535}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("problems", "summary", "valid", "request_urls")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json, object_info_json, family_name, mode, port=8188):
        # Parse graph JSON.
        try:
            graph = json.loads(graph_json) if isinstance(graph_json, str) else graph_json
        except (json.JSONDecodeError, TypeError) as e:
            return ("graph_json is not valid JSON: %s" % e, json.dumps({"error": "bad graph_json"}), False, "[]")

        # Parse object_info JSON.
        try:
            object_info = json.loads(object_info_json) if isinstance(object_info_json, str) else object_info_json
        except (json.JSONDecodeError, TypeError) as e:
            return ("object_info_json is not valid JSON: %s" % e, json.dumps({"error": "bad object_info_json"}), False, "[]")

        if not isinstance(graph, dict):
            return ("graph must be a JSON object", json.dumps({"error": "graph not a dict"}), False, "[]")
        if not isinstance(object_info, dict):
            return ("object_info must be a JSON object", json.dumps({"error": "object_info not a dict"}), False, "[]")

        # Build request URLs for live mode.
        request_urls = []
        if mode == "live":
            class_types = set()
            for node in graph.values():
                if isinstance(node, dict) and isinstance(node.get("class_type"), str):
                    class_types.add(node["class_type"])
            try:
                request_urls = build_live_request(port, sorted(class_types))
            except (TypeError, ValueError) as e:
                return ("live mode: bad port or class types: %s" % e, json.dumps({"error": str(e)}), False, "[]")

        # Validate.
        problems, summary = validate_family({family_name: graph}, object_info, family_name)
        valid = len(problems) == 0
        problems_str = "\n".join(problems) if problems else ""
        summary_str = json.dumps(summary, sort_keys=True)
        urls_str = json.dumps(request_urls)
        return (problems_str, summary_str, valid, urls_str)


NODE_CLASS_MAPPINGS = {
    "PSN_FamilyWorkflowValidator": PSN_FamilyWorkflowValidator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FamilyWorkflowValidator": "Family Workflow Validator",
}
