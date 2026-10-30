"""ParametricStudio: automated aspect-ratio cropping for SDXL/Flux.

PSN_Auto_Aspect_Crop
    Crops an IMAGE tensor [B,H,W,C] (float 0..1) to a target aspect ratio
    (1:1, 16:9, 9:16, 4:3, 3:4 or custom WxH) using a center, face or
    smart crop strategy.  Pure torch (CPU) implementation: no PIL, no
    external face model.  "face" mode uses a lightweight skin-tone / dark
    blob heuristic and falls back to center when nothing is found.
"""

import torch

CAT = "ParametricStudio/Image"

_RATIOS = {
    "1:1": (1.0, 1.0),
    "16:9": (16.0, 9.0),
    "9:16": (9.0, 16.0),
    "4:3": (4.0, 3.0),
    "3:4": (3.0, 4.0),
}


def _s(x):
    """Extract the tensor from a ComfyUI LATENT/IMAGE/MASK wrapper."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(orig, tensor):
    """Re-wrap a tensor in the same container type as the input."""
    if isinstance(orig, dict):
        return {"samples": tensor}
    return tensor


def _round8(v):
    """Round to the nearest multiple of 8 (SDXL/Flux friendly)."""
    v = int(v)
    if v < 8:
        return 8
    return max(8, (v // 8) * 8)


def _target_wh(h, w, ratio, custom_w, custom_h):
    """Compute the target (width, height) for the requested ratio.

    The crop keeps the larger dimension of the source and derives the
    other from the ratio, then rounds both to multiples of 8.  For
    "custom" the user-supplied W/H are used directly (also rounded to 8).
    """
    if ratio == "custom":
        tw = _round8(int(custom_w))
        th = _round8(int(custom_h))
        return tw, th
    rw, rh = _RATIOS[ratio]
    # Keep the longer side of the source, derive the other from the ratio.
    if w >= h:
        tw = w
        th = int(round(w * rh / rw))
    else:
        th = h
        tw = int(round(h * rw / rh))
    return _round8(tw), _round8(th)


def _face_center(img):
    """Very cheap face heuristic on a single image [H,W,C] in 0..1.

    Looks for a skin-tone-ish region in the upper half of the image and
    returns (cx, cy) in pixels, or None if nothing plausible is found.
    """
    h, w, _ = img.shape
    if h < 16 or w < 16:
        return None
    r = img[..., 0].float()
    g = img[..., 1].float()
    b = img[..., 2].float()
    # Rough skin-tone mask: red dominant, not too dark, not too saturated blue.
    skin = (r > 0.35) & (r > g) & (g > b * 0.8) & (r < 0.98)
    # Restrict to the upper 60% of the frame where faces usually are.
    cut = max(1, int(h * 0.6))
    skin[cut:, :] = False
    n = int(skin.sum().item())
    if n < max(16, int(h * w * 0.002)):
        return None
    ys, xs = torch.nonzero(skin, as_tuple=True)
    cy = float(ys.float().mean().item())
    cx = float(xs.float().mean().item())
    return cx, cy


def _smart_center(img):
    """Pick a crop center biased toward the most 'interesting' (high
    variance / edge energy) region of the image.  Returns (cx, cy)."""
    h, w, _ = img.shape
    if h < 8 or w < 8:
        return w / 2.0, h / 2.0
    gray = img.float().mean(dim=-1)
    # Downsample to a small grid and measure local variance as a proxy
    # for visual interest.
    gh, gw = max(1, h // 16), max(1, w // 16)
    small = torch.nn.functional.interpolate(
        gray.unsqueeze(0).unsqueeze(0), size=(gh, gw), mode="area"
    ).squeeze()
    # Edge energy: mean absolute difference to neighbours.
    if gh > 1 and gw > 1:
        vert = (small[1:, :] - small[:-1, :]).abs()  # [gh-1, gw]
        horiz = (small[:, 1:] - small[:, :-1]).abs()  # [gh, gw-1]
        # Average the two into a common [gh-1, gw-1] grid.
        energy = (vert[:, :-1] + horiz[:-1, :]) / 2.0
    else:
        energy = small
    idx = int(energy.argmax().item())
    gy = (idx // max(1, gw)) + 0.5
    gx = (idx % max(1, gw)) + 0.5
    cy = gy * (h / gh)
    cx = gx * (w / gw)
    return cx, cy


def _crop_box(h, w, tw, th, cx, cy):
    """Clamp a crop box of size (tw, th) centered at (cx, cy) inside (w, h)."""
    x0 = int(round(cx - tw / 2.0))
    y0 = int(round(cy - th / 2.0))
    x0 = max(0, min(x0, w - tw))
    y0 = max(0, min(y0, h - th))
    return x0, y0, x0 + tw, y0 + th


class PSN_Auto_Aspect_Crop:
    """Crop an image to a target SDXL/Flux aspect ratio (center/face/smart)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "target_ratio": (list(_RATIOS.keys()) + ["custom"],),
                "crop_mode": (["center", "face", "smart"],),
            },
            "optional": {
                "custom_w": ("INT", {"default": 1024, "min": 8, "max": 8192}),
                "custom_h": ("INT", {"default": 1024, "min": 8, "max": 8192}),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("cropped_image", "original_width", "original_height")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, target_ratio, crop_mode, custom_w=1024, custom_h=1024):
        img = _s(image)
        if not torch.is_tensor(img):
            raise TypeError("image must be a torch tensor")
        if img.dim() != 4 or img.shape[-1] < 1:
            raise ValueError("image must have shape [B,H,W,C]")
        if target_ratio not in _RATIOS and target_ratio != "custom":
            raise ValueError("unknown target_ratio: %r" % (target_ratio,))
        if crop_mode not in ("center", "face", "smart"):
            raise ValueError("unknown crop_mode: %r" % (crop_mode,))

        b, h, w, c = img.shape
        tw, th = _target_wh(h, w, target_ratio, custom_w, custom_h)

        # The crop cannot be larger than the source; shrink target if needed.
        if tw > w or th > h:
            scale = min(w / float(tw), h / float(th))
            tw = _round8(tw * scale)
            th = _round8(th * scale)
            tw = max(8, min(tw, w))
            th = max(8, min(th, h))

        out = torch.empty((b, th, tw, c), dtype=img.dtype, device=img.device)
        for i in range(b):
            frame = img[i]
            if crop_mode == "face":
                fc = _face_center(frame)
                cx, cy = fc if fc is not None else (w / 2.0, h / 2.0)
            elif crop_mode == "smart":
                cx, cy = _smart_center(frame)
            else:
                cx, cy = w / 2.0, h / 2.0
            x0, y0, x1, y1 = _crop_box(h, w, tw, th, cx, cy)
            out[i] = frame[y0:y1, x0:x1]

        return (_out(image, out), int(w), int(h))


NODE_CLASS_MAPPINGS = {"PSN_Auto_Aspect_Crop": PSN_Auto_Aspect_Crop}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Auto_Aspect_Crop": "Auto Aspect Ratio Crop (SDXL/Flux)"}
