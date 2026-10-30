"""PSN_WeightComparator: L2 distance between two ComfyUI models, optionally per block.

ComfyUI MODEL objects are opaque wrappers; this node extracts the underlying
state dict (a mapping of parameter name -> torch tensor) and computes the
Frobenius (L2) distance between corresponding weights.  When ``block_level``
is true, distances are aggregated by the leading dotted segment of each
parameter name (e.g. ``model.diffusion_model.blocks.0.attn.q.weight`` ->
``blocks.0``).

Only torch (CPU) and the standard library are used.  Inputs are never
modified in place.
"""

import torch

CAT = "ParametricStudio/Model"


def _state_dict(model):
    """Return a {name: tensor} mapping for a ComfyUI MODEL object.

    ComfyUI models expose ``model.model`` (the underlying nn.Module) or a
    ``state_dict`` method.  For testing we also accept a plain dict or an
    nn.Module directly.
    """
    if isinstance(model, dict):
        return {k: v for k, v in model.items()}
    # ComfyUI MODEL wrapper: has a .model attribute that is an nn.Module
    inner = getattr(model, "model", None)
    if inner is not None and hasattr(inner, "state_dict"):
        return {k: v for k, v in inner.state_dict().items()}
    if hasattr(model, "state_dict"):
        return {k: v for k, v in model.state_dict().items()}
    raise TypeError("Unsupported MODEL type: %r" % type(model))


def _block_key(name, block_level):
    """Map a parameter name to a block label.

    For block_level=True we take the first two dotted segments that start
    with a known block prefix (``blocks``, ``layers``, ``blocks_``),
    falling back to the first segment.  For block_level=False everything
    maps to "__overall__".
    """
    if not block_level:
        return "__overall__"
    parts = name.split(".")
    # Try to find a block-like segment: e.g. blocks.0, layers.1
    for i, p in enumerate(parts):
        if p in ("blocks", "layers") and i + 1 < len(parts) and parts[i + 1].isdigit():
            return "%s.%s" % (p, parts[i + 1])
    # Fallback: first segment
    return parts[0] if parts else name


def _l2_sq(t1, t2):
    """Squared L2 (Frobenius) distance between two tensors, as a python float."""
    d = t1.float() - t2.float()
    return float((d * d).sum().item())


class PSN_WeightComparator:
    """Compute L2 distance between two models, optionally aggregated per block."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_a": ("MODEL",),
                "model_b": ("MODEL",),
                "block_level": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("FLOAT", "CUSTOM")
    RETURN_NAMES = ("L2_DISTANCE", "BLOCK_DISTANCES")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_a, model_b, block_level):
        sd_a = _state_dict(model_a)
        sd_b = _state_dict(model_b)

        keys_a = set(sd_a.keys())
        keys_b = set(sd_b.keys())
        common = keys_a & keys_b

        if not common:
            raise ValueError(
                "Models share no common weight names (a has %d, b has %d)."
                % (len(keys_a), len(keys_b))
            )

        # Accumulate squared distances per block
        block_sq = {}
        for k in sorted(common):
            ta = sd_a[k]
            tb = sd_b[k]
            if ta.shape != tb.shape:
                # Shape mismatch: skip (cannot compare)
                continue
            blk = _block_key(k, block_level)
            block_sq[blk] = block_sq.get(blk, 0.0) + _l2_sq(ta, tb)

        # Overall L2 = sqrt(sum of all squared distances)
        total_sq = sum(block_sq.values())
        l2_distance = total_sq ** 0.5

        # Per-block L2 distances
        block_distances = {k: v ** 0.5 for k, v in sorted(block_sq.items())}

        return (l2_distance, block_distances)


NODE_CLASS_MAPPINGS = {
    "PSN_WeightComparator": PSN_WeightComparator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_WeightComparator": "Weight Comparator (L2)",
}
