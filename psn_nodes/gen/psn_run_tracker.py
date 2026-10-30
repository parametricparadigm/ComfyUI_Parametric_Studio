"""PSN_Run_Tracker: pure-logic progress tracking and log entry formatting.

This node computes a normalized progress fraction and formats a structured
log entry string. It performs NO file I/O, NO network access, and NO
subprocess calls. The "log_entry" output is a plain string that a downstream
node or external system can write to a file or console.

Inputs:
    run_id (STRING): Identifier for the current run.
    total_items (INT): Total number of items in the grid.
    current_item (INT): Index of the current item (1-based).
    metadata (STRING): Optional metadata to include in the log entry.

Outputs:
    progress (FLOAT): Normalized progress in [0.0, 1.0].
    log_entry (STRING): Formatted log line with timestamp, run_id, progress, and metadata.
"""

import time
import json

CAT = "ParametricStudio/Tracking"


class PSN_RunTracker:
    """Track grid generation progress and produce a formatted log entry."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_id": ("STRING", {"default": "run_001", "multiline": False}),
                "total_items": ("INT", {"default": 10, "min": 1, "max": 1000000, "step": 1}),
                "current_item": ("INT", {"default": 1, "min": 1, "max": 1000000, "step": 1}),
                "metadata": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("progress", "log_entry")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, run_id, total_items, current_item, metadata):
        # Validate and clamp inputs
        if total_items < 1:
            total_items = 1
        if current_item < 1:
            current_item = 1
        if current_item > total_items:
            current_item = total_items

        # Compute progress in [0.0, 1.0]
        progress = float(current_item) / float(total_items)
        progress = max(0.0, min(1.0, progress))

        # Format timestamp (ISO 8601, UTC)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Sanitize metadata: strip control characters, limit length
        if metadata is None:
            metadata = ""
        metadata = str(metadata)
        # Remove control characters except newline, tab
        metadata = "".join(ch for ch in metadata if ch == "\n" or ch == "\t" or ord(ch) >= 32)
        if len(metadata) > 512:
            metadata = metadata[:512] + "..."

        # Build log entry
        log_entry = (
            f"[{timestamp}] run_id={run_id} "
            f"progress={progress:.4f} "
            f"item={current_item}/{total_items} "
            f"metadata={metadata}"
        )

        return (progress, log_entry)


NODE_CLASS_MAPPINGS = {
    "PSN_RunTracker": PSN_RunTracker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RunTracker": "PSN Run Tracker",
}
