"""PSN Spectral Noise Injection.

Implements the core of the "Spectral Noise Injection" idea from the
Parametric Studio spec (section 39, item 10).  The idea is to inject
high-frequency noise into a latent using FFT-based spectral shaping, and
to use a progressive sigma schedule that emphasises high-frequency
content in later sampling steps.

What IS implemented (torch/stdlib only, CPU-safe):
  * PSN_SpectralScheduler  - generates a sigma schedule (linear, karras,
    exponential, or progressive) and a PSN_NOISE_CONFIG dict describing
    how spectral noise should be shaped (cutoff, weight, seed, etc.).
  * PSN_SpectralNoise      - given a latent and a noise config, produces
    a new latent with spectrally-shaped noise injected.  Uses torch.fft
    (2-D FFT over the spatial dims of the latent) to build a radial
    frequency mask, attenuates or boosts high frequencies according to
    the config, and adds the shaped noise to the latent.  Never modifies
    the input in place.
  * PSN_SpectralSampler    - a stand-in sampler that performs a simple
    Euler-style denoising loop using the provided sigmas and the
    spectral noise at the first step.  It does NOT call a real diffusion
    model (that would require a MODEL object and a full KSampler
    backend, which are out of scope for a CPU-only torch module).  It
    instead treats the "model" input as an optional callable that maps
    (latent, sigma) -> latent; if none is provided it simply scales the
    latent by the sigma schedule (a no-op denoiser).  This lets the
    data-flow be exercised end-to-end in tests without a GPU model.

What is NOT implemented:
  * Real MODEL / CONDITIONING / KSampler integration (would need a live
    ComfyUI diffusion model and the k_diffusion sampler library).
  * GPU smoke test (CPU-only here; the FFT path is identical on GPU).
  * numpy-based FFT (torch.fft is used instead; numpy is not required).
"""

import math

import torch

CAT = "ParametricStudio/Sampling"


def _as_latent(latent):
    """Validate and return a copy of the latent dict {"samples": tensor}."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise ValueError("latent must be a dict with a 'samples' key")
    x = latent["samples"]
    if not torch.is_tensor(x):
        raise ValueError("latent['samples'] must be a torch tensor")
    if x.dim() != 4:
        raise ValueError("latent['samples'] must be 4-D [B,C,H,W], got %d-D" % x.dim())
    return {"samples": x.detach().clone()}


def _sigma_schedule(steps, schedule_type, start_sigma, end_sigma):
    """Return a 1-D float tensor of `steps + 1` sigma values (descending)."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = steps + 1
    start = float(start_sigma)
    end = float(end_sigma)
    if start <= 0:
        raise ValueError("start_sigma must be > 0")
    if end < 0:
        raise ValueError("end_sigma must be >= 0")

    if schedule_type == "linear":
        sigmas = torch.linspace(start, end, n)
    elif schedule_type == "karras":
        rho = 7.0
        a = start ** (1.0 / rho)
        b = end ** (1.0 / rho) if end > 0 else 0.0
        t = torch.linspace(0.0, 1.0, n)
        sigmas = (a + t * (b - a)) ** rho
    elif schedule_type == "exponential":
        if end == 0:
            ratio = 1e-4 / start if start > 0 else 0.0
            sigmas = start * (ratio ** torch.linspace(0.0, 1.0, n))
            sigmas[-1] = 0.0
        else:
            ratio = end / start
            sigmas = start * (ratio ** torch.linspace(0.0, 1.0, n))
    elif schedule_type == "progressive":
        t = torch.linspace(0.0, 1.0, n)
        knee = 0.6
        mid = start * 0.3
        sigmas = torch.where(
            t <= knee,
            start + (mid - start) * (t / knee),
            mid + (end - mid) * ((t - knee) / (1.0 - knee)),
        )
    else:
        raise ValueError("unknown schedule_type: %r" % schedule_type)

    sigmas = sigmas.float()
    sigmas[-1] = 0.0
    return sigmas


def _build_noise_config(spectral_weight, cutoff_frac, seed, noise_type):
    """Return a PSN_NOISE_CONFIG dict."""
    if not (0.0 <= cutoff_frac <= 1.0):
        raise ValueError("cutoff_frac must be in [0, 1]")
    if spectral_weight < 0:
        raise ValueError("spectral_weight must be >= 0")
    return {
        "spectral_weight": float(spectral_weight),
        "cutoff_frac": float(cutoff_frac),
        "seed": int(seed),
        "noise_type": str(noise_type),
    }


def _radial_freq_mask(H, W, cutoff_frac, device, dtype):
    """Build a 2-D radial frequency mask in [0,1].

    1.0 at DC (low freq), 0.0 at the Nyquist corner (high freq).
    """
    fy = torch.fft.fftfreq(H, device=device, dtype=dtype)
    fx = torch.fft.fftfreq(W, device=device, dtype=dtype)
    fy = fy.abs()
    fx = fx.abs()
    max_r = math.hypot(0.5, 0.5)
    R = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2) / max_r
    lo = cutoff_frac * 0.5
    hi = 1.0 - lo
    mask = torch.clamp((hi - R) / (hi - lo), 0.0, 1.0)
    return mask


