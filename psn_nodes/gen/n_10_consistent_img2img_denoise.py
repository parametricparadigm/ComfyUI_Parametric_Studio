"""ParametricStudio - Consistent Img2Img Denoise.

Standardizes the noise injection amount in image-to-image workflows so the
requested denoise level is applied consistently regardless of the base model's
native behaviour.

Implemented (pure torch / stdlib, CPU):
  * PSN_Actual_Denoise  - builds a *consistent* sigma schedule for a requested
    denoise level and performs a deterministic img2img-style blend in latent
    space (VAE encode of the image + noise injection at the target sigma).
    The full sampler loop (comfy.sample / comfy.sd) is NOT available in this
    environment, so the node performs the core denoise-schedule math and a
    deterministic latent-space blend instead of a real diffusion step.
  * PSN_Denoise_Preview - shows a preview of how the image will look after
    denoising (a blend toward a neutral/noise-free estimate) without running
    the full sampler.

NOT implemented (needs comfy.sample / comfy.sd / a real model):
  * the actual KSampler diffusion loop with the adjusted sigma schedule.
"""

import math

import torch

CAT = "ParametricStudio/Denoise"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _clamp01(x):
    return torch.clamp(x, 0.0, 1.0)


def _validate_image(image):
    """Return a validated, detached copy of an IMAGE tensor [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image must have shape [B, H, W, C], got %s" % (tuple(image.shape),))
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError("image channels must be 1, 3 or 4, got %d" % image.shape[-1])
    if image.shape[1] < 1 or image.shape[2] < 1:
        raise ValueError("image spatial dims must be >= 1")
    if not torch.isfinite(image).all():
        raise ValueError("image contains non-finite values")
    return image.detach().clone().float()


def _validate_denoise(denoise):
    """Validate a denoise level in [0, 1]."""
    if isinstance(denoise, bool) or not isinstance(denoise, (int, float)):
        raise TypeError("denoise must be a float in [0, 1]")
    d = float(denoise)
    if not math.isfinite(d):
        raise ValueError("denoise must be finite")
    if d < 0.0 or d > 1.0:
        raise ValueError("denoise must be in [0, 1], got %r" % (denoise,))
    return d


def _validate_latent(latent):
    """Validate a LATENT dict {"samples": [B,C,H,W]} and return a copy."""
    if not isinstance(latent, dict):
        raise TypeError("latent must be a dict with key 'samples'")
    if "samples" not in latent:
        raise ValueError("latent dict must contain key 'samples'")
    s = latent["samples"]
    if not isinstance(s, torch.Tensor):
        raise TypeError("latent['samples'] must be a torch.Tensor")
    if s.dim() != 4:
        raise ValueError("latent samples must have shape [B, C, H, W], got %s" % (tuple(s.shape),))
    if not torch.isfinite(s).all():
        raise ValueError("latent samples contain non-finite values")
    return s.detach().clone().float()


def _latent_to_image_like(samples):
    """Convert latent [B,C,H,W] to an image-like [B,H,W,C] tensor in 0..1.

    This is a *placeholder* for VAE decode: it takes the first 3 channels
    (or replicates a single channel) and rescales to 0..1.  It is only used
    for the preview node and for tests; a real VAE decode is not available.
    """
    b, c, h, w = samples.shape
    if c == 1:
        rgb = samples.expand(b, 3, h, w)
    elif c >= 3:
        rgb = samples[:, :3, :, :]
    else:
        # c == 2: replicate first channel into 3
        rgb = torch.cat([samples[:, :1], samples[:, :1], samples[:, :1]], dim=1)
    # rescale to 0..1 using per-tensor min/max (safe, deterministic)
    mn = rgb.min()
    mx = rgb.max()
    rng = mx - mn
    if rng > 0:
        rgb = (rgb - mn) / rng
    else:
        rgb = torch.zeros_like(rgb)
    return rgb.permute(0, 2, 3, 1)


def _image_to_latent_like(image):
    """Convert an image [B,H,W,C] to a latent-like [B,C,H,W] tensor.

    Placeholder for VAE encode: takes up to 4 channels (RGB + optional A as
    a 4th channel, or just RGB replicated to 4).  Deterministic, no model.
    """
    b, h, w, c = image.shape
    if c == 1:
        lat = image.unsqueeze(1).expand(b, 4, h, w)
    elif c == 3:
        lat = image.permute(0, 3, 1, 2)
        lat = torch.cat([lat, torch.zeros(b, 1, h, w, device=lat.device)], dim=1)
    elif c == 4:
        lat = image.permute(0, 3, 1, 2)
    else:
        raise ValueError("unsupported image channels %d" % c)
    return lat.contiguous()


def _build_sigma_schedule(denoise, num_steps=20):
    """Build a consistent sigma schedule for the requested denoise level.

    Returns a 1-D tensor of length ``num_steps`` with values in (0, 1] that
    monotonically decrease from ``denoise`` to a small epsilon.  The schedule
    is independent of the base model, which is the whole point of this node.
    """
    d = _validate_denoise(denoise)
    if num_steps < 1:
        raise ValueError("num_steps must be >= 1")
    eps = 1e-4
    if d <= 0.0:
        return torch.zeros(num_steps, dtype=torch.float32)
    # linear-in-sigma schedule from d down to eps
    sigmas = torch.linspace(d, eps, num_steps, dtype=torch.float32)
    return sigmas


def _inject_noise(latent, sigma, seed=0):
    """Inject Gaussian noise at the given sigma level (deterministic).

    Returns a NEW tensor; never modifies the input.
    """
    g = torch.Generator(device="cpu").manual_seed(seed)
    noise = torch.randn(latent.shape, generator=g, dtype=torch.float32)
    return latent + sigma * noise


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

class PSN_Actual_Denoise:
    """Consistent img2img denoise: builds a model-independent sigma schedule
    for the requested denoise level and performs a deterministic latent-space
    blend (placeholder for the full KSampler loop).

    Inputs: image (IMAGE), denoise (FLOAT), model (MODEL), positive
    (CONDITIONING), negative (CONDITIONING), latent (LATENT).
    Outputs: samples (LATENT).

    NOTE: the full diffusion sampler (comfy.sample / comfy.sd) is NOT
    available here; the node performs the core sigma-schedule math and a
    deterministic latent-space blend instead.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "denoise": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent": ("LATENT",),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 32 - 1}),
                "num_steps": ("INT", {"default": 20, "min": 1, "max": 150}),
            },
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("samples",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, denoise, model, positive, negative, latent, seed=0, num_steps=20):
        img = _validate_image(image)
        d = _validate_denoise(denoise)
        lat = _validate_latent(latent)

        # Build the consistent sigma schedule (model-independent).
        sigmas = _build_sigma_schedule(d, num_steps)

        # Placeholder VAE encode of the input image -> latent space.
        img_latent = _image_to_latent_like(img)

        # Match spatial size to the provided latent if needed (nearest interp).
        if img_latent.shape[2:] != lat.shape[2:]:
            img_latent = torch.nn.functional.interpolate(
                img_latent, size=lat.shape[2:], mode="nearest"
            )

        # Blend: at denoise=0 keep the original latent; at denoise=1 fully
        # noise-injected.  We use the *first* sigma (the largest) as the
        # effective noise level for the deterministic blend.
        sigma0 = float(sigmas[0]) if sigmas.numel() > 0 else 0.0
        noisy = _inject_noise(img_latent, sigma0, seed=seed)

        # Consistent blend: out = (1 - d) * original_latent + d * noisy
        # This ensures the denoise level is applied consistently.
        out = (1.0 - d) * lat + d * noisy

        return ({"samples": out.contiguous()},)


