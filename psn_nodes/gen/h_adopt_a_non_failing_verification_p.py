"""ParametricStudio non-failing verification node.

Adopts a "non-failing verification" pattern for ComfyUI node execution:
optional visual/log checks are attempted on the tensor payload, but any
unavailable or failing check is recorded (as a string report) instead of
raising, so the pipeline keeps flowing. The node passes the payload through
untouched and returns a human-readable verification report.

Reference inspiration (not copied): gamebuilder/stages/build3d.py
``_screenshot`` helper, which tries to capture a real-renderer frame and
logs a warning instead of failing the stage when the renderer is missing.
"""

import torch

CAT = "ParametricStudio/Verification"


def _as_tensor(x):
    """Best-effort conversion of a ComfyUI payload to a torch tensor.

    Returns (tensor, kind) where kind is one of 'image', 'mask', 'latent',
    'tensor', 'unknown'. Never mutates the input.
    """
    if isinstance(x, dict):
        samples = x.get("samples")
        if isinstance(samples, torch.Tensor):
            return samples, "latent"
        return None, "unknown"
    if isinstance(x, torch.Tensor):
        if x.dim() == 4 and x.shape[-1] in (1, 3, 4):
            return x, "image"
        if x.dim() == 3:
            return x, "mask"
        return x, "tensor"
    return None, "unknown"


def _check_image(t):
    """Cheap visual sanity checks on an IMAGE tensor [B,H,W,C] in 0..1."""
    notes = []
    if t.dim() != 4:
        notes.append("image: expected rank 4 [B,H,W,C], got rank %d" % t.dim())
        return notes
    b, h, w, c = t.shape
    if c not in (1, 3, 4):
        notes.append("image: channel count %d unusual (expected 1/3/4)" % c)
    if not torch.is_floating_point(t):
        notes.append("image: non-float dtype %s" % t.dtype)
    else:
        lo = float(t.min())
        hi = float(t.max())
        if lo < -1e-6 or hi > 1 + 1e-6:
            notes.append("image: values outside 0..1 (min=%.4f max=%.4f)" % (lo, hi))
    if bool(torch.isnan(t).any()):
        notes.append("image: contains NaN")
    if bool(torch.isinf(t).any()):
        notes.append("image: contains Inf")
    mean = float(t.mean())
    if mean < 0.001:
        notes.append("image: near-black (mean=%.4f)" % mean)
    elif mean > 0.999:
        notes.append("image: near-white (mean=%.4f)" % mean)
    notes.append("image: shape %s mean=%.4f" % (tuple(t.shape), mean))
    return notes


def _check_mask(t):
    """Cheap sanity checks on a MASK tensor [B,H,W]."""
    notes = []
    if t.dim() != 3:
        notes.append("mask: expected rank 3 [B,H,W], got rank %d" % t.dim())
        return notes
    if not torch.is_floating_point(t):
        notes.append("mask: non-float dtype %s" % t.dtype)
    else:
        lo = float(t.min())
        hi = float(t.max())
        if lo < -1e-6 or hi > 1 + 1e-6:
            notes.append("mask: values outside 0..1 (min=%.4f max=%.4f)" % (lo, hi))
    if bool(torch.isnan(t).any()):
        notes.append("mask: contains NaN")
    notes.append("mask: shape %s" % (tuple(t.shape),))
    return notes


def _check_latent(t):
    """Cheap sanity checks on LATENT samples [B,C,H,W]."""
    notes = []
    if t.dim() != 4:
        notes.append("latent: expected rank 4 [B,C,H,W], got rank %d" % t.dim())
        return notes
    if not torch.is_floating_point(t):
        notes.append("latent: non-float dtype %s" % t.dtype)
    if bool(torch.isnan(t).any()):
        notes.append("latent: contains NaN")
    if bool(torch.isinf(t).any()):
        notes.append("latent: contains Inf")
    notes.append("latent: shape %s" % (tuple(t.shape),))
    return notes


def _check_tensor(t):
    notes = []
    if bool(torch.isnan(t).any()):
        notes.append("tensor: contains NaN")
    if bool(torch.isinf(t).any()):
        notes.append("tensor: contains Inf")
    notes.append("tensor: shape %s" % (tuple(t.shape),))
    return notes


_CHECKERS = {
    "image": _check_image,
    "mask": _check_mask,
    "latent": _check_latent,
    "tensor": _check_tensor,
}


def verify_payload(payload, *, strict=False):
    """Run the non-failing verification on a payload.

    Returns (report_lines, ok) where ok is True when no *problem* notes
    were produced. When ``strict`` is False (default) even a failing check
    never raises: problems are simply recorded. When ``strict`` is True the
    caller may choose to raise, but this helper itself still never raises
    on tensor content issues; it only raises on truly unusable input types
    (e.g. a string), mirroring the "attempt but do not halt" contract.
    """
    lines = []
    ok = True
    tensor, kind = _as_tensor(payload)
    if tensor is None:
        lines.append("verify: payload not a tensor/latent (kind=%s); skipped" % kind)
        return lines, ok
    checker = _CHECKERS.get(kind, _check_tensor)
    try:
        notes = checker(tensor)
    except Exception as exc:  # non-failing: record, do not raise
        lines.append("verify: checker %s raised %s: %s" % (kind, type(exc).__name__, exc))
        ok = False
        return lines, ok
    problem_markers = ("outside", "NaN", "Inf", "unusual", "non-float",
                       "expected rank", "near-black", "near-white")
    for note in notes:
        lines.append("verify: %s" % note)
        if any(m in note for m in problem_markers):
            ok = False
    return lines, ok


class PSN_NonFailingVerify:
    """Attempt visual/log checks on a payload without ever failing the pipeline.

    The payload is passed through unchanged (a fresh copy for tensors so the
    input is never mutated). The returned STRING is a multi-line report of
    every check that was attempted; problems are flagged with ``[!]`` but
    the node always succeeds.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "payload": ("IMAGE,MASK,LATENT",),
                "label": ("STRING", {"default": "payload", "multiline": False}),
            },
            "optional": {
                "strict": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE,MASK,LATENT", "STRING")
    RETURN_NAMES = ("payload", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, payload, label="payload", strict=False):
        lines = ["verify[%s]: started" % label]
        try:
            notes, ok = verify_payload(payload, strict=strict)
        except Exception as exc:  # absolute last-resort non-failing guard
            lines.append("verify[%s]: unexpected %s: %s" % (label, type(exc).__name__, exc))
            ok = False
            notes = []
        for note in notes:
            lines.append(note)
        if ok:
            lines.append("verify[%s]: PASS" % label)
        else:
            lines.append("verify[%s]: WARN (non-failing, pipeline continues)" % label)
        report = "\n".join(lines)
        # Pass the payload through untouched; copy tensors so we never mutate.
        if isinstance(payload, dict):
            out = dict(payload)
            if isinstance(out.get("samples"), torch.Tensor):
                out["samples"] = out["samples"].clone()
        elif isinstance(payload, torch.Tensor):
            out = payload.clone()
        else:
            out = payload
        return (out, report)


NODE_CLASS_MAPPINGS = {
    "PSN_NonFailingVerify": PSN_NonFailingVerify,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NonFailingVerify": "Non-Failing Verify (ParametricStudio)",
}
