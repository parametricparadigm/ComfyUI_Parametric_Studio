"""
PSN_Block_Offload_Manager

Pure-logic, secure-by-design implementation of a block offload manager.
This module does NOT touch GPU, torch, ComfyUI internals, or any I/O.
It only handles:
  - Parsing and validating a comma-separated list of block indices.
  - Building an offload plan (which blocks to offload, which to keep).
  - Simulating the state transitions (VRAM vs CPU) for planning/testing.
  - Providing a safe, deterministic 'offload hook' logic that can be
    wrapped by a real ComfyUI node later.

The node class PSN_BlockOffloadManager exposes a ComfyUI-style interface
but its `run` method operates on plain values (strings, ints, dicts) and
returns a plan/state object, not an actual MODEL tensor.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Offload"

# Allowed modes for the offload strategy
_OFFLOAD_MODES = ("all", "range", "explicit")


def _parse_block_indices(spec: str, total_blocks: int) -> list:
    """
    Parse a comma-separated string of block indices or ranges.
    Supports:
      - Single indices: "0,2,5"
      - Ranges: "0-3,7"
      - Negative indices (from end): "-1,-2"
    Returns a sorted list of unique, valid 0-based indices.
    Raises ValueError on malformed input or out-of-range indices.
    """
    if not isinstance(spec, str):
        raise ValueError("offload_blocks must be a string")
    spec = spec.strip()
    if not spec:
        return []

    indices = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part and not part.startswith("-"):
            # Range like "0-3"
            try:
                lo, hi = part.split("-", 1)
                lo, hi = int(lo.strip()), int(hi.strip())
            except ValueError:
                raise ValueError(f"Invalid range: '{part}'")
            if lo > hi:
                raise ValueError(f"Range start > end: '{part}'")
            for i in range(lo, hi + 1):
                if i < 0 or i >= total_blocks:
                    raise ValueError(f"Index {i} out of range [0, {total_blocks})")
                indices.add(i)
        else:
            # Single index, possibly negative
            try:
                idx = int(part)
            except ValueError:
                raise ValueError(f"Invalid index: '{part}'")
            if idx < 0:
                idx = total_blocks + idx
            if idx < 0 or idx >= total_blocks:
                raise ValueError(f"Index {idx} out of range [0, {total_blocks})")
            indices.add(idx)

    return sorted(indices)


def build_offload_plan(total_blocks: int, offload_spec: str, mode: str = "explicit") -> dict:
    """
    Build a deterministic offload plan.
    Returns a dict with:
      - 'offload': sorted list of block indices to move to CPU
      - 'keep': sorted list of block indices to keep in VRAM
      - 'mode': the mode used
      - 'total_blocks': total number of blocks
      - 'offload_count': number of blocks offloaded
      - 'keep_count': number of blocks kept
    """
    if mode not in _OFFLOAD_MODES:
        raise ValueError(f"Unknown mode: {mode}. Must be one of {_OFFLOAD_MODES}")

    if total_blocks <= 0:
        raise ValueError("total_blocks must be positive")

    if mode == "all":
        offload = list(range(total_blocks))
    elif mode == "range":
        # For 'range' mode, offload_spec is "start-end"
        offload = _parse_block_indices(offload_spec, total_blocks)
    else:  # explicit
        offload = _parse_block_indices(offload_spec, total_blocks)

    offload_set = set(offload)
    keep = [i for i in range(total_blocks) if i not in offload_set]

    return {
        "offload": offload,
        "keep": keep,
        "mode": mode,
        "total_blocks": total_blocks,
        "offload_count": len(offload),
        "keep_count": len(keep),
    }


def simulate_offload_state(plan: dict) -> dict:
    """
    Simulate the state after applying the offload plan.
    Returns a dict mapping each block index to its device: 'cpu' or 'vram'.
    """
    state = {}
    for i in range(plan["total_blocks"]):
        state[i] = "cpu" if i in set(plan["offload"]) else "vram"
    return state


def validate_plan(plan: dict) -> tuple:
    """
    Validate an offload plan. Returns (ok: bool, reason: str).
    """
    if not isinstance(plan, dict):
        return False, "Plan must be a dict"
    for key in ("offload", "keep", "total_blocks", "mode"):
        if key not in plan:
            return False, f"Missing key: {key}"
    if plan["total_blocks"] <= 0:
        return False, "total_blocks must be positive"
    if plan["mode"] not in _OFFLOAD_MODES:
        return False, f"Invalid mode: {plan['mode']}"
    offload_set = set(plan["offload"])
    keep_set = set(plan["keep"])
    if offload_set & keep_set:
        return False, "Block appears in both offload and keep"
    if len(offload_set) + len(keep_set) != plan["total_blocks"]:
        return False, "Offload + keep does not cover all blocks"
    for i in plan["offload"]:
        if i < 0 or i >= plan["total_blocks"]:
            return False, f"Offload index {i} out of range"
    for i in plan["keep"]:
        if i < 0 or i >= plan["total_blocks"]:
            return False, f"Keep index {i} out of range"
    return True, "OK"


class PSN_BlockOffloadManager:
    """
    ComfyUI-style node that plans block offloading.
    Pure logic: no torch, no GPU, no I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "total_blocks": ("INT", {"default": 32, "min": 1, "max": 1024, "step": 1}),
                "offload_blocks": ("STRING", {"default": "0-7", "multiline": False}),
                "mode": (list(_OFFLOAD_MODES),),
            },
            "optional": {
                "dry_run": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("DICT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("plan", "state_summary", "valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, total_blocks, offload_blocks, mode, dry_run=True):
        try:
            plan = build_offload_plan(total_blocks, offload_blocks, mode)
            ok, reason = validate_plan(plan)
            if not ok:
                return ({}, reason, False)
            state = simulate_offload_state(plan)
            cpu_blocks = [i for i, d in state.items() if d == "cpu"]
            vram_blocks = [i for i, d in state.items() if d == "vram"]
            summary = (
                f"Total: {total_blocks}, "
                f"Offloaded (CPU): {len(cpu_blocks)} blocks {cpu_blocks}, "
                f"Kept (VRAM): {len(vram_blocks)} blocks {vram_blocks}, "
                f"Mode: {mode}"
            )
            return (plan, summary, True)
        except ValueError as e:
            return ({}, f"Error: {e}", False)


NODE_CLASS_MAPPINGS = {
    "PSN_BlockOffloadManager": PSN_BlockOffloadManager,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_BlockOffloadManager": "PSN Block Offload Manager",
}
