"""PSN_Workflow_Orchestrator: pure-logic planning for parallel workflow segments.

This module implements ONLY the safe, pure-Python planning logic for splitting a
workflow into independent segments and checking VRAM budget feasibility. It does
NOT spawn processes, touch the GPU, or perform any I/O. It takes plain values
(strings, numbers, JSON text) and returns plain values (lists, strings).
"""

import json
import re

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Workflow"

# Allow-list of safe segment types that can be run in parallel.
# In a real system these would correspond to ComfyUI node groups that are
# independent (no data dependencies between them).
_SAFE_SEGMENT_TYPES = frozenset({
    "load", "transform", "generate", "postprocess", "save",
})

# Maximum number of segments we will ever plan, to prevent runaway splits.
_MAX_SEGMENTS = 64


def _validate_workflow_json(workflow_json):
    """Validate and parse workflow JSON. Returns (segments, error)."""
    if not isinstance(workflow_json, str):
        return None, "workflow_json must be a string"
    if not workflow_json.strip():
        return None, "workflow_json is empty"
    try:
        data = json.loads(workflow_json)
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"invalid JSON: {e}"
    if not isinstance(data, dict):
        return None, "workflow JSON must be an object"
    # Accept either a 'segments' key or a flat list of node-like dicts.
    if "segments" in data:
        segments = data["segments"]
        if not isinstance(segments, list):
            return None, "'segments' must be a list"
    elif "nodes" in data:
        segments = data["nodes"]
        if not isinstance(segments, list):
            return None, "'nodes' must be a list"
    else:
        return None, "workflow JSON must contain 'segments' or 'nodes' key"
    # Validate each segment.
    cleaned = []
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            return None, f"segment {i} must be an object"
        seg_type = seg.get("type", "")
        if not isinstance(seg_type, str) or not seg_type:
            return None, f"segment {i} missing or invalid 'type'"
        if seg_type not in _SAFE_SEGMENT_TYPES:
            return None, f"segment {i} has disallowed type '{seg_type}'"
        seg_id = seg.get("id", f"seg_{i}")
        if not isinstance(seg_id, str) or not seg_id.strip():
            return None, f"segment {i} has invalid 'id'"
        cleaned.append({"id": seg_id, "type": seg_type})
    if not cleaned:
        return None, "no valid segments found"
    if len(cleaned) > _MAX_SEGMENTS:
        return None, f"too many segments ({len(cleaned)} > {_MAX_SEGMENTS})"
    return cleaned, None


def _compute_vram_budget(max_parallel, vram_per_instance):
    """Compute total VRAM budget. Returns (total_vram, error)."""
    if not isinstance(max_parallel, int) or isinstance(max_parallel, bool):
        return None, "max_parallel must be an integer"
    if max_parallel < 1:
        return None, "max_parallel must be >= 1"
    if max_parallel > _MAX_SEGMENTS:
        return None, f"max_parallel too large (>{_MAX_SEGMENTS})"
    if not isinstance(vram_per_instance, (int, float)) or isinstance(vram_per_instance, bool):
        return None, "vram_per_instance must be a number"
    if vram_per_instance <= 0:
        return None, "vram_per_instance must be > 0"
    total_vram = max_parallel * float(vram_per_instance)
    return total_vram, None


def _split_into_batches(segments, max_parallel):
    """Split segments into batches of at most max_parallel each.

    Returns a list of batches, where each batch is a list of segment dicts.
    """
    batches = []
    for i in range(0, len(segments), max_parallel):
        batch = segments[i:i + max_parallel]
        batches.append(batch)
    return batches


class PSN_Workflow_Orchestrator:
    """Plan parallel workflow segments and check VRAM feasibility.

    Pure-logic node: parses workflow JSON, validates segments, splits them
    into parallel batches, and reports VRAM budget status. No processes,
    no GPU, no I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workflow_json": ("STRING", {"default": "{}", "multiline": True}),
                "max_parallel": ("INT", {"default": 2, "min": 1, "max": _MAX_SEGMENTS, "step": 1}),
                "vram_per_instance": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 1e6, "step": 0.1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("instance_ids", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, workflow_json, max_parallel, vram_per_instance):
        # Validate inputs.
        segments, err = _validate_workflow_json(workflow_json)
        if err:
            return ([], f"error: {err}")

        total_vram, err = _compute_vram_budget(max_parallel, vram_per_instance)
        if err:
            return ([], f"error: {err}")

        # Split into batches.
        batches = _split_into_batches(segments, max_parallel)

        # Generate instance IDs: one per segment, prefixed with batch index.
        instance_ids = []
        for batch_idx, batch in enumerate(batches):
            for seg in batch:
                instance_ids.append(f"inst_{batch_idx}_{seg['id']}")

        # Determine status.
        num_segments = len(segments)
        num_batches = len(batches)
        status = (
            f"ok: {num_segments} segments in {num_batches} batch(es), "
            f"max_parallel={max_parallel}, total_vram={total_vram:.2f}GB"
        )

        return (instance_ids, status)


NODE_CLASS_MAPPINGS = {
    "PSN_Workflow_Orchestrator": PSN_Workflow_Orchestrator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Workflow_Orchestrator": "PSN Workflow Orchestrator",
}
