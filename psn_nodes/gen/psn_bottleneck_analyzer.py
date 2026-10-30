"""PSN_Bottleneck_Analyzer: pure-logic profiling bottleneck analysis.

This module implements a ComfyUI-style custom node that analyzes a plain
Python dict of profiling data (node name -> execution time in seconds) and
identifies the slowest nodes. It performs no I/O, no network access, no
file access, and no GPU/torch operations. It only accepts plain values
(numbers, strings, dicts) and returns plain values (lists, strings).

The node is safe-by-design: it validates input types, rejects malformed
data, and never executes arbitrary code.
"""

from typing import Any, Dict, List, Tuple

CAT = "ParametricStudio/Profiling"


def _validate_profile_data(profile_data: Any) -> Tuple[bool, str, Dict[str, float]]:
    """Validate and normalize profile data.

    Args:
        profile_data: Expected to be a dict mapping node names (str) to
                      execution times (int or float, non-negative).

    Returns:
        A tuple (is_valid, error_message, normalized_dict).
        If invalid, normalized_dict is empty and error_message explains why.
    """
    if not isinstance(profile_data, dict):
        return False, "profile_data must be a dict", {}

    normalized: Dict[str, float] = {}
    for key, value in profile_data.items():
        if not isinstance(key, str):
            return False, f"Node name must be a string, got {type(key).__name__}", {}
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, f"Execution time for node '{key}' must be a number, got {type(value).__name__}", {}
        if value < 0:
            return False, f"Execution time for node '{key}' must be non-negative, got {value}", {}
        normalized[key] = float(value)

    return True, "", normalized


def _find_bottlenecks(profile_data: Dict[str, float], top_n: int) -> List[Tuple[str, float]]:
    """Sort nodes by execution time descending and return the top N.

    Args:
        profile_data: Normalized dict of node name -> execution time.
        top_n: Number of top bottlenecks to return.

    Returns:
        A list of (node_name, execution_time) tuples, sorted by time descending.
        Ties are broken alphabetically by node name for deterministic output.
    """
    if top_n <= 0:
        return []

    sorted_items = sorted(
        profile_data.items(),
        key=lambda item: (-item[1], item[0])
    )
    return sorted_items[:top_n]


def _build_report(bottlenecks: List[Tuple[str, float]], total_nodes: int, top_n: int) -> str:
    """Build a human-readable report string.

    Args:
        bottlenecks: List of (node_name, execution_time) tuples.
        total_nodes: Total number of nodes in the profile.
        top_n: Requested number of top bottlenecks.

    Returns:
        A formatted string report.
    """
    if not bottlenecks:
        return "No bottlenecks found. Profile data is empty or top_n is 0."

    lines = [
        f"Bottleneck Analysis Report",
        f"Total nodes profiled: {total_nodes}",
        f"Top {top_n} slowest nodes:",
        "-" * 40,
    ]

    for rank, (name, time) in enumerate(bottlenecks, start=1):
        lines.append(f"  {rank}. {name}: {time:.6f} seconds")

    lines.append("-" * 40)
    return "\n".join(lines)


class PSN_Bottleneck_Analyzer:
    """Identifies the slowest nodes in the profile data.

    Accepts a dict of node names to execution times, sorts by time
    descending, and returns the top N slowest nodes along with a
    human-readable report string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "profile_data": ("DICT", {"default": {}}),
                "top_n": ("INT", {"default": 5, "min": 0, "max": 1000, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("top_bottlenecks", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, profile_data: Any, top_n: int) -> Tuple[List, str]:
        """Analyze profile data and return top bottlenecks and a report.

        Args:
            profile_data: Dict mapping node names (str) to execution times (number).
            top_n: Number of top slowest nodes to return.

        Returns:
            A tuple (top_bottlenecks, report) where top_bottlenecks is a list
            of [node_name, execution_time] pairs and report is a string.
        """
        is_valid, error_msg, normalized = _validate_profile_data(profile_data)
        if not is_valid:
            return ([], f"Error: {error_msg}")

        bottlenecks = _find_bottlenecks(normalized, top_n)
        report = _build_report(bottlenecks, len(normalized), top_n)

        # Convert tuples to lists for ComfyUI compatibility
        top_bottlenecks = [[name, time] for name, time in bottlenecks]
        return (top_bottlenecks, report)


NODE_CLASS_MAPPINGS = {
    "PSN_Bottleneck_Analyzer": PSN_Bottleneck_Analyzer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Bottleneck_Analyzer": "PSN Bottleneck Analyzer",
}
