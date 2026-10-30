"""ParametricStudio tensor format conversion utilities.

Converts between ComfyUI IMAGE, LATENT and MASK formats.

Real ComfyUI types used here:
    IMAGE  : float torch tensor [B, H, W, C] in 0..1
    MASK   : float torch tensor [B, H, W] in 0..1
    LATENT : dict {"samples": float torch tensor [B, C, H, W]}

The VAE-dependent nodes (PSN_Image_To_Latent, PSN_Latent_To_Image,
PSN_Mask_To_Latent) accept a VAE object that exposes the standard
ComfyUI ``encode`` / ``decode`` methods.  When no VAE is available
(e.g. in unit tests) a lightweight deterministic pseudo-VAE is used so
that the shape / dtype / range behaviour of the nodes can still be
verified on CPU.
"""

import torch

CAT = "ParametricStudio/TensorFormat"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _s(x):
    """Return the raw tensor from a LATENT dict or a plain tensor."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Wrap a samples tensor in a LATENT dict, preserving other keys."""
    if isinstance(latent, dict):
        d = dict(latent)
        d["samples"] = samples
        return d
    return {"samples": samples}


def _as_image(image):
    """Validate / normalise an IMAGE tensor to [B,H,W,C] float in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    x = image.detach().clone().float()
    if x.dim() == 3:
        # [H, W, C] -> [1, H, W, C]
        x = x.unsqueeze(0)
    if x.dim() != 4:
        raise ValueError("image must have shape [B,H,W,C] (or [H,W,C])")
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("image channel count must be 1, 3 or 4")
    return x


def _as_mask(mask):
    """Validate / normalise a MASK tensor to [B,H,W] float in 0..1."""
    if not isinstance(mask, torch.Tensor):
        raise TypeError("mask must be a torch.Tensor")
    x = mask.detach().clone().float()
    if x.dim() == 2:
        x = x.unsqueeze(0)
    if x.dim() != 3:
        raise ValueError("mask must have shape [B,H,W] (or [H,W])")
    return x


def _as_latent(latent):
    """Validate a LATENT dict and return its samples tensor."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise TypeError("latent must be a dict with a 'samples' key")
    x = latent["samples"]
    if not isinstance(x, torch.Tensor):
        raise TypeError("latent['samples'] must be a torch.Tensor")
    x = x.detach().clone().float()
    if x.dim() != 4:
        raise ValueError("latent samples must have shape [B,C,H,W]")
    return x


def _clamp01(x):
    return x.clamp_(0.0, 1.0)


# ---------------------------------------------------------------------------
# pseudo-VAE (deterministic, CPU, no weights) – used when no real VAE is
# supplied so the nodes remain testable without a ComfyUI runtime.
# ---------------------------------------------------------------------------


