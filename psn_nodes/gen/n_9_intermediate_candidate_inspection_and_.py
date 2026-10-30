"""ParametricStudio - Intermediate Candidate Inspection and Branching.

PSN_IntermediateInspector: pauses a sampling pipeline at a given step,
inspects the intermediate latent candidate (producing a small preview
IMAGE), and optionally branches the batch into a new path by duplicating
the candidate with a deterministic perturbation.

Data flow:  KSampler (partial) -> PSN_IntermediateInspector -> KSampler (resume)

Only torch (CPU) and the Python standard library are used. Inputs are
never modified in place.
"""

import torch

CAT = "ParametricStudio/Inspection"


def _latent_samples(latent):
    """Return the samples tensor from a LATENT dict, validating shape."""
    if not isinstance(latent, dict):
        raise TypeError("latent must be a dict with a 'samples' tensor")
    x = latent.get("samples")
    if not isinstance(x, torch.Tensor):
        raise TypeError("latent['samples'] must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError("latent samples must be 4D [B,C,H,W], got %dD" % x.dim())
    return x


def _make_out_latent(base, samples):
    """Build a new LATENT dict without mutating the input dict."""
    return {"samples": samples}


def _latent_to_preview(samples):
    """Convert a latent [B,C,H,W] into a preview IMAGE [B,H,W,C] in 0..1.

    Uses the first three channels (padded with zeros if fewer) as RGB,
    normalised per-channel to the 0..1 range. This is a lightweight
    visualisation, not a VAE decode.
    """
    x = samples.detach().float()
    b, c, h, w = x.shape
    if c >= 3:
        rgb = x[:, :3]
    elif c == 2:
        rgb = torch.cat([x, torch.zeros(b, 1, h, w, device=x.device, dtype=x.dtype)], dim=1)
    elif c == 1:
        rgb = x.repeat(1, 3, 1, 1)
    else:
        raise ValueError("latent must have at least 1 channel")
    # per-channel min-max normalisation to 0..1 (guard against constant channels)
    lo = rgb.amin(dim=(0, 2, 3), keepdim=True)
    hi = rgb.amax(dim=(0, 2, 3), keepdim=True)
    span = (hi - lo)
    span = torch.where(span > 0, span, torch.ones_like(span))
    norm = (rgb - lo) / span
    # HWC
    return norm.permute(0, 2, 3, 1).contiguous()


def _branch_perturb(samples, step):
    """Deterministic, step-seeded perturbation used to create a branch.

    Adds a small zero-mean noise scaled by 1/sqrt(step+1) so later steps
    branch more gently. Uses a CPU generator seeded from the step so the
    result is reproducible and independent of global RNG state.
    """
    x = samples.detach().float()
    gen = torch.Generator(device="cpu")
    gen.manual_seed(1000 + int(step))
    noise = torch.randn(x.shape, generator=gen, device="cpu", dtype=x.dtype)
    scale = 0.05 / (float(step) + 1.0) ** 0.5
    return x + noise * scale


class PSN_IntermediateInspector:
    """Inspect an intermediate latent candidate and optionally branch it.

    - action='inspect': pass the latent through unchanged and emit a preview.
    - action='branch':  emit a perturbed copy of the latent (a new path) and
      a preview of that branch.

    The `step` value is the sampling step at which the pause happens; it is
    used to seed the branch perturbation and is validated to be >= 0.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "step": ("INT", {"default": 10, "min": 0, "max": 10000}),
                "action": (["inspect", "branch"],),
            }
        }

    RETURN_TYPES = ("LATENT", "IMAGE")
    RETURN_NAMES = ("latent_out", "preview")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, step, action):
        if action not in ("inspect", "branch"):
            raise ValueError("action must be 'inspect' or 'branch'")
        if not isinstance(step, int) or isinstance(step, bool):
            raise TypeError("step must be an int")
        if step < 0:
            raise ValueError("step must be >= 0")

        x = _latent_samples(latent)

        if action == "branch":
            out_samples = _branch_perturb(x, step)
        else:
            out_samples = x.detach().clone()

        out_latent = _make_out_latent(latent, out_samples)
        preview = _latent_to_preview(out_samples)
        return (out_latent, preview)


NODE_CLASS_MAPPINGS = {
    "PSN_IntermediateInspector": PSN_IntermediateInspector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_IntermediateInspector": "PSN Intermediate Inspector",
}
