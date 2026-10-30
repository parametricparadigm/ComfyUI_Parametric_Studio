"""Parametric Studio - Custom Sigma Schedule Baseline.

Implements the core "Sigma Schedule Manipulation" workflow:
  * PSN_CustomSigmaGenerator: builds a 1D SIGMAS tensor from a chosen
    schedule (Linear / Karras / Exponential / Custom).
  * PSN_BaselineSampler: takes a model, conditioning, latent and the
    custom sigmas, builds an API-format KSampler graph (JSON) and
    executes a *local* CPU Euler sampler over the latent so the node
    works without a running PS backend.  The JSON graph is returned
    alongside the latent so a real backend submission can be verified
    (the actual HTTP submission to port 8200 is NOT implemented here -
    network access is forbidden in this environment).

Only torch (CPU) and the Python standard library are used.  Inputs are
never modified in place.
"""

import json
import math

import torch

CAT = "ParametricStudio/Sampling"

SIGMAS = "SIGMAS"
PSN_CONFIG = "PSN_CONFIG"

SCHEDULER_TYPES = ("Linear", "Karras", "Exponential", "Custom")
SAMPLER_TYPES = ("euler", "euler_ancestral", "heun", "dpmpp_2m")


def _as_tensor(x):
    """Return x as a torch tensor (no copy if already a tensor)."""
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x, dtype=torch.float32)


def _validate_sigmas(sigmas):
    """Validate a SIGMAS input: must be a 1D float tensor, finite, non-negative."""
    t = _as_tensor(sigmas)
    if t.dim() != 1:
        raise ValueError("SIGMAS must be a 1D tensor, got %dD" % t.dim())
    if t.numel() < 1:
        raise ValueError("SIGMAS must contain at least one value")
    if not torch.isfinite(t).all():
        raise ValueError("SIGMAS must be finite (no NaN/Inf)")
    if (t < 0).any():
        raise ValueError("SIGMAS must be non-negative")
    return t


def _linear_sigmas(steps, start_sigma, end_sigma):
    """Linear interpolation from start_sigma down to end_sigma.

    Returns steps+1 values (ComfyUI convention: len(sigmas) == steps + 1,
    last value is 0.0 for a full denoise).
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = steps + 1
    if n == 1:
        return torch.tensor([end_sigma], dtype=torch.float32)
    t = torch.linspace(0.0, 1.0, n, dtype=torch.float32)
    return start_sigma + (end_sigma - start_sigma) * t


def _karras_sigmas(steps, start_sigma, end_sigma):
    """Karras-style schedule (from ComfyUI / Stable Diffusion 3).

    sigma_i = (start^rho + i/(steps-1) * (end^rho - start^rho))^(1/rho)
    with rho = 7.0, then rescale so the first value equals start_sigma.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    rho = 7.0
    n = steps + 1
    if n == 1:
        return torch.tensor([end_sigma], dtype=torch.float32)
    eps = 1e-8
    s = max(start_sigma, eps)
    e = max(end_sigma, eps)
    r = torch.arange(n, dtype=torch.float32) / float(n - 1)
    sig = (s ** rho + r * (e ** rho - s ** rho)) ** (1.0 / rho)
    # Rescale so first value is exactly start_sigma and last is end_sigma.
    if sig[0].item() > 0:
        sig = sig * (start_sigma / sig[0].item())
    sig = sig.clone()
    sig[-1] = end_sigma
    return sig