class _PseudoVAE:
    """A tiny deterministic stand-in for a ComfyUI VAE.

    encode:  [B,H,W,C] -> [B,C,H//f,W//f]   (average-pool + channel mix)
    decode:  [B,C,H,W] -> [B,H* f,W* f,C]   (upsample + channel mix)

    The operations are invertible enough that a round-trip preserves the
    spatial shape and keeps values in 0..1.
    """

    def __init__(self, latent_channels=4, downscale=8):
        self.latent_channels = latent_channels
        self.downscale = downscale

    def encode(self, image):
        """image: [B,H,W,C] in 0..1 -> samples [B,C,H//f,W//f]."""
        x = _as_image(image)
        b, h, w, c = x.shape
        f = self.downscale
        # pad to a multiple of f
        ph = (f - h % f) % f
        pw = (f - w % f) % f
        if ph or pw:
            x = torch.nn.functional.pad(x, (0, 0, 0, pw, 0, ph))
        h2, w2 = x.shape[1], x.shape[2]
        # average-pool over f x f blocks, then mix channels to latent_channels
        x = x.reshape(b, h2 // f, f, w2 // f, f, c)
        x = x.mean(dim=(2, 4))  # [B, h2//f, w2//f, c]
        x = x.permute(0, 3, 1, 2)  # [B, c, h2//f, w2//f]
        # simple linear mix to latent_channels (deterministic, no weights)
        out = torch.zeros(b, self.latent_channels, h2 // f, w2 // f, dtype=x.dtype)
        for i in range(self.latent_channels):
            # each latent channel is a weighted sum of input channels
            wts = (torch.arange(c, dtype=x.dtype) + 1.0).view(1, c, 1, 1)
            out[:, i] = (x * wts).mean(dim=1)
        return {"samples": out}

    def decode(self, latent):
        """samples [B,C,H,W] -> image [B,H* f,W* f,C] in 0..1."""
        x = _as_latent(latent)
        b, c, h, w = x.shape
        f = self.downscale
        # upsample by f (nearest)
        x = torch.nn.functional.interpolate(
            x, scale_factor=f, mode="nearest"
        )  # [B, C, H*f, W*f]
        x = x.permute(0, 2, 3, 1)  # [B, H*f, W*f, C]
        # mix latent channels back to 3 RGB channels (deterministic)
        out = torch.zeros(b, x.shape[1], x.shape[2], 3, dtype=x.dtype)
        for i in range(3):
            wts = (torch.arange(c, dtype=x.dtype) + 1.0).view(1, 1, 1, c)
            out[:, :, :, i] = (x * wts).mean(dim=3)
        return _clamp01(out)


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


class PSN_Image_To_Latent:
    """Encode an IMAGE into LATENT space using a VAE (or a pseudo-VAE)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "vae": ("MODEL",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, vae):
        img = _as_image(image)
        if vae is None or not hasattr(vae, "encode"):
            vae = _PseudoVAE()
        result = vae.encode(img)
        if isinstance(result, dict):
            samples = result["samples"]
        else:
            samples = result
        return ({"samples": samples},)


class PSN_Latent_To_Image:
    """Decode a LATENT into an IMAGE using a VAE (or a pseudo-VAE)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "vae": ("MODEL",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, vae):
        lat = _as_latent(latent)
        if vae is None or not hasattr(vae, "decode"):
            vae = _PseudoVAE()
        result = vae.decode({"samples": lat})
        if isinstance(result, dict):
            img = result.get("samples", result)
        else:
            img = result
        return (_clamp01(img),)


class PSN_Mask_To_Latent:
    """Convert a MASK into a LATENT representation for inpainting.

    The mask is first expanded to a single-channel IMAGE, then encoded
    with the VAE.  The resulting latent can be fed into an inpainting
    sampler.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
                "vae": ("MODEL",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mask, vae):
        m = _as_mask(mask)
        # expand [B,H,W] -> [B,H,W,1] image
        img = m.unsqueeze(-1)
        if vae is None or not hasattr(vae, "encode"):
            vae = _PseudoVAE()
        result = vae.encode(img)
        if isinstance(result, dict):
            samples = result["samples"]
        else:
            samples = result
        return ({"samples": samples},)


class PSN_Latent_To_Mask:
    """Convert a LATENT back to a MASK (spatial shape of the latent).

    The latent samples are reduced to a single-channel mask by taking
    the mean over the channel dimension and clamping to 0..1.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent):
        x = _as_latent(latent)  # [B, C, H, W]
        m = x.mean(dim=1)  # [B, H, W]
        return (_clamp01(m),)


class PSN_Image_To_Mask:
    """Convert an IMAGE to a MASK by averaging the colour channels."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image):
        x = _as_image(image)  # [B, H, W, C]
        m = x.mean(dim=-1)  # [B, H, W]
        return (_clamp01(m),)


class PSN_Mask_To_Image:
    """Convert a MASK to a single-channel IMAGE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mask):
        m = _as_mask(mask)  # [B, H, W]
        img = m.unsqueeze(-1)  # [B, H, W, 1]
        return (_clamp01(img),)


# ---------------------------------------------------------------------------
# mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Image_To_Latent": PSN_Image_To_Latent,
    "PSN_Latent_To_Image": PSN_Latent_To_Image,
    "PSN_Mask_To_Latent": PSN_Mask_To_Latent,
    "PSN_Latent_To_Mask": PSN_Latent_To_Mask,
    "PSN_Image_To_Mask": PSN_Image_To_Mask,
    "PSN_Mask_To_Image": PSN_Mask_To_Image,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Image_To_Latent": "PSN Image To Latent",
    "PSN_Latent_To_Image": "PSN Latent To Image",
    "PSN_Mask_To_Latent": "PSN Mask To Latent",
    "PSN_Latent_To_Mask": "PSN Latent To Mask",
    "PSN_Image_To_Mask": "PSN Image To Mask",
    "PSN_Mask_To_Image": "PSN Mask To Image",
}
