"""PSN_Batch_Resize_Pad: resize a batch of images to fit a target box and pad to uniform size.

ComfyUI custom node (ParametricStudio). Pure torch CPU implementation (no PIL needed):
- each image is scaled with bilinear interpolation to fit inside target_width x target_height
  while preserving aspect ratio;
- the result is centered on a canvas of exactly target_width x target_height filled with
  the requested pad color.

IMAGE tensors are float [B, H, W, C] in 0..1. Inputs are never modified in place.
"""

import torch

CAT = "ParametricStudio/Preprocessing"


def _as_image_tensor(images):
    """Validate and return a float32 CPU tensor of shape [B, H, W, C]."""
    if not isinstance(images, torch.Tensor):
        raise TypeError("images must be a torch.Tensor")
    x = images.detach().to(dtype=torch.float32, device="cpu")
    if x.dim() != 4:
        raise ValueError(f"images must be a 4D tensor [B,H,W,C], got {x.dim()}D")
    b, h, w, c = x.shape
    if b < 1 or h < 1 or w < 1 or c < 1:
        raise ValueError(f"images must have positive dimensions, got {tuple(x.shape)}")
    return x


def _parse_pad_color(pad_color):
    """Parse a color spec into a float tensor [C] in 0..1.

    Accepted forms:
      - "#RRGGBB" / "#RGB"
      - "R,G,B" (integers 0..255 or floats 0..1)
      - a single number (grayscale, 0..255 or 0..1)
    """
    s = str(pad_color).strip()
    if s.startswith("#"):
        hexs = s[1:]
        if len(hexs) == 3:
            hexs = "".join(ch * 2 for ch in hexs)
        if len(hexs) != 6:
            raise ValueError(f"invalid hex color: {pad_color!r}")
        try:
            r = int(hexs[0:2], 16)
            g = int(hexs[2:4], 16)
            b = int(hexs[4:6], 16)
        except ValueError:
            raise ValueError(f"invalid hex color: {pad_color!r}")
        return torch.tensor([r / 255.0, g / 255.0, b / 255.0], dtype=torch.float32)

    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    if not parts:
        raise ValueError(f"invalid pad color: {pad_color!r}")
    vals = []
    for p in parts:
        try:
            v = float(p)
        except ValueError:
            raise ValueError(f"invalid pad color component: {p!r}")
        if v < 0.0 or v > 255.0:
            raise ValueError(f"pad color component out of range: {v}")
        vals.append(v)
    if len(vals) == 1:
        v = vals[0]
        v = v / 255.0 if v > 1.0 else v
        return torch.tensor([v, v, v], dtype=torch.float32)
    if len(vals) == 3:
        out = []
        for v in vals:
            out.append(v / 255.0 if v > 1.0 else v)
        return torch.tensor(out, dtype=torch.float32)
    raise ValueError(f"pad color must have 1 or 3 components, got {len(vals)}")


def _resize_fit(img, tw, th):
    """Resize a single [H, W, C] image to fit inside tw x th, preserving aspect ratio.

    Returns (resized_tensor [h, w, C], new_h, new_w).
    """
    h, w, c = img.shape
    if h == th and w == tw:
        return img, h, w
    scale = min(tw / float(w), th / float(h))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    # img: [H, W, C] -> [1, C, H, W] for interpolate
    x = img.permute(2, 0, 1).unsqueeze(0)
    x = torch.nn.functional.interpolate(
        x, size=(new_h, new_w), mode="bilinear", align_corners=False
    )
    x = x.squeeze(0).permute(1, 2, 0)
    return x, new_h, new_w


class PSN_Batch_Resize_Pad:
    """Resize each image in a batch to fit a target box (aspect preserved) and pad to uniform size."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "target_width": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "target_height": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "pad_color": ("STRING", {"default": "#000000"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("processed_images",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, images, target_width, target_height, pad_color):
        x = _as_image_tensor(images)
        tw = int(target_width)
        th = int(target_height)
        if tw < 1 or th < 1:
            raise ValueError("target_width and target_height must be >= 1")
        pad = _parse_pad_color(pad_color)

        b, h, w, c = x.shape
        out = torch.empty((b, th, tw, c), dtype=torch.float32)

        for i in range(b):
            img = x[i]  # [H, W, C]
            resized, rh, rw = _resize_fit(img, tw, th)
            # pad color for this image's channel count
            if pad.numel() == c:
                fill = pad
            elif c == 1:
                fill = pad[:1]
            else:
                # broadcast 3-channel pad to c channels (e.g. RGBA)
                fill = pad[: min(3, c)]
                if c > 3:
                    extra = torch.ones(c - 3, dtype=torch.float32)
                    fill = torch.cat([fill, extra])
            canvas = fill.view(1, 1, c).expand(1, th, tw, c).clone()
            top = (th - rh) // 2
            left = (tw - rw) // 2
            canvas[:, top:top + rh, left:left + rw, :] = resized
            out[i] = canvas

        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_Batch_Resize_Pad": PSN_Batch_Resize_Pad,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Batch_Resize_Pad": "Batch Resize & Pad for Datasets",
}
