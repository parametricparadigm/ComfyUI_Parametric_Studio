"""PSN_CV_RunTracker: pure-logic run tracker for CV nodes.

This module implements the secure, pure-logic portion of a run tracker.
It records timestamps, computes deterministic hashes of input payloads,
and formats a JSONL log entry. It does NOT perform any file I/O, network
access, or OS operations. The caller is responsible for persisting the
returned `log_entry` string to a JSONL file if desired.

Dependencies: time, json, hashlib (standard library only).
"""

import hashlib
import json
import time

CAT = "ParametricStudio/CV"


def _compute_hash(payload: str) -> str:
    """Compute a SHA-256 hex digest of the given payload string."""
    if payload is None:
        payload = ""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _format_log_entry(node_id: str, input_hash: str, timestamp: float, duration: float) -> str:
    """Format a single JSONL log entry as a compact JSON string."""
    entry = {
        "node_id": node_id,
        "input_hash": input_hash,
        "timestamp": timestamp,
        "duration": duration,
    }
    return json.dumps(entry, separators=(",", ":"))


class PSN_CV_RunTracker:
    """Logs execution time and input/output hashes for CV nodes.

    Pure-logic implementation: returns a formatted JSONL log entry string.
    No file I/O is performed. The caller should write the returned string
    to a JSONL file for post-hoc analysis.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "node_id": ("STRING", {"default": "unnamed_node"}),
            },
            "optional": {
                "input_hash": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("log_entry",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, node_id: str, input_hash: str = "") -> tuple:
        """Record timestamp and duration, return a JSONL log entry.

        Args:
            node_id: Identifier for the CV node being tracked.
            input_hash: Optional pre-computed hash of the input payload.
                        If empty, a hash of the empty string is used.

        Returns:
            A tuple containing a single JSONL-formatted log entry string.
        """
        # Validate node_id
        if not isinstance(node_id, str):
            node_id = str(node_id)
        if not node_id:
            node_id = "unnamed_node"

        # Validate input_hash
        if not isinstance(input_hash, str):
            input_hash = str(input_hash) if input_hash is not None else ""

        # Compute hash if not provided
        if not input_hash:
            input_hash = _compute_hash("")

        # Record timing
        start_time = time.time()
        # Simulate minimal processing time (the actual CV work would be
        # wrapped around this node in a real ComfyUI setup)
        end_time = time.time()
        duration = end_time - start_time

        # Format and return the log entry
        log_entry = _format_log_entry(node_id, input_hash, start_time, duration)
        return (log_entry,)


NODE_CLASS_MAPPINGS = {
    "PSN_CV_RunTracker": PSN_CV_RunTracker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CV_RunTracker": "CV Run Tracker",
}