def _spectral_noise(shape, cfg, device, dtype):
    """Generate spectrally-shaped noise of the given 4-D shape."""
    B, C, H, W = shape
    seed = int(cfg.get("seed", 0))
    weight = float(cfg.get("spectral_weight", 1.0))
    cutoff = float(cfg.get("cutoff_frac", 0.5))
    noise_type = str(cfg.get("noise_type", "gaussian"))

    g = torch.Generator(device=device).manual_seed(seed)
    if noise_type == "gaussian":
        noise = torch.randn(shape, generator=g, device=device, dtype=dtype)
    elif noise_type == "uniform":
        noise = (torch.rand(shape, generator=g, device=device, dtype=dtype) * 2.0 - 1.0)
    else:
        raise ValueError("unknown noise_type: %r" % noise_type)

    mask = _radial_freq_mask(H, W, cutoff, device, dtype)
    spec = torch.fft.fft2(noise)
    gain = 1.0 + weight * (1.0 - mask)
    gain = gain[None, None, :, :]
    spec = spec * gain
    shaped = torch.fft.ifft2(spec).real
    return shaped


class PSN_SpectralScheduler:
    """Generate a sigma schedule and a spectral noise configuration."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 512}),
                "schedule_type": ("linear", "karras", "exponential", "progressive"),
                "start_sigma": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 100.0}),
                "end_sigma": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0}),
                "spectral_weight": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
                "cutoff_frac": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
                "noise_type": ("gaussian", "uniform"),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 32 - 1}),
            },
            "optional": {
                "config": ("PSN_CONFIG",),
            },
        }

    RETURN_TYPES = ("SIGMAS", "PSN_NOISE_CONFIG")
    RETURN_NAMES = ("sigmas", "noise_config")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, steps, schedule_type, start_sigma, end_sigma,
            spectral_weight, cutoff_frac, noise_type, seed, config=None):
        sigmas = _sigma_schedule(steps, schedule_type, start_sigma, end_sigma)
        noise_config = _build_noise_config(spectral_weight, cutoff_frac, seed, noise_type)
        return (sigmas, noise_config)


class PSN_SpectralNoise:
    """Inject spectrally-shaped noise into a latent (CPU-safe, torch.fft)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "noise_config": ("PSN_NOISE_CONFIG",),
                "noise_scale": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
            },
            "optional": {
                "config": ("PSN_CONFIG",),
            },
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, noise_config, noise_scale, config=None):
        lat = _as_latent(latent)
        x = lat["samples"]
        if not isinstance(noise_config, dict):
            raise ValueError("noise_config must be a dict (PSN_NOISE_CONFIG)")
        noise = _spectral_noise(tuple(x.shape), noise_config, x.device, x.dtype)
        out = x + float(noise_scale) * noise
        return ({"samples": out},)


class PSN_SpectralSampler:
    """Euler-style denoising loop with spectral noise at the first step.

    The `model` input is an optional callable (latent_dict, sigma) ->
    latent_dict that acts as the denoiser.  If None, the latent is simply
    scaled by (1 - sigma) each step (a trivial denoiser).  This is a
    stand-in for a real KSampler; it exercises the data flow and the
    spectral-noise path without requiring a GPU diffusion model.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "sigmas": ("SIGMAS",),
                "noise_config": ("PSN_NOISE_CONFIG",),
                "sampler": ("euler", "euler_ancestral"),
                "noise_scale": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
            },
            "optional": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "config": ("PSN_CONFIG",),
            },
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, sigmas, noise_config, sampler, noise_scale,
            model=None, positive=None, negative=None, config=None):
        lat = _as_latent(latent)
        x = lat["samples"]
        if not torch.is_tensor(sigmas):
            raise ValueError("sigmas must be a 1-D torch tensor")
        if sigmas.dim() != 1:
            raise ValueError("sigmas must be 1-D")
        if sigmas.numel() < 2:
            raise ValueError("sigmas must have at least 2 entries")
        if not isinstance(noise_config, dict):
            raise ValueError("noise_config must be a dict (PSN_NOISE_CONFIG)")

        noise = _spectral_noise(tuple(x.shape), noise_config, x.device, x.dtype)
        x = x + float(noise_scale) * noise

        for i in range(sigmas.numel() - 1):
            sigma = sigmas[i].item()
            next_sigma = sigmas[i + 1].item()
            if model is not None and callable(model):
                x = model({"samples": x}, sigma)["samples"]
            else:
                x = x * (next_sigma / sigma) if sigma > 0 else torch.zeros_like(x)

        return ({"samples": x},)


NODE_CLASS_MAPPINGS = {
    "PSN_SpectralScheduler": PSN_SpectralScheduler,
    "PSN_SpectralNoise": PSN_SpectralNoise,
    "PSN_SpectralSampler": PSN_SpectralSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SpectralScheduler": "PSN Spectral Scheduler",
    "PSN_SpectralNoise": "PSN Spectral Noise",
    "PSN_SpectralSampler": "PSN Spectral Sampler",
}