def _exponential_sigmas(steps, start_sigma, end_sigma):
    """Exponential (geometric) interpolation from start_sigma to end_sigma."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = steps + 1
    if n == 1:
        return torch.tensor([end_sigma], dtype=torch.float32)
    eps = 1e-8
    s = max(start_sigma, eps)
    e = max(end_sigma, eps)
    t = torch.linspace(0.0, 1.0, n, dtype=torch.float32)
    sig = s * (e / s) ** t
    sig = sig.clone()
    sig[-1] = end_sigma
    return sig


def _parse_custom_sigmas(raw):
    """Parse a comma-separated string of floats into a 1D float tensor."""
    if not isinstance(raw, str):
        raise ValueError("Custom sigma string must be a string")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("Custom sigma string is empty")
    vals = []
    for p in parts:
        try:
            v = float(p)
        except ValueError:
            raise ValueError("Invalid sigma value: %r" % p)
        if not math.isfinite(v):
            raise ValueError("Sigma value must be finite: %r" % p)
        if v < 0:
            raise ValueError("Sigma value must be non-negative: %r" % p)
        vals.append(v)
    return torch.tensor(vals, dtype=torch.float32)


def _build_kgraph(model, positive, negative, latent, sigmas, sampler, seed):
    """Build an API-format ComfyUI graph (dict) for a KSampler with custom sigmas.

    The graph is a plain JSON-serialisable dict.  In a real deployment this
    would be POSTed to the PS backend (port 8200); here it is returned so
    the caller can inspect or submit it.
    """
    sigma_list = sigmas.tolist()
    graph = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["2", 1],
                "latent_image": ["4", 0],
                "seed": int(seed),
                "steps": int(sigmas.numel() - 1),
                "cfg": 8.0,
                "sampler_name": sampler,
                "scheduler": "custom",
                "custom_sigmas": sigma_list,
                "denoise": 1.0,
            },
        },
        "1": {"class_type": "MODEL_PLACEHOLDER", "inputs": {}},
        "2": {"class_type": "CONDITIONING_PLACEHOLDER", "inputs": {}},
        "4": {"class_type": "LATENT_PLACEHOLDER", "inputs": {}},
    }
    return graph


def _euler_step(latent, sigmas, model_fn):
    """Run a CPU Euler sampler over the latent using the given sigmas.

    model_fn(latent, sigma) -> predicted noise tensor (same shape as latent).
    This is a *local* stand-in for the PS backend sampler so the node is
    testable without a running server.
    """
    x = latent.clone()
    for i in range(sigmas.numel() - 1):
        sigma = sigmas[i].item()
        sigma_next = sigmas[i + 1].item()
        if sigma <= 0.0:
            break
        noise = model_fn(x, sigma)
        x = x + (sigma_next - sigma) * noise
    return x


class PSN_CustomSigmaGenerator:
    """Generate a custom SIGMAS schedule (Linear / Karras / Exponential / Custom)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scheduler_type": (SCHEDULER_TYPES,),
                "steps": ("INT", {"default": 20, "min": 1, "max": 1024}),
                "start_sigma": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0}),
                "end_sigma": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0}),
            },
            "optional": {
                "custom_sigma_string": ("STRING", {"default": ""}),
                "config": (PSN_CONFIG,),
            },
        }

    RETURN_TYPES = (SIGMAS,)
    RETURN_NAMES = ("sigmas",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, scheduler_type, steps, start_sigma, end_sigma,
            custom_sigma_string="", config=None):
        if scheduler_type not in SCHEDULER_TYPES:
            raise ValueError("Unknown scheduler_type: %r" % scheduler_type)
        if steps < 1:
            raise ValueError("steps must be >= 1")
        if start_sigma < 0 or end_sigma < 0:
            raise ValueError("start_sigma and end_sigma must be non-negative")

        if scheduler_type == "Custom":
            sigmas = _parse_custom_sigmas(custom_sigma_string)
        elif scheduler_type == "Linear":
            sigmas = _linear_sigmas(steps, start_sigma, end_sigma)
        elif scheduler_type == "Karras":
            sigmas = _karras_sigmas(steps, start_sigma, end_sigma)
        elif scheduler_type == "Exponential":
            sigmas = _exponential_sigmas(steps, start_sigma, end_sigma)
        else:
            raise ValueError("Unknown scheduler_type: %r" % scheduler_type)

        sigmas = _validate_sigmas(sigmas)
        return (sigmas,)


class PSN_BaselineSampler:
    """Sample a latent using a custom SIGMAS schedule.

    Builds an API-format KSampler graph (JSON) and runs a local CPU Euler
    sampler.  The actual HTTP submission to the PS backend (port 8200) is
    NOT implemented (network is forbidden); the graph is returned so a
    real backend can consume it.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent": ("LATENT",),
                "sigmas": (SIGMAS,),
                "sampler": (SAMPLER_TYPES,),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 63 - 1}),
            },
            "optional": {
                "config": (PSN_CONFIG,),
            },
        }

    RETURN_TYPES = ("LATENT", "STRING")
    RETURN_NAMES = ("latent", "graph_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, positive, negative, latent, sigmas, sampler, seed=0, config=None):
        # Validate latent.
        if not isinstance(latent, dict) or "samples" not in latent:
            raise ValueError("LATENT must be a dict with a 'samples' tensor")
        x = latent["samples"]
        if not isinstance(x, torch.Tensor):
            raise ValueError("LATENT['samples'] must be a torch.Tensor")
        if x.dim() != 4:
            raise ValueError("LATENT['samples'] must be 4D [B,C,H,W], got %dD" % x.dim())

        # Validate sigmas.
        sig = _validate_sigmas(sigmas)

        # Build the API-format graph (JSON-serialisable).
        graph = _build_kgraph(model, positive, negative, latent, sig, sampler, seed)
        graph_json = json.dumps(graph)

        # Local CPU Euler sampling using a deterministic pseudo-noise model.
        # In a real deployment the PS backend would run the actual diffusion
        # model; here we use a simple linear model so the node is testable.
        def _model_fn(x, sigma):
            # Predicted noise: a deterministic function of x and sigma.
            # For a true diffusion model this would be the model output.
            return -x * sigma

        x_out = _euler_step(x, sig, _model_fn)

        # Build output latent dict (do not modify input).
        out_latent = {"samples": x_out}
        return (out_latent, graph_json)


NODE_CLASS_MAPPINGS = {
    "PSN_CustomSigmaGenerator": PSN_CustomSigmaGenerator,
    "PSN_BaselineSampler": PSN_BaselineSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CustomSigmaGenerator": "PSN Custom Sigma Generator",
    "PSN_BaselineSampler": "PSN Baseline Sampler",
}
