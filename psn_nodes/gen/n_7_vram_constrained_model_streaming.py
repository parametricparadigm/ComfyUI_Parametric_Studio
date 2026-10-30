"""
VRAM-Constrained Model Streaming (pure-logic core).

This module implements the *planning* and *scheduling* logic for streaming
model blocks to/from GPU memory under a strict VRAM budget. It does NOT
touch torch, ComfyUI internals, or any file/network I/O. Instead it works
on plain Python values (numbers, strings, JSON text) describing a model's
block structure and a VRAM limit, and produces a deterministic streaming
plan (which blocks are resident, which are offloaded, and the order of
transfers) that a real GPU backend could execute.

Node: PSN_WeightFerry
  - Inputs: model_json (STRING, JSON describing blocks), vram_limit (FLOAT, GB),
            block_size_gb (FLOAT, GB per block), overhead_gb (FLOAT, GB fixed overhead)
  - Outputs: plan_json (STRING), resident_count (INT), offloaded_count (INT),
             fits (BOOLEAN), reason (STRING)

The plan is a JSON object with:
  {
    "total_blocks": int,
    "resident_blocks": [int, ...],   # block indices kept on GPU
    "offloaded_blocks": [int, ...],  # block indices on CPU
    "transfer_order": [int, ...],    # order in which blocks are moved in
    "estimated_peak_vram_gb": float,
    "vram_limit_gb": float
  }
"""

import json
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/VRAM"

# Minimum VRAM (GB) that makes sense; below this we reject.
_MIN_VRAM_GB = 0.001
# Maximum VRAM (GB) we accept to avoid absurd inputs.
_MAX_VRAM_GB = 1e6
# Minimum block size (GB) that makes sense.
_MIN_BLOCK_GB = 0.0001
# Maximum block size (GB).
_MAX_BLOCK_GB = 1e5
# Maximum number of blocks we will plan for (safety cap).
_MAX_BLOCKS = 100_000


# ---------------------------------------------------------------------------
# Pure-logic helpers
# ---------------------------------------------------------------------------

