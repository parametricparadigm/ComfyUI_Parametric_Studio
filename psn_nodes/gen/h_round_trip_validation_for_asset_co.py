"""Round-trip validation for asset conversions (ComfyUI custom node).

Simulates the classic export -> re-import -> compare workflow used for
GLB/BVH/FBX asset pipelines, but operates on ComfyUI tensors so it can be
wired into a node graph.  The "export" step is a quantization/rounding
simulation (the kind of lossy step a real format conversion performs),
the "re-import" step is the identity re-read, and the comparison is a
frame-by-frame / element-by-element fidelity check that reports max
absolute error, mean absolute error, and a pass/fail verdict against a
tolerance.

No files are written, no network is used, and inputs are never mutated.
"""

import torch

CAT = "ParametricStudio/Validation"


def _as_tensor(x):
    """Coerce a ComfyUI tensor payload to a float32 torch tensor (copy)."""
    if isinstance(x, dict):
        x = x.get("samples")
    if not isinstance(x, torch.Tensor):
        raise TypeError("expected a torch tensor (or LATENT dict with 'samples')")
    return x.detach().float().clone()


def _quantize(t, bits):
    """Simulate a lossy export: quantize to `bits` levels in [0, 1]."""
    if bits < 1:
        raise ValueError("bits must be >= 1")
    levels = (1 << bits) - 1
    q = torch.round(t * levels) / levels
    return torch.clamp(q, 0.0, 1.0)


def _compare(a, b, tol):
    """Element-wise fidelity report between two same-shape tensors."""
    if a.shape != b.shape:
        raise ValueError(
            "shape mismatch: source %s vs reimported %s" % (tuple(a.shape), tuple(b.shape))
        )
    diff = (a - b).abs()
    max_err = float(diff.max().item()) if diff.numel() else 0.0
    mean_err = float(diff.mean().item()) if diff.numel() else 0.0
    worst = int(diff.argmax().item()) if diff.numel() else 0
    # per-frame (first dim) max error, so callers can see which frame broke
    if a.dim() >= 1 and a.shape[0] > 0:
        per_frame = diff.reshape(a.shape[0], -1).max(dim=1).values
        worst_frame = int(per_frame.argmax().item())
    else:
        per_frame = torch.zeros(0)
        worst_frame = 0
    return {
        "max_err": max_err,
        "mean_err": mean_err,
        "worst_index": worst,
        "worst_frame": worst_frame,
        "per_frame_max": per_frame,
        "passed": max_err <= tol,
    }


class PSN_RoundTripAssetValidation:
    """Simulate a lossy export/re-import and validate fidelity frame-by-frame.

    Accepts an IMAGE or LATENT tensor, quantizes it to `bits` levels (the
    simulated export), re-reads it (the simulated re-import), and compares
    against the original.  Returns the re-imported tensor plus a report
    tensor whose channels are [max_err, mean_err, passed(0/1), worst_frame].
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source": ("IMAGE",),
                "bits": ("INT", {"default": 8, "min": 1, "max": 32}),
                "tolerance": ("FLOAT", {"default": 0.01, "min": 0.0, "max": 1.0, "step": 0.001}),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT")
    RETURN_NAMES = ("reimported", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, source, bits, tolerance):
        src = _as_tensor(source)
        exported = _quantize(src, bits)
        reimported = exported.clone()  # simulated re-read
        rep = _compare(src, reimported, tolerance)
        # report as a 1x1x1x4 float tensor: [max_err, mean_err, passed, worst_frame]
        report = torch.tensor(
            [[[
                [rep["max_err"], rep["mean_err"], 1.0 if rep["passed"] else 0.0, float(rep["worst_frame"])]
            ]]],
            dtype=torch.float32,
        )
        return (reimported, report)


class PSN_RoundTripLatentValidation:
    """Same round-trip fidelity check for LATENT tensors [B,C,H,W]."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "bits": ("INT", {"default": 8, "min": 1, "max": 32}),
                "tolerance": ("FLOAT", {"default": 0.01, "min": 0.0, "max": 1.0, "step": 0.001}),
            }
        }

    RETURN_TYPES = ("LATENT", "FLOAT")
    RETURN_NAMES = ("reimported", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, bits, tolerance):
        src = _as_tensor(latent)
        # latents are not bounded to [0,1]; normalize to [0,1] for quantization
        lo = float(src.min().item())
        hi = float(src.max().item())
        span = hi - lo
        if span < 1e-12:
            norm = torch.zeros_like(src)
        else:
            norm = (src - lo) / span
        exported = _quantize(norm, bits)
        reimported = exported * span + lo
        rep = _compare(src, reimported, tolerance)
        report = torch.tensor(
            [[[
                [rep["max_err"], rep["mean_err"], 1.0 if rep["passed"] else 0.0, float(rep["worst_frame"])]
            ]]],
            dtype=torch.float32,
        )
        out = {"samples": reimported}
        return (out, report)


NODE_CLASS_MAPPINGS = {
    "PSN_RoundTripAssetValidation": PSN_RoundTripAssetValidation,
    "PSN_RoundTripLatentValidation": PSN_RoundTripLatentValidation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RoundTripAssetValidation": "Round-Trip Asset Validation (Image)",
    "PSN_RoundTripLatentValidation": "Round-Trip Asset Validation (Latent)",
}
