"""PSN Multi-GPU Distribution for Large Models.

Implements a planning/simulation layer for distributing model components
across multiple devices.  Real multi-GPU execution requires ``accelerate``
and a multi-GPU host; this module provides the core planning logic that
torch/stdlib can do: parsing device maps, computing per-device layer
assignments, estimating VRAM budgets, and simulating the distribution.

NOT implemented (requires real multi-GPU + accelerate):
  * Actual model weight movement between GPUs.
  * Real VRAM measurement / offloading at runtime.
  * Communication overhead between GPUs.
"""

import torch

CAT = "ParametricStudio/MultiGPU"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parse_device_map(device_map: str):
    """Parse a comma-separated device map string into a list of device names.

    Accepts e.g. ``"cuda:0,cuda:1"`` or ``"cpu"``.
    Returns a list of strings.
    """
    if not isinstance(device_map, str) or not device_map.strip():
        raise ValueError("device_map must be a non-empty string")
    parts = [p.strip() for p in device_map.split(",") if p.strip()]
    if not parts:
        raise ValueError("device_map must contain at least one device")
    return parts


def _validate_device(dev: str):
    """Validate a single device string."""
    if dev == "cpu":
        return
    if dev.startswith("cuda:"):
        idx = dev[5:]
        if not idx.isdigit():
            raise ValueError(f"Invalid cuda device index: {dev!r}")
        return
    if dev == "cuda":
        return
    raise ValueError(f"Unknown device: {dev!r}")


def _compute_layer_assignment(num_layers: int, devices: list):
    """Compute which layers go to which device using round-robin.

    Returns a list of lists: assignment[i] = list of layer indices on device i.
    """
    n = len(devices)
    assignment = [[] for _ in range(n)]
    for layer_idx in range(num_layers):
        assignment[layer_idx % n].append(layer_idx)
    return assignment


def _estimate_vram(num_layers: int, params_per_layer: float, devices: list):
    """Estimate VRAM usage per device (in bytes) for a uniform model.

    Returns a dict: device -> estimated bytes.
    """
    total_bytes = num_layers * params_per_layer * 4  # fp32
    per_device = total_bytes / len(devices)
    return {dev: per_device for dev in devices}


def _simulate_distribution(num_layers: int, devices: list, offload_threshold: float):
    """Simulate distributing layers across devices.

    Returns a dict with:
      - "assignment": list of lists (layer indices per device)
      - "vram_estimate": dict device -> bytes
      - "offloaded_layers": list of layer indices that would be offloaded
        to CPU if their estimated VRAM share exceeds the threshold.
    """
    assignment = _compute_layer_assignment(num_layers, devices)
    vram = _estimate_vram(num_layers, 1.0, devices)  # 1 param per layer for sim
    total_vram = sum(vram.values())
    offloaded = []
    for i, dev in enumerate(devices):
        if dev == "cpu":
            continue
        share = vram[dev] / total_vram if total_vram > 0 else 0.0
        if share > offload_threshold:
            offloaded.extend(assignment[i])
    return {
        "assignment": assignment,
        "vram_estimate": vram,
        "offloaded_layers": offloaded,
    }


# ---------------------------------------------------------------------------
# Node 1: PSN_Distribute_Model
# ---------------------------------------------------------------------------

class PSN_Distribute_Model:
    """Plan the distribution of model layers across multiple devices.

    In a real multi-GPU setup this would use ``accelerate`` to move weights.
    Here it computes the layer assignment and VRAM estimates so downstream
    nodes can be informed about the distribution plan.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "device_map": ("STRING", {"default": "cuda:0,cuda:1"}),
                "num_layers": ("INT", {"default": 32, "min": 1, "max": 1024}),
                "offload_threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("MODEL", "STRING")
    RETURN_NAMES = ("distributed_model", "distribution_plan")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, device_map, num_layers, offload_threshold):
        devices = _parse_device_map(device_map)
        for d in devices:
            _validate_device(d)

        plan = _simulate_distribution(num_layers, devices, offload_threshold)

        # Build a human-readable plan string
        lines = [f"Device map: {', '.join(devices)}"]
        for i, dev in enumerate(devices):
            layers = plan["assignment"][i]
            vram = plan["vram_estimate"][dev]
            lines.append(f"  {dev}: layers {layers}, ~{vram:.0f} bytes")
        if plan["offloaded_layers"]:
            lines.append(f"  Offloaded to CPU: {plan['offloaded_layers']}")
        plan_str = "\n".join(lines)

        # Return the model unchanged (planning only) plus the plan string
        return (model, plan_str)


# ---------------------------------------------------------------------------
# Node 2: PSN_Gather_Results
# ---------------------------------------------------------------------------

class PSN_Gather_Results:
    """Collect and combine results from a distributed model.

    In a real setup this would gather tensors from all devices and
    concatenate/average them.  Here it validates the distribution plan
    and returns the output tensor unchanged (pass-through with metadata).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "distributed_model": ("MODEL",),
                "output": ("IMAGE",),
                "distribution_plan": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("final_output", "gather_info")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, distributed_model, output, distribution_plan):
        if not isinstance(output, torch.Tensor):
            raise TypeError("output must be a torch.Tensor")
        if output.dim() != 4:
            raise ValueError(f"output must be 4D [B,H,W,C], got {output.dim()}D")

        # Count devices from the plan string
        device_count = 1
        if distribution_plan:
            first_line = distribution_plan.split("\n")[0]
            if "Device map:" in first_line:
                devices_str = first_line.split(":", 1)[1].strip()
                device_count = len([d for d in devices_str.split(",") if d.strip()])

        info = f"Gathered from {device_count} device(s). Output shape: {list(output.shape)}"
        # Return output unchanged (no in-place modification)
        return (output, info)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Distribute_Model": PSN_Distribute_Model,
    "PSN_Gather_Results": PSN_Gather_Results,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Distribute_Model": "PSN Distribute Model (Multi-GPU)",
    "PSN_Gather_Results": "PSN Gather Results (Multi-GPU)",
}