def _parse_model_json(model_json):
    """
    Parse the model JSON string.

    Expected format:
      {
        "blocks": [
          {"name": "block_0", "size_gb": 1.2},
          {"name": "block_1", "size_gb": 1.3},
          ...
        ]
      }

    Returns a list of (name, size_gb) tuples.
    Raises ValueError on malformed input.
    """
    if not isinstance(model_json, str):
        raise ValueError("model_json must be a string")
    try:
        data = json.loads(model_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"model_json is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("model_json must be a JSON object")
    if "blocks" not in data:
        raise ValueError("model_json must contain a 'blocks' key")
    blocks = data["blocks"]
    if not isinstance(blocks, list):
        raise ValueError("'blocks' must be a list")
    if len(blocks) > _MAX_BLOCKS:
        raise ValueError(f"Too many blocks: {len(blocks)} > {_MAX_BLOCKS}")

    parsed = []
    for i, blk in enumerate(blocks):
        if not isinstance(blk, dict):
            raise ValueError(f"Block {i} must be an object")
        name = blk.get("name", f"block_{i}")
        if not isinstance(name, str):
            raise ValueError(f"Block {i} name must be a string")
        size = blk.get("size_gb")
        if not isinstance(size, (int, float)) or isinstance(size, bool):
            raise ValueError(f"Block {i} size_gb must be a number")
        size = float(size)
        if size < 0:
            raise ValueError(f"Block {i} size_gb must be non-negative")
        if size > _MAX_BLOCK_GB:
            raise ValueError(f"Block {i} size_gb too large: {size}")
        parsed.append((name, size))
    return parsed


def _compute_plan(blocks, vram_limit_gb, overhead_gb):
    """
    Compute the streaming plan.

    Strategy:
      - Total fixed overhead (activations, buffers, etc.) is `overhead_gb`.
      - Available VRAM for weights = vram_limit_gb - overhead_gb.
      - We greedily fill the GPU with blocks in order until the next block
        would exceed the available VRAM. All remaining blocks are offloaded.
      - The transfer_order is the list of offloaded blocks in the order they
        would be streamed in (i.e., their original order).

    Returns (plan_dict, fits, reason).
    """
    if vram_limit_gb < _MIN_VRAM_GB:
        raise ValueError(f"vram_limit must be >= {_MIN_VRAM_GB} GB")
    if vram_limit_gb > _MAX_VRAM_GB:
        raise ValueError(f"vram_limit must be <= {_MAX_VRAM_GB} GB")
    if overhead_gb < 0:
        raise ValueError("overhead_gb must be non-negative")
    if overhead_gb > _MAX_VRAM_GB:
        raise ValueError(f"overhead_gb must be <= {_MAX_VRAM_GB} GB")

    available = vram_limit_gb - overhead_gb
    if available < 0:
        return (
            {
                "total_blocks": len(blocks),
                "resident_blocks": [],
                "offloaded_blocks": list(range(len(blocks))),
                "transfer_order": list(range(len(blocks))),
                "estimated_peak_vram_gb": overhead_gb,
                "vram_limit_gb": vram_limit_gb,
            },
            False,
            "Overhead exceeds VRAM limit; no blocks can be resident",
        )

    resident = []
    offloaded = []
    used = 0.0
    for i, (_name, size) in enumerate(blocks):
        if used + size <= available + 1e-9:
            resident.append(i)
            used += size
        else:
            offloaded.append(i)

    # If everything fits, no streaming needed.
    if not offloaded:
        return (
            {
                "total_blocks": len(blocks),
                "resident_blocks": resident,
                "offloaded_blocks": [],
                "transfer_order": [],
                "estimated_peak_vram_gb": used + overhead_gb,
                "vram_limit_gb": vram_limit_gb,
            },
            True,
            "All blocks fit in VRAM; no streaming required",
        )

    # If nothing fits, all offloaded.
    if not resident:
        return (
            {
                "total_blocks": len(blocks),
                "resident_blocks": [],
                "offloaded_blocks": offloaded,
                "transfer_order": offloaded,
                "estimated_peak_vram_gb": overhead_gb,
                "vram_limit_gb": vram_limit_gb,
            },
            False,
            "No blocks fit in VRAM; all must be streamed",
        )

    # Partial fit: some resident, some offloaded.
    # Peak VRAM = overhead + max(resident_total, largest_offloaded_block)
    # because at any point we may have all resident blocks plus one offloaded
    # block being transferred in.
    resident_total = sum(blocks[i][1] for i in resident)
    largest_offloaded = max(blocks[i][1] for i in offloaded)
    peak = overhead_gb + max(resident_total, largest_offloaded)

    fits = peak <= vram_limit_gb + 1e-9
    reason = (
        f"{len(resident)} blocks resident, {len(offloaded)} offloaded; "
        f"estimated peak {peak:.4f} GB vs limit {vram_limit_gb:.4f} GB"
    )

    return (
        {
            "total_blocks": len(blocks),
            "resident_blocks": resident,
            "offloaded_blocks": offloaded,
            "transfer_order": offloaded,
            "estimated_peak_vram_gb": peak,
            "vram_limit_gb": vram_limit_gb,
        },
        fits,
        reason,
    )


# ---------------------------------------------------------------------------
# ComfyUI-style node
# ---------------------------------------------------------------------------

class PSN_WeightFerry:
    """
    Plan VRAM-constrained streaming of model blocks.

    Takes a JSON description of model blocks and a VRAM limit, and produces
    a streaming plan (which blocks stay on GPU, which are offloaded, and the
    transfer order). This is pure logic; no GPU or torch is involved.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_json": ("STRING", {"default": '{"blocks": []}', "multiline": True}),
                "vram_limit": ("FLOAT", {"default": 24.0, "min": _MIN_VRAM_GB, "max": _MAX_VRAM_GB, "step": 0.1}),
            },
            "optional": {
                "overhead_gb": ("FLOAT", {"default": 2.0, "min": 0.0, "max": _MAX_VRAM_GB, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("plan_json", "resident_count", "offloaded_count", "fits", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_json, vram_limit, overhead_gb=2.0):
        blocks = _parse_model_json(model_json)
        plan, fits, reason = _compute_plan(blocks, vram_limit, overhead_gb)
        plan_json = json.dumps(plan, indent=2)
        resident_count = len(plan["resident_blocks"])
        offloaded_count = len(plan["offloaded_blocks"])
        return (plan_json, resident_count, offloaded_count, fits, reason)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_WeightFerry": PSN_WeightFerry,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_WeightFerry": "Weight Ferry (VRAM Streaming Plan)",
}
