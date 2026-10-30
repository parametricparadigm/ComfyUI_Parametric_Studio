"""PSN_GlobalSeedBroadcaster: Broadcasts a single global seed to all seed widgets in the graph, ensuring bit-for-bit reproducibility.

This module implements the pure-logic, secure-by-design part of a global seed broadcaster.
It does NOT open sockets, access files, or use GPU/torch/ComfyUI internals.
It provides:
  - A node class PSN_GlobalSeedBroadcaster that takes a seed and mode, and outputs the resolved seed and a deterministic hash.
  - A helper function psn_broadcast_seed that simulates broadcasting a seed to a list of downstream node identifiers,
    returning a mapping of node_id -> seed value. This is the pure-logic part that a ComfyUI graph injector would use.
  - A helper function psn_seed_hash that computes a deterministic string hash of a seed value.

All functions take plain values (numbers, strings, lists) and return plain values.
"""

import hashlib
import json

CAT = "ParametricStudio/Seed"

# Allowed modes for seed broadcasting
_MODES = ("fixed", "increment")


def psn_seed_hash(seed: int) -> str:
    """Compute a deterministic hex hash string for a given integer seed.
    
    Uses SHA-256 of the JSON-encoded seed value to produce a stable,
    reproducible hash string.
    
    Args:
        seed: An integer seed value.
        
    Returns:
        A 64-character hexadecimal string representing the SHA-256 hash.
    """
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    payload = json.dumps({"seed": seed}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def psn_broadcast_seed(seed: int, mode: str, downstream_nodes: list) -> dict:
    """Simulate broadcasting a global seed to downstream nodes.
    
    In 'fixed' mode, all downstream nodes receive the exact same seed.
    In 'increment' mode, each downstream node receives seed + index,
    where index is the position in the downstream_nodes list.
    
    Args:
        seed: The base integer seed to broadcast.
        mode: Either "fixed" or "increment".
        downstream_nodes: A list of node identifiers (strings) representing
                          downstream nodes that will receive the seed.
                          
    Returns:
        A dictionary mapping each node identifier to its assigned seed value.
        
    Raises:
        ValueError: If mode is not in _MODES.
        TypeError: If seed is not an int or downstream_nodes is not a list.
    """
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")
    if not isinstance(downstream_nodes, list):
        raise TypeError("downstream_nodes must be a list")
    
    result = {}
    for idx, node_id in enumerate(downstream_nodes):
        if mode == "fixed":
            result[node_id] = seed
        else:  # increment
            result[node_id] = seed + idx
    return result


class PSN_GlobalSeedBroadcaster:
    """Broadcasts a single global seed to all seed widgets in the graph, ensuring bit-for-bit reproducibility.
    
    This node acts as a central seed source. It outputs the resolved seed value
    and a deterministic hash of that seed. The hash can be used to verify
    reproducibility across runs.
    
    In 'fixed' mode, the output seed is exactly the input seed.
    In 'increment' mode, the output seed is the input seed (the increment
    behavior for multiple downstream nodes is handled by the broadcast helper).
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1, "step": 1}),
                "mode": (list(_MODES),),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("seed_out", "seed_hash")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, seed: int, mode: str):
        """Resolve the global seed and compute its deterministic hash.
        
        Args:
            seed: The integer seed to broadcast.
            mode: Either "fixed" or "increment".
            
        Returns:
            A tuple of (seed_out, seed_hash) where seed_out is the resolved
            integer seed and seed_hash is the SHA-256 hex string of the seed.
        """
        if not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        if mode not in _MODES:
            raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")
        
        # In both modes, the base seed output is the input seed.
        # The increment mode's per-node offset is handled by psn_broadcast_seed
        # when applied to a list of downstream nodes.
        seed_out = seed
        seed_hash = psn_seed_hash(seed_out)
        return (seed_out, seed_hash)


NODE_CLASS_MAPPINGS = {
    "PSN_GlobalSeedBroadcaster": PSN_GlobalSeedBroadcaster,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_GlobalSeedBroadcaster": "PSN Global Seed Broadcaster",
}