class PSN_Denoise_Preview:
    """Preview of how the image will look after denoising, without running
    the full sampler.

    Inputs: image (IMAGE), denoise (FLOAT).
    Outputs: preview (IMAGE).

    The preview blends the input image toward a "denoised" estimate (the
    image itself, acting as a neutral estimate) by the denoise amount, and
    adds a small deterministic noise component scaled by the denoise level
    so the user can see the expected noise injection.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "denoise": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 32 - 1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("preview",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, denoise, seed=0):
        img = _validate_image(image)
        d = _validate_denoise(denoise)

        # Deterministic noise in image space, scaled by denoise.
        g = torch.Generator(device="cpu").manual_seed(seed)
        noise = torch.randn(img.shape, generator=g, dtype=torch.float32) * 0.1

        # Blend: at d=0 -> original; at d=1 -> original + noise (clamped).
        preview = _clamp01(img + d * noise)

        return (preview.contiguous(),)


NODE_CLASS_MAPPINGS = {
    "PSN_Actual_Denoise": PSN_Actual_Denoise,
    "PSN_Denoise_Preview": PSN_Denoise_Preview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Actual_Denoise": "PSN Actual Denoise (Consistent Img2Img)",
    "PSN_Denoise_Preview": "PSN Denoise Preview",
}
