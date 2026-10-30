"""Parametric Studio - Golden Scheduler Integration.

Implements the "Golden Scheduler" idea from the
``sigmas_tools_and_the_golden_scheduler`` pack: an optimized sigma schedule
for flow-matching style diffusion models, plus a small CPU sampler that
consumes the schedule.  Everything here is pure ``torch`` (CPU) + stdlib so
it can be unit-tested without a GPU or a live ComfyUI server.

The "golden" schedule is a shifted flow-matching schedule:

    t_i = i / (steps - 1)                 (i = 0 .. steps-1, descending)
    s_i = shift * t_i / (1 + (shift - 1) * t_i)

with ``shift`` chosen from the model's latent size (bigger images benefit
from a larger shift, mirroring the Flux/SD3 convention).  The final sigma
is always 0.0 so the sampler terminates at the clean latent.
"""

from __future__ import annotations

import math

import torch

CAT = "ParametricStudio/Sampling"

# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _as_tensor(x):
    """Return *x* as a torch tensor (no copy when already a tensor)."""
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x, dtype=torch.float32)


def _latent_samples(latent):
    """Extract the ``samples`` tensor from a ComfyUI LATENT dict."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise ValueError("LATENT input must be a dict with a 'samples' tensor")
    return _as_tensor(latent["samples"])


def _latent_out(latent, samples):
    """Build a new LATENT dict without mutating the input."""
    return {"samples": samples}


def _model_shift(model):
    """Derive a default shift from the model object.

    Real ComfyUI models expose ``model.model.config`` or similar; here we
    accept any object with a ``shift`` attribute, a ``model_config`` dict,
    or fall back to a sensible default of 3.0 (Flux-like).
    """
    if model is None:
        return 3.0
    if hasattr(model, "shift") and isinstance(model.shift, (int, float)):
        return float(model.shift)
    cfg = getattr(model, "model_config", None)
    if isinstance(cfg, dict) and "shift" in cfg:
        return float(cfg["shift"])
    return 3.0


# ---------------------------------------------------------------------------
# schedule math (pure python / torch, no model weights needed)
# ---------------------------------------------------------------------------


def golden_sigmas(steps: int, shift: float = 3.0) -> torch.Tensor:
    """Return a 1-D float32 tensor of *steps* sigma values, descending.

    The schedule is the standard flow-matching shifted schedule used by
    Flux / SD3.  The last value is forced to 0.0.
    """
    if not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if not (isinstance(shift, (int, float)) and shift > 0):
        raise ValueError("shift must be a positive number")
    shift = float(shift)

    if steps == 1:
        return torch.tensor([0.0], dtype=torch.float32)

    # t goes from 1.0 (noisy) down to 0.0 (clean)
    t = torch.linspace(1.0, 0.0, steps, dtype=torch.float32)
    sigmas = shift * t / (1.0 + (shift - 1.0) * t)
    sigmas[-1] = 0.0
    return sigmas


def linear_sigmas(steps: int) -> torch.Tensor:
    """Plain linear schedule for comparison / baseline."""
    if not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if steps == 1:
        return torch.tensor([0.0], dtype=torch.float32)
    t = torch.linspace(1.0, 0.0, steps, dtype=torch.float32)
    t[-1] = 0.0
    return t


def _sigma_preview_image(sigmas: torch.Tensor, width: int = 256, height: int = 64) -> torch.Tensor:
    """Render the sigma curve as a small [1, H, W, 3] float image in 0..1.

    The x-axis is the step index, the y-axis is the sigma value (0 at the
    bottom, max at the top).  The curve is drawn as a 1-px bright line on a
    dark background so it is easy to eyeball in the ComfyUI preview.
    """
    sigmas = sigmas.detach().cpu().float()
    n = sigmas.numel()
    if n == 0:
        raise ValueError("sigmas must be non-empty")
    s_max = float(sigmas.max().item())
    if s_max <= 0.0:
        s_max = 1.0

    img = torch.zeros(1, height, width, 3, dtype=torch.float32)
    # background: very dark blue
    img[:, :, :, 0] = 0.02
    img[:, :, :, 1] = 0.02
    img[:, :, :, 2] = 0.06

    for i in range(n):
        x = int(round(i * (width - 1) / max(n - 1, 1)))
        y = int(round((1.0 - float(sigmas[i].item()) / s_max) * (height - 1)))
        y = max(0, min(height - 1, y))
        img[0, y, x, 0] = 1.0
        img[0, y, x, 1] = 0.9
        img[0, y, x, 2] = 0.2

    return img


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


class PSN_GoldenScheduler:
    """Generate an optimized ("golden") sigma schedule + preview image.

    The schedule is a shifted flow-matching curve.  ``shift`` can be
    overridden manually; otherwise it is derived from the model object
    (``model.shift`` or ``model.model_config['shift']``) defaulting to 3.0.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "steps": ("INT", {"default": 20, "min": 1, "max": 512}),
            },
            "optional": {
                "shift": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0}),
                "config": ("PSN_CONFIG",),
            },
        }

    RETURN_TYPES = ("SIGMAS", "IMAGE")
    RETURN_NAMES = ("sigmas", "preview_image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, steps, shift=0.0, config=None):
        if shift is None or shift <= 0.0:
            shift = _model_shift(model)
        sigmas = golden_sigmas(int(steps), float(shift))
        preview = _sigma_preview_image(sigmas)
        return (sigmas, preview)


class PSN_GoldenSampler:
    """Sample a latent using the golden sigma schedule.

    Implements a simple Euler step in flow-matching space:

        x_{i+1} = x_i + (sigma_{i+1} - sigma_i) * v(x_i, sigma_i)

    where ``v`` is the model's velocity prediction.  For testing we accept
    any callable ``model`` that maps ``(x, sigma) -> v``; a real ComfyUI
    MODEL object would be wrapped by the ComfyUI runtime before reaching
    this node.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent": ("LATENT",),
                "sigmas": ("SIGMAS",),
                "sampler": ("COMBO", {"default": "euler", "options": ["euler", "euler_ancestral"]}),
            },
            "optional": {
                "config": ("PSN_CONFIG",),
            },
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, positive, negative, latent, sigmas, sampler="euler", config=None):
        x = _latent_samples(latent).clone().float()
        sigmas = _as_tensor(sigmas).float().cpu()
        if sigmas.dim() != 1 or sigmas.numel() < 1:
            raise ValueError("sigmas must be a 1-D tensor with at least one value")

        # If the model is a plain callable (test stub), call it directly.
        # A real ComfyUI MODEL would be handled by the ComfyUI runtime;
        # we only support the callable form here.
        if not callable(model):
            raise TypeError("model must be callable (x, sigma) -> v in this implementation")

        for i in range(sigmas.numel() - 1):
            sigma_i = float(sigmas[i].item())
            sigma_next = float(sigmas[i + 1].item())
            v = model(x, torch.tensor(sigma_i, dtype=torch.float32))
            v = _as_tensor(v).float()
            if v.shape != x.shape:
                raise ValueError("model output shape must match latent shape")
            x = x + (sigma_next - sigma_i) * v

        return (_latent_out(latent, x),)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_GoldenScheduler": PSN_GoldenScheduler,
    "PSN_GoldenSampler": PSN_GoldenSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_GoldenScheduler": "PSN Golden Scheduler",
    "PSN_GoldenSampler": "PSN Golden Sampler",
}
