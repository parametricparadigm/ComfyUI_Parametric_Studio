"""ParametricStudio - Latent Inpainting for Local Edits.

Two ComfyUI nodes that prepare and finish mask-constrained inpainting in
latent space so that only the masked region has to be regenerated:

* PSN_Latent_Inpaint_Encode: encodes an IMAGE + MASK pair into an inpaint
  latent (image latent with the masked region zeroed) plus a downsampled
  MASK_LATENT that matches the latent grid.
* PSN_Latent_Inpaint_Decode: decodes the (sampled) inpaint latent and
  blends the edited region back into the original image using the mask.

The nodes are pure torch (CPU friendly) and never modify their inputs.
"""

import torch

CAT = "ParametricStudio/Inpainting"


def _as_tensor(x):
    if isinstance(x, torch.Tensor):
        return x
    raise TypeError("expected a torch.Tensor")


def _image_tensor(image):
    """Validate an IMAGE tensor: float [B,H,W,C] in 0..1."""
    t = _as_tensor(image)
    if t.dim() != 4:
        raise ValueError(f"IMAGE must be [B,H,W,C], got shape {tuple(t.shape)}")
    if t.shape[-1] not in (1, 3, 4):
        raise ValueError(f"IMAGE channels must be 1/3/4, got {t.shape[-1]}")
    if not t.is_floating_point():
        raise TypeError("IMAGE must be a float tensor")
    if t.min() < -1e-6 or t.max() > 1 + 1e-6:
        raise ValueError("IMAGE values must be in 0..1")
    return t


def _mask_tensor(mask):
    """Validate a MASK tensor: float [B,H,W] in 0..1 (1 = inpaint region)."""
    t = _as_tensor(mask)
    if t.dim() != 3:
        raise ValueError(f"MASK must be [B,H,W], got shape {tuple(t.shape)}")
    if not t.is_floating_point():
        raise TypeError("MASK must be a float tensor")
    if t.min() < -1e-6 or t.max() > 1 + 1e-6:
        raise ValueError("MASK values must be in 0..1")
    return t


def _latent_dict(latent):
    """Validate a LATENT dict with a float [B,C,H,W] 'samples' tensor."""
    if not isinstance(latent, dict):
        raise TypeError("LATENT must be a dict with a 'samples' tensor")
    if "samples" not in latent:
        raise ValueError("LATENT dict must contain a 'samples' key")
    t = _as_tensor(latent["samples"])
    if t.dim() != 4:
        raise ValueError(f"LATENT samples must be [B,C,H,W], got {tuple(t.shape)}")
    if not t.is_floating_point():
        raise TypeError("LATENT samples must be a float tensor")
    return t


def _clone_latent(latent, samples):
    """Return a new LATENT dict sharing nothing with the input."""
    out = {k: (v.clone() if isinstance(v, torch.Tensor) else v) for k, v in latent.items()}
    out["samples"] = samples
    return out


def _gaussian_blur(mask, radius):
    """Separable Gaussian blur of a [B,H,W] mask (no in-place ops)."""
    if radius <= 0:
        return mask
    r = int(radius)
    sigma = max(r / 2.0, 0.5)
    half = r
    coords = torch.arange(-half, half + 1, dtype=torch.float32, device=mask.device)
    kernel = torch.exp(-(coords ** 2) / (2.0 * sigma * sigma))
    kernel = kernel / kernel.sum()
    # pad then convolve along H and W separately (1x1 conv per axis)
    m = mask.unsqueeze(1)  # [B,1,H,W]
    m = torch.nn.functional.pad(m, (half, half, 0, 0), mode="replicate")
    m = torch.nn.functional.conv2d(m, kernel.view(1, 1, 1, -1), groups=1)
    m = torch.nn.functional.pad(m, (0, 0, half, half), mode="replicate")
    m = torch.nn.functional.conv2d(m, kernel.view(1, 1, -1, 1), groups=1)
    return m.squeeze(1)


