"""ParametricStudio: check_graph validator for ComfyUI API-format JSON graphs.

This module implements a `check_graph` function that validates API-format
JSON graphs against a ComfyUI instance's `/object_info` dictionary BEFORE
execution.  It catches missing node classes, unknown inputs, wrong input
types, and out-of-range scalar values so that generated graphs can be
rejected (or repaired) before they are ever queued.

The module also exposes a ComfyUI custom node (PSN_CheckGraph) that wraps the
validator so it can be used inside a workflow: feed it a graph JSON string
and an object_info JSON string, and it returns a list of human-readable
problems (empty list == graph is valid).

Only the stdlib + torch (CPU) are used.  No network, no subprocess, no
file I/O.  All validation is pure Python on plain dicts/lists.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import torch

CAT = "ParametricStudio/Graph"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _spec_of(raw: Any) -> Tuple[str, List[Any], Dict[str, Any]]:
    """Extract (type_name, options, config) from one input spec.

    ComfyUI `/object_info` input entries look like:
        "width": ["INT", {"default": 512, "min": 1, "max": 4096}]
        "model": ["MODEL"]
        "vae": [["VAE", "CLIP_VAE"], {"default": "VAE"}]

    Returns ("INT", ["INT"], {"default": 512, ...}) style tuples.  For
    multi-type inputs the first element is a list of type names.
    """
    if not isinstance(raw, list):
        return ("", [], {})
    if len(raw) == 0:
        return ("", [], {})
    head = raw[0]
    if isinstance(head, str):
        type_name = head
        options: List[Any] = [head]
    elif isinstance(head, list):
        type_name = ",".join(str(t) for t in head)
        options = list(head)
    else:
        type_name = str(head)
        options = [head]
    config: Dict[str, Any] = {}
    if len(raw) >= 2 and isinstance(raw[1], dict):
        config = dict(raw[1])
    return (type_name, options, config)


def _type_matches(value_type: str, allowed: List[Any]) -> bool:
    """True if `value_type` is one of the allowed type names."""
    if not allowed:
        return True
    for a in allowed:
        if isinstance(a, str) and a == value_type:
            return True
    return False


def _scalar_in_range(value: Any, config: Dict[str, Any]) -> Optional[str]:
    """Return an error string if a scalar value violates min/max/step."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    lo = config.get("min")
    hi = config.get("max")
    if isinstance(lo, (int, float)) and value < lo:
        return f"value {value!r} is below min {lo!r}"
    if isinstance(hi, (int, float)) and value > hi:
        return f"value {value!r} is above max {hi!r}"
    step = config.get("step")
    if isinstance(step, (int, float)) and step > 0:
        # allow tiny float tolerance
        if abs(value % step) > 1e-6 and abs((value % step) - step) > 1e-6:
            return f"value {value!r} is not a multiple of step {step!r}"
    return None


def _is_link(value: Any) -> bool:
    """True if value is a ComfyUI link reference [node_id, slot]."""
    return (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], int)
        and isinstance(value[1], int)
    )


def _node_id_of(value: Any) -> Optional[int]:
    if _is_link(value):
        return int(value[0])
    return None


# ---------------------------------------------------------------------------
# core validator
# ---------------------------------------------------------------------------


