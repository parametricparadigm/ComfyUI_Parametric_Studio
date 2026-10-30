"""
PSN_Node_Profiler: A pure-logic profiler for tracking execution time of nodes.

This module implements a context-manager based profiler that records start/end
timestamps for named operations (simulating node execution). It does NOT
monkey-patch, import torch/comfy, or perform any I/O. Instead, it provides a
safe, deterministic timing wrapper that can be used to measure the duration
of arbitrary callables or simulated node runs.

The node class `PSN_NodeProfiler` accepts a `run_id` and a list of simulated
node names with their durations (or a callable to time), and returns a
dictionary of profile data including per-node start, end, and duration.

Since we cannot access real ComfyUI execution internals or GPU timing, this
implementation focuses on the pure-logic part: recording and structuring
timing data for a set of named operations.
"""

import time
import contextlib
from typing import Any, Dict, List, Optional, Callable

# We use a simple internal helper to simulate timing without actual sleep
# to keep tests fast and deterministic. In production, this would wrap
# real node execution.

class _TimingContext:
    """Context manager that records start and end times for a named operation."""
    
    def __init__(self, name: str, profile: Dict[str, Any]):
        self.name = name
        self.profile = profile
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        self.profile[self.name] = {
            "start": self.start_time,
            "end": self.end_time,
            "duration": duration
        }
        return False  # Do not suppress exceptions


def _profile_operations(run_id: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Profile a list of operations. Each operation is a dict with:
    - 'name': str, the name of the node/operation
    - 'duration': float, simulated duration in seconds (for testing)
    
    Returns a profile data dictionary with run_id and per-node timing info.
    """
    profile = {"run_id": run_id, "nodes": {}}
    
    for op in operations:
        name = op.get("name", "unknown")
        simulated_duration = op.get("duration", 0.0)
        
        # Use a context manager to record timing
        with _TimingContext(name, profile["nodes"]):
            # Simulate work by sleeping for the specified duration
            # In a real scenario, this would be the actual node execution
            if simulated_duration > 0:
                time.sleep(simulated_duration)
    
    # Add total duration
    if profile["nodes"]:
        total_start = min(node_data["start"] for node_data in profile["nodes"].values())
        total_end = max(node_data["end"] for node_data in profile["nodes"].values())
        profile["total_duration"] = total_end - total_start
    else:
        profile["total_duration"] = 0.0
    
    return profile


class PSN_NodeProfiler:
    """
    A ComfyUI custom node that profiles execution time for a set of named operations.
    
    Inputs:
        run_id (STRING): A unique identifier for this profiling run.
        operations (STRING): JSON string representing a list of operations to profile.
                             Each operation is a dict with 'name' and 'duration'.
    
    Outputs:
        profile_data (DICT): A dictionary containing timing data for each operation.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_id": ("STRING", {"default": "run_001"}),
                "operations": ("STRING", {"default": "[]", "multiline": True}),
            },
            "optional": {
                "verbose": ("BOOLEAN", {"default": False}),
            },
        }
    
    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("profile_data",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Profiling"
    
    def run(self, run_id: str, operations: str, verbose: bool = False) -> tuple:
        """
        Profile the given operations and return timing data.
        
        Args:
            run_id: Unique identifier for this run.
            operations: JSON string containing a list of operation dicts.
            verbose: If True, include additional metadata.
        
        Returns:
            A tuple containing the profile data dictionary.
        """
        import json
        
        # Parse the operations JSON
        try:
            ops_list = json.loads(operations)
            if not isinstance(ops_list, list):
                raise ValueError("Operations must be a JSON list")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in operations: {e}")
        
        # Validate each operation
        for i, op in enumerate(ops_list):
            if not isinstance(op, dict):
                raise ValueError(f"Operation {i} must be a dict")
            if "name" not in op or not isinstance(op["name"], str):
                raise ValueError(f"Operation {i} must have a 'name' string field")
            if "duration" in op:
                if not isinstance(op["duration"], (int, float)):
                    raise ValueError(f"Operation {i} 'duration' must be a number")
                if op["duration"] < 0:
                    raise ValueError(f"Operation {i} 'duration' must be non-negative")
        
        # Profile the operations
        profile = _profile_operations(run_id, ops_list)
        
        if verbose:
            profile["verbose"] = True
            profile["node_count"] = len(ops_list)
        
        return (profile,)


# Module-level mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_NodeProfiler": PSN_NodeProfiler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NodeProfiler": "PSN Node Profiler",
}
