"""Conditional Upscaling Pipeline for ComfyUI (ParametricStudio).

Nodes:
  - PSN_Quality_Gate: compares a quality score against a threshold and emits a boolean flag.
  - PSN_Upscale_Switch: applies a 2x bicubic upscale (torch) when the flag is True, otherwise passes the image through unchanged.

NOTE: A real upscaler model (MODEL input) is accepted for interface compatibility but the actual
upscaling is done with torch.nn.functional.interpolate (bicubic, 2x).  No external model weights
are loaded.
"""

import torch
import torch.nn.functional as F

CAT = "ParametricStudio/Upscaling"


def _as_image(image):
    """Validate and return a float tensor [B,H,W,C] in 0..1.  Never mutates the input."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image must be 4-D [B,H,W,C], got %d-D" % image.dim())
    return image.float().clone()


class PSN_Quality_Gate:
    """Emit needs_upscale=True when quality_score < threshold."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "quality_score": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "IMAGE")
    RETURN_NAMES = ("needs_upscale", "image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, quality_score, threshold):
        img = _as_image(image)
        needs = bool(quality_score < threshold)
        return (needs, img)


class PSN_Upscale_Switch:
    """Upscale image 2x (bicubic) when flag is True, otherwise pass through unchanged."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "flag": ("BOOLEAN",),
                "upscaler_model": ("MODEL",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("final_image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, flag, upscaler_model):
        img = _as_image(image)
        if not flag:
            return (img,)
        # 2x bicubic upscale: [B,H,W,C] -> [B,2H,2W,C]
        b, h, w, c = img.shape
        # rearrange to [B,C,H,W] for interpolate
        x = img.permute(0, 3, 1, 2)
        x = F.interpolate(x, size=(h * 2, w * 2), mode="bicubic", align_corners=False)
        x = x.permute(0, 2, 3, 1).clamp(0.0, 1.0)
        return (x,)


NODE_CLASS_MAPPINGS = {
    "PSN_Quality_Gate": PSN_Quality_Gate,
    "PSN_Upscale_Switch": PSN_Upscale_Switch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Quality_Gate": "Quality Gate",
    "PSN_Upscale_Switch": "Upscale Switch",
}
