import json
import math

import torch

CAT = "ParametricStudio/ColorPipeline"


def _img(x):
    if not isinstance(x, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if x.dim() != 4 or x.shape[-1] not in (1, 3, 4):
        raise ValueError("image must be [B,H,W,C] with C in {1,3,4}")
    if not torch.is_floating_point(x):
        raise TypeError("image must be a float tensor")
    return x


def _clamp01(t):
    return torch.clamp(t, 0.0, 1.0)


def _op_exposure(img, params):
    ev = float(params.get("ev", 0.0))
    return _clamp01(img * (2.0 ** ev))


def _op_contrast(img, params):
    amount = float(params.get("amount", 1.0))
    if amount < 0.0:
        raise ValueError("contrast amount must be >= 0")
    mid = 0.5
    return _clamp01(mid + (img - mid) * amount)


def _op_brightness(img, params):
    delta = float(params.get("delta", 0.0))
    return _clamp01(img + delta)


def _op_gamma(img, params):
    gamma = float(params.get("gamma", 1.0))
    if gamma <= 0.0:
        raise ValueError("gamma must be > 0")
    return _clamp01(torch.pow(img.clamp(min=1e-6), 1.0 / gamma))


def _op_saturation(img, params):
    amount = float(params.get("amount", 1.0))
    if amount < 0.0:
        raise ValueError("saturation amount must be >= 0")
    if img.shape[-1] < 3:
        return img
    gray = img[..., :3].mean(dim=-1, keepdim=True)
    rgb = img[..., :3] + (img[..., :3] - gray) * (amount - 1.0)
    if img.shape[-1] == 4:
        return _clamp01(torch.cat([rgb, img[..., 3:4]], dim=-1))
    return _clamp01(rgb)


def _op_tint(img, params):
    r = float(params.get("r", 0.0))
    g = float(params.get("g", 0.0))
    b = float(params.get("b", 0.0))
    if img.shape[-1] < 3:
        return img
    shift = torch.tensor([r, g, b], device=img.device, dtype=img.dtype)
    if img.shape[-1] == 4:
        return _clamp01(torch.cat([img[..., :3] + shift, img[..., 3:4]], dim=-1))
    return _clamp01(img + shift)


def _op_levels(img, params):
    in_lo = float(params.get("in_lo", 0.0))
    in_hi = float(params.get("in_hi", 1.0))
    if in_hi <= in_lo:
        raise ValueError("levels in_hi must be > in_lo")
    return _clamp01((img - in_lo) / (in_hi - in_lo))


_OPS = {
    "exposure": _op_exposure,
    "contrast": _op_contrast,
    "brightness": _op_brightness,
    "gamma": _op_gamma,
    "saturation": _op_saturation,
    "tint": _op_tint,
    "levels": _op_levels,
}


def _validate_workflow(wf):
    if not isinstance(wf, dict):
        raise ValueError("workflow must be a JSON object")
    nodes = wf.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("workflow must contain a 'nodes' list")
    if len(nodes) == 0:
        raise ValueError("workflow must contain at least one node")
    if len(nodes) > 64:
        raise ValueError("workflow too long (max 64 nodes)")
    seen = set()
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"node {i} must be an object")
        op = node.get("op")
        if op not in _OPS:
            raise ValueError(f"node {i}: unknown op {op!r}")
        params = node.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"node {i}: params must be an object")
        name = node.get("name")
        if name is not None:
            if not isinstance(name, str) or not name:
                raise ValueError(f"node {i}: name must be a non-empty string")
            if name in seen:
                raise ValueError(f"duplicate node name {name!r} (cycle/aliasing not allowed)")
            seen.add(name)
        # dependency check: a node may only reference earlier nodes
        deps = node.get("depends_on", [])
        if not isinstance(deps, list):
            raise ValueError(f"node {i}: depends_on must be a list")
        for d in deps:
            if d not in seen:
                raise ValueError(f"node {i}: depends_on {d!r} is not a previous node (cycle or forward reference)")


def _run_workflow(image, wf):
    img = image.clone()
    log = []
    for i, node in enumerate(wf["nodes"]):
        op = node["op"]
        params = node.get("params", {})
        before = img
        img = _OPS[op](img, params)
        entry = {
            "index": i,
            "op": op,
            "params": params,
            "name": node.get("name"),
            "mean_before": float(before.mean().item()),
            "mean_after": float(img.mean().item()),
            "shape": list(img.shape),
        }
        log.append(entry)
    return img, log


class PSN_WorkflowOrchestrator:
    """Chains multiple color grading ops defined in a JSON workflow into one pass."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "workflow_json": ("STRING", {"default": '{"nodes": []}', "multiline": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "log_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, workflow_json):
        img = _img(image)
        try:
            wf = json.loads(workflow_json)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"workflow_json is not valid JSON: {e}")
        _validate_workflow(wf)
        out, log = _run_workflow(img, wf)
        return (out, json.dumps(log))


NODE_CLASS_MAPPINGS = {"PSN_WorkflowOrchestrator": PSN_WorkflowOrchestrator}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_WorkflowOrchestrator": "Workflow Orchestrator (Color Pipeline)"}