def check_graph(graph: Dict[str, Any], info: Dict[str, Any]) -> List[str]:
    """Validate an API-format ComfyUI graph against an /object_info dict.

    Parameters
    ----------
    graph : dict
        API-format graph: {"nodes": {"<id>": {"class_type": str,
        "inputs": {name: value | [src_id, slot]}}}}
    info : dict
        /object_info mapping: {"<class_type>": {"input": {"required":
        {name: spec}, "optional": {name: spec}}, ...}}

    Returns
    -------
    list[str]
        Human-readable problems.  Empty list means the graph is valid.
    """
    problems: List[str] = []

    if not isinstance(graph, dict):
        return ["graph must be a dict"]
    if not isinstance(info, dict):
        return ["object_info must be a dict"]

    nodes = graph.get("nodes")
    if not isinstance(nodes, dict):
        return ["graph['nodes'] must be a dict"]

    # index nodes by id for link resolution
    node_ids = set(nodes.keys())

    for nid, node in nodes.items():
        if not isinstance(node, dict):
            problems.append(f"node {nid!r}: entry must be a dict")
            continue
        class_type = node.get("class_type")
        if not isinstance(class_type, str) or not class_type:
            problems.append(f"node {nid!r}: missing or invalid 'class_type'")
            continue

        spec = info.get(class_type)
        if spec is None:
            problems.append(
                f"node {nid!r}: class_type {class_type!r} not found in object_info"
            )
            continue
        if not isinstance(spec, dict):
            problems.append(f"node {nid!r}: object_info entry for {class_type!r} is malformed")
            continue

        input_spec = spec.get("input")
        if not isinstance(input_spec, dict):
            problems.append(f"node {nid!r}: object_info entry for {class_type!r} has no 'input' dict")
            continue

        required = input_spec.get("required", {})
        optional = input_spec.get("optional", {})
        if not isinstance(required, dict):
            required = {}
        if not isinstance(optional, dict):
            optional = {}

        node_inputs = node.get("inputs", {})
        if not isinstance(node_inputs, dict):
            problems.append(f"node {nid!r}: 'inputs' must be a dict")
            continue

        # 1) required inputs must be present
        for rname in required:
            if rname not in node_inputs:
                problems.append(f"node {nid!r} ({class_type}): missing required input {rname!r}")

        # 2) every supplied input must be known
        for iname, ival in node_inputs.items():
            if iname not in required and iname not in optional:
                problems.append(f"node {nid!r} ({class_type}): unknown input {iname!r}")
                continue

            raw_spec = required.get(iname, optional.get(iname))
            type_name, options, config = _spec_of(raw_spec)

            # link reference?  then just check the source node exists
            if _is_link(ival):
                src = _node_id_of(ival)
                if src is None or str(src) not in node_ids:
                    problems.append(
                        f"node {nid!r} ({class_type}): input {iname!r} links to missing node {src!r}"
                    )
                continue

            # literal value: check type + range
            if isinstance(ival, bool):
                # bool is a subclass of int; treat as its own type
                if not _type_matches("BOOLEAN", options):
                    problems.append(
                        f"node {nid!r} ({class_type}): input {iname!r} expected type {options}, got bool"
                    )
                continue
            if isinstance(ival, (int, float)):
                if not _type_matches("INT", options) and not _type_matches("FLOAT", options):
                    problems.append(
                        f"node {nid!r} ({class_type}): input {iname!r} expected type {options}, got number"
                    )
                else:
                    err = _scalar_in_range(ival, config)
                    if err:
                        problems.append(f"node {nid!r} ({class_type}): input {iname!r}: {err}")
                continue
            if isinstance(ival, str):
                if not _type_matches("STRING", options):
                    problems.append(
                        f"node {nid!r} ({class_type}): input {iname!r} expected type {options}, got string"
                    )
                continue
            if isinstance(ival, list):
                # could be a list-of-strings (e.g. model names) or a link
                # we already handled links above; treat as STRING list
                if not _type_matches("STRING", options):
                    problems.append(
                        f"node {nid!r} ({class_type}): input {iname!r} expected type {options}, got list"
                    )
                continue
            if isinstance(ival, dict):
                # e.g. LATENT dict {"samples": tensor} -- in API format this
                # would normally be a link, but allow dict passthrough
                continue
            # unknown python type
            problems.append(
                f"node {nid!r} ({class_type}): input {iname!r} has unsupported value type {type(ival).__name__}"
            )

    # 3) link integrity: every link target must exist and the source node
    #    must actually have that output (best-effort: we only know class_type)
    for nid, node in nodes.items():
        if not isinstance(node, dict):
            continue
        node_inputs = node.get("inputs", {})
        if not isinstance(node_inputs, dict):
            continue
        for iname, ival in node_inputs.items():
            if _is_link(ival):
                src = _node_id_of(ival)
                if src is not None and str(src) in node_ids:
                    src_node = nodes[str(src)]
                    if not isinstance(src_node, dict):
                        continue
                    # we cannot fully verify output slots without RETURN_TYPES
                    # metadata in object_info; skip deep check.
                    pass

    return problems


# ---------------------------------------------------------------------------
# ComfyUI node wrapper
# ---------------------------------------------------------------------------


def _s(x: Any) -> torch.Tensor:
    """Coerce a tensor-like input to a CPU float tensor (no in-place)."""
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().float()
    return torch.as_tensor(x, dtype=torch.float32)


def _out(latent: Dict[str, Any], samples: torch.Tensor) -> Dict[str, Any]:
    """Build a new LATENT dict without mutating the input."""
    return {"samples": samples}


class PSN_CheckGraph:
    """Validate an API-format ComfyUI graph JSON against /object_info JSON.

    Inputs are JSON strings (so they can be wired from a LoadText or a
    prompt-builder node).  The node returns a STRING with the list of
    problems (empty string == valid) and a BOOLEAN `is_valid`.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"multiline": True, "default": "{}"}),
                "object_info_json": ("STRING", {"multiline": True, "default": "{}"}),
            }
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("problems", "is_valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json: str, object_info_json: str):
        try:
            graph = json.loads(graph_json) if graph_json else {}
        except json.JSONDecodeError as e:
            return (f"graph_json is not valid JSON: {e}", False)
        try:
            info = json.loads(object_info_json) if object_info_json else {}
        except json.JSONDecodeError as e:
            return (f"object_info_json is not valid JSON: {e}", False)

        if not isinstance(graph, dict):
            return ("graph must be a JSON object", False)
        if not isinstance(info, dict):
            return ("object_info must be a JSON object", False)

        problems = check_graph(graph, info)
        text = "\n".join(problems) if problems else ""
        return (text, len(problems) == 0)


# ---------------------------------------------------------------------------
# module-level mappings (required by ComfyUI)
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_CheckGraph": PSN_CheckGraph,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CheckGraph": "Check Graph (validate API JSON vs object_info)",
}
