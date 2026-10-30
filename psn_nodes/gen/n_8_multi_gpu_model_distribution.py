"""ParametricStudio - Multi-GPU Model Distribution (CPU-safe core).

Implements the *planning* and *metadata* side of distributing a model's
layers across multiple devices.  Because this environment has no GPUs and
no torch.distributed process group, the nodes operate on a lightweight
"model descriptor" (a dict) that mirrors the structure of a real
``torch.nn.Module`` parameter layout.

What IS implemented (pure torch/stdlib, CPU):
  * PSN_MultiGPU_Init  - validates a device_map, assigns each named layer
    to a device, records the placement plan, and returns an augmented
    model descriptor with a ``_psn_gpu_plan`` key.
  * PSN_MultiGPU_Sync - simulates a gradient synchronisation step: given
    per-device gradient shards it computes the all-reduce (mean) and
    attaches the synchronised gradients to the model descriptor.

What is NOT implemented (requires real multi-GPU hardware):
  * Actual ``.to(device)`` calls on real ``nn.Module`` parameters.
  * ``torch.distributed`` process-group initialisation and real
    all-reduce / all-gather collective communication.
  * ``DistributedDataParallel`` wrapping.
"""

import torch

CAT = "ParametricStudio/MultiGPU"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _validate_device_map(device_map):
    """Validate and normalise a device_map dict.

    Returns a normalised dict {layer_name: device_str}.
    Raises ValueError on bad input.
    """
    if not isinstance(device_map, dict):
        raise ValueError("device_map must be a dict, got %s" % type(device_map).__name__)
    if len(device_map) == 0:
        raise ValueError("device_map must not be empty")
    normalised = {}
    for key, val in device_map.items():
        if not isinstance(key, str) or not key:
            raise ValueError("device_map keys must be non-empty strings")
        if not isinstance(val, str) or not val:
            raise ValueError("device_map values must be non-empty device strings")
        # basic device-string sanity: 'cpu', 'cuda', 'cuda:N', 'mps'
        v = val.strip().lower()
        if v not in ("cpu", "cuda", "mps"):
            if not (v.startswith("cuda:") and v[5:].isdigit()):
                raise ValueError("unrecognised device string: %r" % val)
        normalised[key] = v
    return normalised


def _build_plan(layers, device_map):
    """Build a placement plan: list of {layer, device, param_count}.

    ``layers`` is a list of layer names (strings) or a dict
    {name: param_count}.  Layers not present in device_map are
    assigned to the first device in the map (round-robin fallback).
    """
    if isinstance(layers, dict):
        layer_items = list(layers.items())
    elif isinstance(layers, (list, tuple)):
        layer_items = [(l, 0) for l in layers]
    else:
        raise ValueError("layers must be a list of names or a dict {name: count}")

    devices = list(device_map.values())
    plan = []
    for i, (name, pcount) in enumerate(layer_items):
        dev = device_map.get(name, devices[i % len(devices)])
        plan.append({"layer": name, "device": dev, "param_count": int(pcount)})
    return plan


# ---------------------------------------------------------------------------
# Node 1: PSN_MultiGPU_Init
# ---------------------------------------------------------------------------

class PSN_MultiGPU_Init:
    """Plan the distribution of model layers across devices.

    Accepts a model descriptor (dict with at least a 'layers' key) and a
    device_map, validates everything, and returns the model descriptor
    augmented with a '_psn_gpu_plan' key describing where each layer
    should live.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "device_map": ("DICT",),
            },
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, device_map):
        if not isinstance(model, dict):
            raise ValueError("model must be a dict descriptor")
        layers = model.get("layers")
        if layers is None:
            raise ValueError("model descriptor must contain a 'layers' key")

        norm_map = _validate_device_map(device_map)
        plan = _build_plan(layers, norm_map)

        # never mutate the input
        out = dict(model)
        out["_psn_gpu_plan"] = plan
        out["_psn_device_map"] = norm_map
        return (out,)


# ---------------------------------------------------------------------------
# Node 2: PSN_MultiGPU_Sync
# ---------------------------------------------------------------------------

class PSN_MultiGPU_Sync:
    """Simulate a gradient all-reduce (mean) across devices.

    Input: a model descriptor that already carries ``_psn_gpu_plan``
    (from PSN_MultiGPU_Init) plus a ``grad_shards`` key: a dict mapping
    device -> {layer_name: 1-D float tensor}.

    Output: the same descriptor with ``_psn_synced_grads`` =
    {layer_name: mean-of-shards tensor}.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
            },
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model):
        if not isinstance(model, dict):
            raise ValueError("model must be a dict descriptor")
        if "_psn_gpu_plan" not in model:
            raise ValueError("model has no _psn_gpu_plan; run PSN_MultiGPU_Init first")

        grad_shards = model.get("grad_shards")
        if grad_shards is None:
            raise ValueError("model must contain 'grad_shards' for sync")
        if not isinstance(grad_shards, dict):
            raise ValueError("grad_shards must be a dict {device: {layer: tensor}}")

        # collect per-layer shards across devices
        layer_grads = {}
        for dev, shard in grad_shards.items():
            if not isinstance(shard, dict):
                raise ValueError("each device entry in grad_shards must be a dict")
            for lname, tensor in shard.items():
                if not isinstance(tensor, torch.Tensor):
                    raise ValueError("gradient for %s must be a torch.Tensor" % lname)
                if tensor.dim() != 1:
                    raise ValueError("gradient for %s must be 1-D" % lname)
                layer_grads.setdefault(lname, []).append(tensor)

        synced = {}
        for lname, tensors in layer_grads.items():
            # all-reduce mean: sum / count
            stacked = torch.stack(tensors, dim=0)
            synced[lname] = stacked.mean(dim=0)

        out = dict(model)
        out["_psn_synced_grads"] = synced
        return (out,)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_MultiGPU_Init": PSN_MultiGPU_Init,
    "PSN_MultiGPU_Sync": PSN_MultiGPU_Sync,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MultiGPU_Init": "MultiGPU Init (ParametricStudio)",
    "PSN_MultiGPU_Sync": "MultiGPU Sync (ParametricStudio)",
}
