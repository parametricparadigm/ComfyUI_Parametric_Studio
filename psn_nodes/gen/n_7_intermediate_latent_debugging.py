"""PSN intermediate latent debugging nodes.

Provides PSN_Peek_Sampler (a CPU sampling loop that decodes the latent at
selected steps) and PSN_Peek_Visualizer (arranges peek images in a grid).

NOTE: real ComfyUI MODEL/CONDITIONING/VAE integration (comfy.sample, comfy.sd)
is NOT implemented because those libraries are unavailable in this workspace.
The sampler accepts model/positive/negative inputs but ignores them; denoising
and decoding are done by pluggable callables that default to deterministic
synthetic implementations so the node is fully testable on CPU with torch.
"""

import torch

CAT = "ParametricStudio/Debug"


def _latent_samples(latent):
    """Return the 'samples' tensor from a LATENT dict, validating shape."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise ValueError("latent must be a dict with a 'samples' tensor")
    x = latent["samples"]
    if not torch.is_tensor(x):
        raise ValueError("latent['samples'] must be a torch tensor")
    if x.dim() != 4:
        raise ValueError("latent samples must be 4D [B,C,H,W], got %dD" % x.dim())
    return x


def _out(latent, samples):
    """Build a new LATENT dict without mutating the input."""
    return {"samples": samples}


def _default_denoise(model, conditioning, x, step, total_steps, cfg):
    """Deterministic synthetic denoiser.

    Produces a plausible denoised latent: moves x toward a fixed target
    (zeros) by a fraction that grows with the step, so the latent visibly
    converges over the loop. Pure function of its inputs.
    """
    frac = (step + 1) / float(total_steps)
    target = torch.zeros_like(x)
    return x + (target - x) * frac


def _default_decode(samples):
    """Deterministic synthetic VAE decode: latent [B,C,H,W] -> image [B,H,W,C].

    Averages the latent channels into a single grayscale image scaled to 0..1.
    """
    x = samples
    if x.dim() != 4:
        raise ValueError("decode expects 4D [B,C,H,W] tensor")
    gray = x.mean(dim=1, keepdim=True)  # [B,1,H,W]
    # Map roughly to 0..1 via a tanh-like squash of the mean magnitude.
    img = torch.sigmoid(gray)  # [B,1,H,W]
    img = img.repeat(1, 1, 1, 3)  # [B,1,H,W] -> [B,1,H,W,3]? no, repeat on last dim
    # Build [B,H,W,3] properly:
    b, c, h, w = img.shape
    img = img.permute(0, 2, 3, 1)  # [B,H,W,C]
    return img


def _parse_peek_steps(peek_steps, total_steps):
    """Parse a comma-separated string of 1-based step numbers.

    Returns a sorted list of unique ints in [1, total_steps].
    """
    if not isinstance(peek_steps, str):
        raise ValueError("peek_steps must be a comma-separated string")
    steps = []
    for tok in peek_steps.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            v = int(tok)
        except ValueError:
            raise ValueError("peek_steps contains non-integer token: %r" % tok)
        if v < 1 or v > total_steps:
            raise ValueError("peek step %d out of range 1..%d" % (v, total_steps))
        steps.append(v)
    return sorted(set(steps))


class PSN_Peek_Sampler:
    """CPU sampling loop that decodes the latent at selected steps (debug peek)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent": ("LATENT",),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**63 - 1}),
                "steps": ("INT", {"default": 10, "min": 1, "max": 1000}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0}),
                "sampler_name": ("euler",),
                "scheduler": ("normal",),
                "peek_steps": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("LATENT", "IMAGE")
    RETURN_NAMES = ("samples", "peeks")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, positive, negative, latent, seed, steps, cfg,
            sampler_name="euler", scheduler="normal", peek_steps="",
            denoise_fn=None, decode_fn=None):
        x = _latent_samples(latent).clone()
        if steps < 1:
            raise ValueError("steps must be >= 1")
        peek_set = _parse_peek_steps(peek_steps, steps) if peek_steps else []

        if denoise_fn is None:
            denoise_fn = _default_denoise
        if decode_fn is None:
            decode_fn = _default_decode

        peeks = []
        for step in range(1, steps + 1):
            x = denoise_fn(model, (positive, negative), x, step, steps, cfg)
            if step in peek_set:
                img = decode_fn(x)
                peeks.append(img)

        if peeks:
            peeks_out = torch.cat(peeks, dim=0)  # [N,H,W,C]
        else:
            # Empty image tensor with the spatial size of the latent.
            b, c, h, w = x.shape
            peeks_out = torch.zeros((0, h, w, 3), dtype=x.dtype)

        return (_out(latent, x), peeks_out)


class PSN_Peek_Visualizer:
    """Arrange peeked images [N,H,W,C] into a single grid image."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "peeks": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("grid",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, peeks):
        if not torch.is_tensor(peeks):
            raise ValueError("peeks must be a torch tensor")
        if peeks.dim() != 4:
            raise ValueError("peeks must be 4D [N,H,W,C], got %dD" % peeks.dim())
        n, h, w, c = peeks.shape
        if n == 0:
            raise ValueError("peeks is empty; nothing to visualize")
        if c < 1:
            raise ValueError("peeks must have at least 1 channel")
        # Lay out in a single row: grid is [1, h, n*w, c].
        grid = peeks.reshape(1, h, n * w, c)
        return (grid,)


NODE_CLASS_MAPPINGS = {
    "PSN_Peek_Sampler": PSN_Peek_Sampler,
    "PSN_Peek_Visualizer": PSN_Peek_Visualizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Peek_Sampler": "PSN Peek Sampler",
    "PSN_Peek_Visualizer": "PSN Peek Visualizer",
}
