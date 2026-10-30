"""ParametricStudio - Audio Sampling & Scheduling nodes.

Core-only implementation: sigma schedule generation (Linear / Karras /
AudioOptimized) and a deterministic Euler-style latent denoising loop that
maps a latent to a synthetic audio waveform.  No real audio diffusion model
or hdf5plugin decoding is implemented.
"""

import math

import torch

CAT = "ParametricStudio/Audio"


def _as_tensor(x):
    if isinstance(x, torch.Tensor):
        return x
    if isinstance(x, (int, float)):
        return torch.tensor(float(x))
    if isinstance(x, (list, tuple)):
        return torch.tensor(list(x), dtype=torch.float32)
    raise TypeError("expected a tensor-like value")


def _latent_samples(latent):
    if isinstance(latent, dict) and "samples" in latent:
        return latent["samples"]
    if isinstance(latent, torch.Tensor):
        return latent
    raise TypeError("latent must be a dict with 'samples' or a tensor")


def _latent_out(latent, samples):
    if isinstance(latent, dict):
        out = dict(latent)
        out["samples"] = samples
        return out
    return {"samples": samples}


def _karras_sigmas(steps, sigma_max, sigma_min):
    """Karras-style schedule: smoothstep between sigma_min and sigma_max."""
    rho = 7.0
    sigmas = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        # smoothstep
        s = t * t * (3.0 - 2.0 * t)
        # karras: sigma = (sigma_max^(1/rho) + s * (sigma_min^(1/rho) - sigma_max^(1/rho)))^rho
        a = sigma_max ** (1.0 / rho)
        b = sigma_min ** (1.0 / rho)
        sig = (a + s * (b - a)) ** rho
        sigmas.append(sig)
    sigmas.append(0.0)
    return torch.tensor(sigmas, dtype=torch.float32)


def _linear_sigmas(steps, sigma_max, sigma_min):
    sigmas = torch.linspace(sigma_max, sigma_min, steps, dtype=torch.float32)
    sigmas = torch.cat([sigmas, torch.zeros(1, dtype=torch.float32)])
    return sigmas


def _audio_optimized_sigmas(steps, sigma_max, sigma_min):
    """Audio-optimized: front-loaded schedule (more steps at high sigma) to
    capture coarse temporal structure first, then refine fine detail."""
    # Use a power curve: t^gamma with gamma < 1 to front-load
    gamma = 0.6
    sigmas = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        s = t ** gamma
        sig = sigma_max + s * (sigma_min - sigma_max)
        sigmas.append(sig)
    sigmas.append(0.0)
    return torch.tensor(sigmas, dtype=torch.float32)


class PSN_AudioScheduler:
    """Generate a sigma schedule tailored for audio diffusion models."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 512}),
                "scheduler_type": ("Linear", "Karras", "AudioOptimized"),
                "sigma_max": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 100.0}),
                "sigma_min": ("FLOAT", {"default": 0.001, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("SIGMAS",)
    RETURN_NAMES = ("sigmas",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, steps, scheduler_type, sigma_max, sigma_min):
        if steps < 1:
            raise ValueError("steps must be >= 1")
        if sigma_max <= 0:
            raise ValueError("sigma_max must be > 0")
        if sigma_min < 0:
            raise ValueError("sigma_min must be >= 0")
        if sigma_min >= sigma_max:
            raise ValueError("sigma_min must be < sigma_max")

        if scheduler_type == "Linear":
            sigmas = _linear_sigmas(steps, sigma_max, sigma_min)
        elif scheduler_type == "Karras":
            sigmas = _karras_sigmas(steps, sigma_max, sigma_min)
        elif scheduler_type == "AudioOptimized":
            sigmas = _audio_optimized_sigmas(steps, sigma_max, sigma_min)
        else:
            raise ValueError(f"unknown scheduler_type: {scheduler_type}")

        return (sigmas,)


class PSN_AudioSampler:
    """Execute a deterministic Euler-style denoising loop over a latent using
    the given sigmas, then map the result to a synthetic audio waveform.

    No real audio diffusion model is used; the 'model' input is accepted for
    interface compatibility but the denoising is a simple linear interpolation
    toward a target latent derived from the conditioning.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "sigmas": ("SIGMAS",),
                "sampler": ("Euler", "EulerAncestral", "Heun"),
                "sample_rate": ("INT", {"default": 22050, "min": 8000, "max": 96000}),
            },
            "optional": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, sigmas, sampler, sample_rate, positive=None, negative=None):
        samples = _latent_samples(latent)
        if not isinstance(sigmas, torch.Tensor):
            sigmas = _as_tensor(sigmas)
        sigmas = sigmas.to(dtype=torch.float32)

        if sigmas.dim() != 1 or sigmas.numel() < 2:
            raise ValueError("sigmas must be a 1-D tensor with at least 2 elements")

        # Ensure sigmas are strictly decreasing to 0
        if sigmas[-1].item() != 0.0:
            sigmas = torch.cat([sigmas, torch.zeros(1, dtype=torch.float32)])

        # Build a simple target latent: use positive conditioning if available,
        # otherwise use a fixed pattern derived from the latent shape.
        if positive is not None and isinstance(positive, torch.Tensor):
            target = positive.to(dtype=torch.float32)
            # Reshape to match latent shape if possible
            if target.shape != samples.shape:
                target = torch.nn.functional.interpolate(
                    target.reshape(1, -1, 1, 1),
                    size=samples.shape[1:],
                    mode="nearest",
                ).reshape(samples.shape)
        else:
            # Deterministic pseudo-target from latent shape
            target = torch.zeros_like(samples)
            for i in range(samples.shape[0]):
                target[i] = torch.linspace(0.0, 1.0, samples.numel() // samples.shape[0]).reshape(samples.shape[1:])

        # Euler denoising: x_{t+1} = x_t + (sigma_{t+1} - sigma_t) * (target - x_t) / sigma_t
        x = samples.clone().to(dtype=torch.float32)
        for i in range(len(sigmas) - 1):
            sigma_t = sigmas[i].item()
            sigma_next = sigmas[i + 1].item()
            if sigma_t > 1e-8:
                # Simple Euler step toward target
                x = x + (sigma_next - sigma_t) * (target - x) / sigma_t
            else:
                x = target

        # Map latent to audio waveform: take first channel, reshape to [B, samples]
        # Assume latent is [B, C, H, W] or [B, C, T]
        if x.dim() == 4:
            # [B, C, H, W] -> use first channel, flatten H*W as time
            waveform = x[:, 0, :, :].reshape(x.shape[0], -1)
        elif x.dim() == 3:
            # [B, C, T]
            waveform = x[:, 0, :]
        elif x.dim() == 2:
            waveform = x
        else:
            waveform = x.reshape(x.shape[0], -1)

        # Normalize to [-1, 1]
        max_val = waveform.abs().max()
        if max_val > 1e-8:
            waveform = waveform / max_val

        audio = {
            "waveform": waveform,
            "sample_rate": sample_rate,
        }
        return (audio,)


NODE_CLASS_MAPPINGS = {
    "PSN_AudioScheduler": PSN_AudioScheduler,
    "PSN_AudioSampler": PSN_AudioSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AudioScheduler": "Audio Scheduler",
    "PSN_AudioSampler": "Audio Sampler",
}