def _downsample_mask(mask, target_h, target_w):
    """Average-pool a [B,H,W] mask to [B,target_h,target_w] (no in-place)."""
    m = mask.unsqueeze(1)
    m = torch.nn.functional.interpolate(m, size=(target_h, target_w), mode="area")
    return m.squeeze(1)


def _upsample_mask(mask, target_h, target_w):
    """Bilinear-upsample a [B,H,W] mask to [B,target_h,target_w]."""
    m = mask.unsqueeze(1)
    m = torch.nn.functional.interpolate(m, size=(target_h, target_w), mode="bilinear", align_corners=False)
    return m.squeeze(1)


class PSN_Latent_Inpaint_Encode:
    """Encode IMAGE + MASK into an inpaint latent and a matching mask latent.

    The image is encoded with the VAE; the masked region of the latent is
    zeroed so the sampler only has to fill it in. The mask is blurred and
    downsampled to the latent grid.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "vae": ("VAE",),
                "mask_blur": ("INT", {"default": 4, "min": 0, "max": 64}),
            }
        }

    RETURN_TYPES = ("LATENT", "MASK_LATENT")
    RETURN_NAMES = ("LATENT", "MASK_LATENT")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, mask, vae, mask_blur):
        img = _image_tensor(image)
        msk = _mask_tensor(mask)
        if img.shape[0] != msk.shape[0]:
            raise ValueError(f"batch mismatch: image {img.shape[0]} vs mask {msk.shape[0]}")
        if img.shape[1] != msk.shape[1] or img.shape[2] != msk.shape[2]:
            raise ValueError(f"size mismatch: image {tuple(img.shape[1:3])} vs mask {tuple(msk.shape[1:])}")

        blurred = _gaussian_blur(msk, int(mask_blur))

        # Encode the image with the VAE (ComfyUI VAE exposes .encode).
        latent = vae.encode(img)
        samples = _latent_dict(latent)
        samples = samples.clone()  # never mutate the VAE's output in place

        # Downsample the blurred mask to the latent grid.
        mask_latent = _downsample_mask(blurred, samples.shape[2], samples.shape[3])

        # Zero out the masked region of the latent (1 = inpaint).
        weight = mask_latent.unsqueeze(1)  # [B,1,lh,lw]
        inpaint_samples = samples * (1.0 - weight)

        return (_clone_latent(latent, inpaint_samples), mask_latent)


class PSN_Latent_Inpaint_Decode:
    """Decode an inpaint latent and blend the edited region into the original.

    The latent is decoded with the VAE; the result is blended with the
    original image using the (upsampled) mask latent so that only the
    inpainted region changes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "mask_latent": ("MASK_LATENT",),
                "vae": ("VAE",),
                "original_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, mask_latent, vae, original_image):
        samples = _latent_dict(latent)
        msk = _as_tensor(mask_latent)
        if msk.dim() != 3:
            raise ValueError(f"MASK_LATENT must be [B,H,W], got {tuple(msk.shape)}")
        if msk.shape[0] != samples.shape[0]:
            raise ValueError(f"batch mismatch: latent {samples.shape[0]} vs mask {msk.shape[0]}")
        orig = _image_tensor(original_image)
        if orig.shape[0] != samples.shape[0]:
            raise ValueError(f"batch mismatch: image {orig.shape[0]} vs latent {samples.shape[0]}")

        decoded = vae.decode({"samples": samples})
        dec_img = _image_tensor(decoded)

        # Upsample the mask latent back to image resolution.
        msk_img = _upsample_mask(msk, dec_img.shape[1], dec_img.shape[2])

        # Blend: out = orig * (1 - m) + decoded * m
        w = msk_img.unsqueeze(-1)  # [B,H,W,1]
        out = orig * (1.0 - w) + dec_img * w
        out = torch.clamp(out, 0.0, 1.0)
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_Latent_Inpaint_Encode": PSN_Latent_Inpaint_Encode,
    "PSN_Latent_Inpaint_Decode": PSN_Latent_Inpaint_Decode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Latent_Inpaint_Encode": "PSN Latent Inpaint Encode",
    "PSN_Latent_Inpaint_Decode": "PSN Latent Inpaint Decode",
}
