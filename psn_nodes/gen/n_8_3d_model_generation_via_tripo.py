"""ParametricStudio - Tripo 3D model generation (offline core).

The real Tripo API requires network access and an API key, which are not
available in this sandbox.  This module implements the *core* logic that
torch/stdlib can do:

* PSN_Tripo_Text_To_3D  - validates inputs, builds a deterministic job id
  and a deterministic (offline) model URL from the prompt.
* PSN_Tripo_Image_To_3D - validates inputs, converts the IMAGE tensor to a
  base64-encoded PNG-like payload (pure torch/stdlib), builds a job id and
  a deterministic model URL.

What was NOT implemented: actual network calls to the Tripo API, polling,
and real model generation.  The nodes return a placeholder URL and job id
so the rest of the pipeline can be wired and tested offline.
"""

import base64
import hashlib
import json

import torch

CAT = "ParametricStudio/3D"


def _s(x):
    """Return the tensor inside a LATENT dict, or the tensor itself."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _validate_image(image):
    """Validate an IMAGE tensor: [B,H,W,C] float in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError(f"image must be 4-D [B,H,W,C], got {image.dim()}-D")
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError(f"image channels must be 1, 3 or 4, got {image.shape[-1]}")
    if not (image.dtype == torch.float32 or image.dtype == torch.float16 or image.dtype == torch.float64):
        raise TypeError(f"image must be a float tensor, got {image.dtype}")
    if image.numel() > 0:
        if image.min() < -1e-6 or image.max() > 1 + 1e-6:
            raise ValueError("image values must be in [0, 1]")
    return image


def _image_to_base64_png(image):
    """Encode an IMAGE tensor [B,H,W,C] as a base64 string.

    This is a simplified encoding: we take the first image in the batch,
    convert to uint8, and produce a minimal base64 payload.  It is NOT a
    real PNG; it is a deterministic byte representation suitable for
    offline testing and as a stand-in for the real upload payload.
    """
    img = image[0].clamp(0.0, 1.0)
    if img.shape[-1] == 1:
        img = img.expand(-1, -1, 3)
    elif img.shape[-1] == 4:
        img = img[..., :3]
    # [H, W, C] -> uint8
    u8 = (img * 255.0).round().to(torch.uint8)
    raw = u8.contiguous().view(-1).numpy().tobytes()
    return base64.b64encode(raw).decode("ascii")


def _make_job_id(seed_str):
    """Deterministic job id from a seed string."""
    h = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()
    return "tripo_" + h[:24]


def _make_model_url(job_id, fmt="glb"):
    """Deterministic placeholder model URL."""
    return f"https://models.tripo3d.ai/{job_id}/{job_id}.{fmt}"


class PSN_Tripo_Text_To_3D:
    """Generate a 3D model from a text prompt (offline core, no network)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {"default": ""}),
                "prompt": ("STRING", {"default": "a red cube"}),
                "texture": ("BOOLEAN", {"default": True}),
                "pbr": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("model_url", "job_id")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, api_key, prompt, texture=True, pbr=True):
        if not isinstance(api_key, str):
            raise TypeError("api_key must be a string")
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if not isinstance(texture, bool):
            raise TypeError("texture must be a boolean")
        if not isinstance(pbr, bool):
            raise TypeError("pbr must be a boolean")

        seed = f"text|{prompt.strip().lower()}|texture={texture}|pbr={pbr}"
        job_id = _make_job_id(seed)
        model_url = _make_model_url(job_id)
        return (model_url, job_id)


class PSN_Tripo_Image_To_3D:
    """Generate a 3D model from an input image (offline core, no network)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {"default": ""}),
                "image": ("IMAGE",),
                "texture": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("model_url", "job_id")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, api_key, image, texture=True):
        if not isinstance(api_key, str):
            raise TypeError("api_key must be a string")
        if not isinstance(texture, bool):
            raise TypeError("texture must be a boolean")

        img = _validate_image(image)
        b64 = _image_to_base64_png(img)
        seed = f"image|{b64[:64]}|texture={texture}"
        job_id = _make_job_id(seed)
        model_url = _make_model_url(job_id)
        return (model_url, job_id)


NODE_CLASS_MAPPINGS = {
    "PSN_Tripo_Text_To_3D": PSN_Tripo_Text_To_3D,
    "PSN_Tripo_Image_To_3D": PSN_Tripo_Image_To_3D,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Tripo_Text_To_3D": "Tripo Text to 3D",
    "PSN_Tripo_Image_To_3D": "Tripo Image to 3D",
}
