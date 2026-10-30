"""ParametricStudio - Memory-Heavy Model Streaming.

CPU-only implementation of the core scheduling logic behind two ComfyUI
nodes that let models larger than VRAM be run by streaming transformer
blocks between a slow tier (CPU/RAM) and a fast tier (GPU/VRAM).

Because this sandbox has no real ComfyUI ``MODEL`` objects and no GPU,
the nodes operate on a *model descriptor*: a plain dict that stands in
for a ComfyUI model and carries a list of block parameter tensors.

Descriptor layout (all keys optional except ``blocks``):

    {
        "blocks": [tensor, tensor, ...],   # one tensor per transformer block
        "device": "cpu" | "cuda",          # where the *active* blocks live
        "block_size": int,                 # blocks kept in the fast tier
        "prefetch": bool,                  # prefetch next window
        "offload_blocks": [int, ...],      # indices pinned to the slow tier
        "stream_log": [str, ...],          # audit trail of moves
    }

The streaming scheduler is pure Python + torch (CPU) and is fully unit
tested in ``test_n_6_memory_heavy_model_streaming.py``.
"""

import torch

CAT = "ParametricStudio/MemoryStreaming"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _is_descriptor(model):
    """Return True if *model* looks like a model descriptor dict."""
    return isinstance(model, dict) and isinstance(model.get("blocks"), (list, tuple)) \
        and all(isinstance(b, torch.Tensor) for b in model["blocks"])


def _clone_descriptor(model):
    """Deep-copy a descriptor without touching the original tensors in place.

    Tensors are cloned so that downstream nodes can never mutate the
    upstream model (ComfyUI contract: never modify inputs in place).
    """
    if not _is_descriptor(model):
        raise ValueError("expected a model descriptor dict with a 'blocks' list of tensors")
    out = dict(model)
    out["blocks"] = [b.detach().clone() for b in model["blocks"]]
    for key in ("stream_log", "offload_blocks"):
        if key in out and isinstance(out[key], (list, tuple)):
            out[key] = list(out[key])
    return out


def _validate_indices(indices, n_blocks):
    """Validate a list of block indices against the block count."""
    if not isinstance(indices, (list, tuple)):
        raise TypeError("indices must be a list of ints")
    for i in indices:
        if not isinstance(i, int) or isinstance(i, bool):
            raise TypeError("block indices must be ints, got %r" % (i,))
        if i < 0 or i >= n_blocks:
            raise ValueError("block index %d out of range [0, %d)" % (i, n_blocks))
    return list(indices)


def _parse_block_list(text, n_blocks):
    """Parse a comma-separated string of block indices.

    Accepts forms like ``"0,1,2"``, ``" 3 , 4 "`` and ``""`` (empty -> []).
    Raises on anything that is not a non-negative integer token.
    """
    if text is None:
        return []
    if not isinstance(text, str):
        raise TypeError("offload_blocks must be a comma-separated string")
    text = text.strip()
    if not text:
        return []
    out = []
    for tok in text.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            val = int(tok)
        except ValueError:
            raise ValueError("invalid block index token: %r" % tok)
        if val < 0:
            raise ValueError("block indices must be non-negative, got %d" % val)
        out.append(val)
    return _validate_indices(out, n_blocks)


# ---------------------------------------------------------------------------
# streaming scheduler (pure logic, CPU-only)
# ---------------------------------------------------------------------------

def build_stream_schedule(n_blocks, block_size, prefetch):
    """Compute the ordered list of (window_start, window_end, prefetch_end) tuples.

    The model is processed in windows of ``block_size`` consecutive blocks.
    When ``prefetch`` is True the scheduler also reports how far ahead the
    next window should be staged (one full window ahead, clamped to the end).

    Returns a list of dicts::

        {"start": int, "end": int, "prefetch_end": int}

    where ``[start, end)`` is the active window and ``[end, prefetch_end)``
    is the range that should already be resident in the fast tier before the
    active window finishes.
    """
    if not isinstance(n_blocks, int) or isinstance(n_blocks, bool):
        raise TypeError("n_blocks must be an int")
    if n_blocks <= 0:
        raise ValueError("n_blocks must be positive")
    if not isinstance(block_size, int) or isinstance(block_size, bool):
        raise TypeError("block_size must be an int")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if not isinstance(prefetch, bool):
        raise TypeError("prefetch must be a bool")

    schedule = []
    start = 0
    while start < n_blocks:
        end = min(start + block_size, n_blocks)
        if prefetch:
            prefetch_end = min(end + block_size, n_blocks)
        else:
            prefetch_end = end
        schedule.append({"start": start, "end": end, "prefetch_end": prefetch_end})
        start = end
    return schedule


