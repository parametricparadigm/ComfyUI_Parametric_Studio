"""PSN_VRAM_History_Logger: pure-logic VRAM history logger.

This module implements the secure, pure-Python logic for a VRAM history
logger. It does NOT import torch, does NOT start threads, and does NOT
access the GPU. Instead, it provides:

- A `VRAMHistoryLogger` class that accepts pre-sampled VRAM values (as a
  list of floats) and records them with timestamps, enforcing a minimum
  interval between samples to prevent excessive CPU usage.
- A `run` function that validates inputs, simulates the sampling logic
  over a provided list of sample values, and returns the history data.

The node is designed to be used in a ComfyUI workflow where an upstream
node (or a future GPU-aware wrapper) provides the actual VRAM samples.
This module handles validation, interval enforcement, and data formatting.
"""

import time
import json

CAT = "ParametricStudio/VRAM"


class VRAMHistoryLogger:
    """Records VRAM usage samples with timestamps, enforcing a minimum interval.

    Attributes:
        run_id: Identifier for this logging session.
        interval_ms: Minimum interval in milliseconds between samples.
        history: List of dicts with 'timestamp_ms' and 'vram_mb' keys.
    """

    def __init__(self, run_id: str, interval_ms: int):
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        if not isinstance(interval_ms, int) or interval_ms < 1:
            raise ValueError("interval_ms must be a positive integer")
        self.run_id = run_id
        self.interval_ms = interval_ms
        self.history = []
        self._last_sample_time_ms = None

    def add_sample(self, vram_mb: float, timestamp_ms: float = None) -> bool:
        """Add a VRAM sample if the interval constraint is satisfied.

        Args:
            vram_mb: VRAM usage in megabytes.
            timestamp_ms: Optional timestamp in ms. If None, uses current time.

        Returns:
            True if the sample was added, False if rejected due to interval.
        """
        if not isinstance(vram_mb, (int, float)) or vram_mb < 0:
            raise ValueError("vram_mb must be a non-negative number")
        if timestamp_ms is None:
            timestamp_ms = time.time() * 1000.0
        if not isinstance(timestamp_ms, (int, float)) or timestamp_ms < 0:
            raise ValueError("timestamp_ms must be a non-negative number")

        if self._last_sample_time_ms is not None:
            if (timestamp_ms - self._last_sample_time_ms) < self.interval_ms:
                return False

        self.history.append({
            "timestamp_ms": float(timestamp_ms),
            "vram_mb": float(vram_mb),
        })
        self._last_sample_time_ms = float(timestamp_ms)
        return True

    def get_history(self) -> list:
        """Return the recorded history as a list of dicts."""
        return list(self.history)

    def to_json(self) -> str:
        """Return the history as a JSON string."""
        return json.dumps({
            "run_id": self.run_id,
            "interval_ms": self.interval_ms,
            "samples": self.history,
        }, indent=2)


def _validate_inputs(run_id: str, interval_ms: int, samples: list) -> tuple:
    """Validate all inputs and return (logger, error_message)."""
    if not isinstance(run_id, str) or not run_id.strip():
        return None, "run_id must be a non-empty string"
    if not isinstance(interval_ms, int) or interval_ms < 1:
        return None, "interval_ms must be a positive integer"
    if not isinstance(samples, list):
        return None, "samples must be a list of numbers"
    for i, s in enumerate(samples):
        if not isinstance(s, (int, float)) or s < 0:
            return None, f"samples[{i}] must be a non-negative number"
    try:
        logger = VRAMHistoryLogger(run_id, interval_ms)
    except ValueError as e:
        return None, str(e)
    return logger, None


class PSN_VRAM_History_Logger:
    """ComfyUI node that records VRAM usage history from pre-sampled values.

    This node does NOT sample the GPU. It accepts a list of VRAM sample
    values (in MB) and records them with simulated timestamps, enforcing
    the minimum interval between samples.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_id": ("STRING", {"default": "run_001"}),
                "interval_ms": ("INT", {"default": 100, "min": 1, "max": 100000, "step": 1}),
                "samples": ("LIST", {"default": []}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("history_data", "history_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, run_id: str, interval_ms: int, samples: list) -> tuple:
        logger, err = _validate_inputs(run_id, interval_ms, samples)
        if err:
            return ([], json.dumps({"error": err}))

        # Simulate timestamps: assume samples arrive at regular intervals
        # starting from 0. We use the actual interval_ms as the time step.
        base_time_ms = 0.0
        for i, vram_mb in enumerate(samples):
            ts = base_time_ms + i * interval_ms
            logger.add_sample(float(vram_mb), timestamp_ms=ts)

        history = logger.get_history()
        history_json = logger.to_json()
        return (history, history_json)


NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_History_Logger": PSN_VRAM_History_Logger,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_History_Logger": "VRAM History Logger",
}
