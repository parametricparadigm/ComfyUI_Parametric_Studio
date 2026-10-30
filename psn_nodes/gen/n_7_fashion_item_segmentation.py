"""PSN_FashionItemSegmenter: heuristic fashion-item segmentation.

The spec calls for a specialized fashion segmentation model (e.g. an ONNX
model).  That model is not available in this environment, so this module
implements the *core* of the idea using only torch/stdlib: a color/region
heuristic that segments the most salient region of the image and reports a
bounding box.  The mask and bbox are returned in the standard ComfyUI
formats (MASK = [B,H,W] float tensor in 0..1, BBOX = list of dicts).
"""

import torch

CAT = "ParametricStudio/Segmentation"

# Heuristic color profiles per item type.  Each profile is a dict with:
#   "hue_lo", "hue_hi"  – HSV hue range (0..1) that is considered "in range"
#   "sat_min"           – minimum saturation (0..1)
#   "val_min"           – minimum value (0..1)
# These are deliberately broad so that a synthetic test image with a
# saturated red shoe, a brown bag, or a colourful dress will be picked up.
_PROFILES = {
    "shoes":   {"hue_lo": 0.0,  "hue_hi": 0.12, "sat_min": 0.35, "val_min": 0.25},
    "bags":    {"hue_lo": 0.05, "hue_hi": 0.18, "sat_min": 0.25, "val_min": 0.20},
    "dresses": {"hue_lo": 0.0,  "hue_hi": 1.0,  "sat_min": 0.30, "val_min": 0.25},
    "all":     {"hue_lo": 0.0,  "hue_hi": 1.0,  "sat_min": 0.25, "val_min": 0.20},
}


def _rgb_to_hsv(img):
    """Convert an RGB tensor [B,H,W,3] in 0..1 to HSV [B,H,W,3] in 0..1."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    cmax = torch.max(torch.max(r, g), b)
    cmin = torch.min(torch.min(r, g), b)
    delta = cmax - cmin

    # Hue
    hue = torch.zeros_like(cmax)
    mask_r = (cmax == r) & (delta > 0)
    mask_g = (cmax == g) & (delta > 0)
    mask_b = (cmax == b) & (delta > 0)
    hue = torch.where(mask_r, ((g - b) / delta).remainder(6.0), hue)
    hue = torch.where(mask_g, ((b - r) / delta + 2.0), hue)
    hue = torch.where(mask_b, ((r - g) / delta + 4.0), hue)
    hue = (hue / 6.0).remainder(1.0)

    # Saturation
    sat = torch.where(cmax > 0, delta / cmax, torch.zeros_like(cmax))

    # Value
    val = cmax

    return torch.stack([hue, sat, val], dim=-1)


def _bbox_from_mask(mask):
    """Return (x0, y0, x1, y1) for the first (only) batch element, or None."""
    ys, xs = torch.nonzero(mask > 0.5, as_tuple=True)
    if xs.numel() == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


class PSN_FashionItemSegmenter:
    """Heuristic fashion-item segmentation (shoes / bags / dresses / all).

    Returns a binary MASK and a list of bounding-box dicts.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "item_type": (["shoes", "bags", "dresses", "all"],),
            }
        }

    RETURN_TYPES = ("MASK", "BBOX")
    RETURN_NAMES = ("mask", "bounding_boxes")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, item_type):
        # --- validate image ---
        if not isinstance(image, torch.Tensor):
            raise ValueError("image must be a torch.Tensor")
        if image.dim() != 4 or image.shape[-1] != 3:
            raise ValueError("image must have shape [B, H, W, 3]")
        if image.shape[1] < 1 or image.shape[2] < 1:
            raise ValueError("image H and W must be >= 1")

        if item_type not in _PROFILES:
            raise ValueError(f"item_type must be one of {list(_PROFILES)}")

        img = image.float().clamp(0.0, 1.0)
        B, H, W, _ = img.shape

        hsv = _rgb_to_hsv(img)
        hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]

        prof = _PROFILES[item_type]
        hue_lo, hue_hi = prof["hue_lo"], prof["hue_hi"]

        # Hue range check (handles wrap-around when hue_lo > hue_hi, though
        # our profiles never do; kept for robustness).
        if hue_lo <= hue_hi:
            hue_ok = (hue >= hue_lo) & (hue <= hue_hi)
        else:
            hue_ok = (hue >= hue_lo) | (hue <= hue_hi)

        in_range = hue_ok & (sat >= prof["sat_min"]) & (val >= prof["val_min"])

        # Build per-batch mask
        masks = []
        bboxes = []
        for i in range(B):
            m = in_range[i].float()  # [H, W]
            masks.append(m)
            bb = _bbox_from_mask(m)
            if bb is not None:
                x0, y0, x1, y1 = bb
                bboxes.append({
                    "x": x0, "y": y0,
                    "width": x1 - x0 + 1, "height": y1 - y0 + 1,
                    "item_type": item_type,
                })
            else:
                bboxes.append({"x": 0, "y": 0, "width": 0, "height": 0,
                               "item_type": item_type})

        mask_out = torch.stack(masks, dim=0)  # [B, H, W]
        return (mask_out, bboxes)


NODE_CLASS_MAPPINGS = {
    "PSN_FashionItemSegmenter": PSN_FashionItemSegmenter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FashionItemSegmenter": "Fashion Item Segmenter (ParametricStudio)",
}