def apply_stream_schedule(descriptor, schedule):
    """Apply a stream schedule to a descriptor, recording moves in ``stream_log``.

    For each window the blocks in ``[start, prefetch_end)`` are marked as
    resident in the fast tier (``device``) and the rest are marked as
    resident in the slow tier (``cpu``).  The descriptor's ``device`` field
    is updated to reflect the fast tier.

    Returns a *new* descriptor (inputs are never mutated).
    """
    out = _clone_descriptor(descriptor)
    n = len(out["blocks"])
    fast = out.get("device", "cuda")
    slow = "cpu"
    log = list(out.get("stream_log", []))
    resident_fast = set()
    for win in schedule:
        s, e, pe = win["start"], win["end"], win["prefetch_end"]
        for i in range(s, pe):
            if i not in resident_fast:
                log.append("move %d -> %s" % (i, fast))
                resident_fast.add(i)
        for i in range(n):
            if i < s and i in resident_fast:
                # block fell behind the window: evict to slow tier
                log.append("evict %d -> %s" % (i, slow))
                resident_fast.discard(i)
    out["stream_log"] = log
    out["device"] = fast
    return out


def offload_blocks(descriptor, indices):
    """Pin the given block indices to the slow tier.

    Returns a new descriptor whose ``offload_blocks`` field lists the pinned
    indices and whose ``stream_log`` records the offload moves.
    """
    out = _clone_descriptor(descriptor)
    n = len(out["blocks"])
    idx = _validate_indices(indices, n)
    log = list(out.get("stream_log", []))
    existing = set(out.get("offload_blocks", []))
    for i in idx:
        if i not in existing:
            log.append("offload %d -> cpu" % i)
            existing.add(i)
    out["offload_blocks"] = sorted(existing)
    out["stream_log"] = log
    return out


# ---------------------------------------------------------------------------
# ComfyUI nodes
# ---------------------------------------------------------------------------

class PSN_Weight_Ferry:
    """Stream transformer blocks between CPU and GPU in windows.

    Replaces the monolithic forward pass with a block-by-block schedule so
    that models larger than VRAM can be executed.  The node returns a
    patched model descriptor whose ``stream_log`` records every move that
    the scheduler would perform on a real GPU.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "block_size": ("INT", {"default": 4, "min": 1, "max": 256}),
                "prefetch": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, block_size, prefetch):
        if not _is_descriptor(model):
            raise ValueError("model must be a descriptor dict with a 'blocks' list of tensors")
        n = len(model["blocks"])
        schedule = build_stream_schedule(n, block_size, prefetch)
        patched = apply_stream_schedule(model, schedule)
        patched["block_size"] = block_size
        patched["prefetch"] = prefetch
        return (patched,)


class PSN_Block_Offload_Manager:
    """Pin specific transformer blocks to CPU to free VRAM.

    The given block indices are moved to the slow tier and recorded in the
    descriptor's ``offload_blocks`` field.  On a real GPU these blocks would
    be replaced by placeholders that trigger on-demand loading.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "offload_blocks": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, offload_blocks):
        if not _is_descriptor(model):
            raise ValueError("model must be a descriptor dict with a 'blocks' list of tensors")
        n = len(model["blocks"])
        idx = _parse_block_list(offload_blocks, n)
        patched = offload_blocks_fn(model, idx)
        return (patched,)


# alias so the node method name does not shadow the module-level function
offload_blocks_fn = offload_blocks


NODE_CLASS_MAPPINGS = {
    "PSN_Weight_Ferry": PSN_Weight_Ferry,
    "PSN_Block_Offload_Manager": PSN_Block_Offload_Manager,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Weight_Ferry": "Weight Ferry (block streaming)",
    "PSN_Block_Offload_Manager": "Block Offload Manager",
}
