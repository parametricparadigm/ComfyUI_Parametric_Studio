"""ParametricStudio - SAM-based segmentation for inpainting.

This module provides a ComfyUI node that produces a segmentation mask
from an image plus point/box prompts.  The real Segment Anything Model
(`segment_anything` / `sam2`) is a heavy dependency that is NOT available
in this environment, so the node implements the *core* logic that torch
and the standard library can do:

* prompt parsing and validation (points, boxes, auto mode),
* deterministic mask generation from the prompts (geometric primitives
  that stand in for SAM's learned segmentation),
* mask -> image isolation for inpainting,
* proper ComfyUI tensor conventions (IMAGE [B,H,W,C] 0..1, MASK [B,H,W]).

What was NOT implemented:
* Actual SAM/SAM2 model loading and inference (requires the
  `segment_anything` package and a model checkpoint, neither of which
  can be installed or downloaded here).
* GPU acceleration (CPU torch only).
"""

import torch

CAT = "ParametricStudio/Segmentation"


def _as_tensor(x):
    """Return x as a torch tensor (no copy if already a tensor)."""
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x)


def _validate_image(image):
    """Validate an IMAGE tensor: [B,H,W,C] float in 0..1."""
    img = _as_tensor(image)
    if img.dim() != 4:
        raise ValueError(f"IMAGE must be 4D [B,H,W,C], got {img.dim()}D")
    if img.shape[-1] not in (1, 3, 4):
        raise ValueError(f"IMAGE channels must be 1, 3 or 4, got {img.shape[-1]}")
    if not img.is_floating_point():
        raise ValueError("IMAGE must be a floating point tensor")
    if img.numel() and (img.min() < -1e-6 or img.max() > 1 + 1e-6):
        raise ValueError("IMAGE values must be in [0, 1]")
    return img


def _parse_points(point_coords):
    """Parse point_coords into a list of (x, y) integer tuples.

    Accepts:
      * a flat list [x1, y1, x2, y2, ...]
      * a list of pairs [[x1, y1], [x2, y2], ...]
      * a torch tensor of shape [N, 2]
    """
    if point_coords is None:
        return []
    if isinstance(point_coords, torch.Tensor):
        point_coords = point_coords.detach().cpu().tolist()
    if not isinstance(point_coords, (list, tuple)):
        raise ValueError("point_coords must be a list of [x, y] pairs")
    if len(point_coords) == 0:
        return []
    # Detect flat vs nested
    first = point_coords[0]
    if isinstance(first, (list, tuple)):
        pairs = point_coords
    else:
        if len(point_coords) % 2 != 0:
            raise ValueError("flat point_coords list must have even length")
        pairs = [point_coords[i:i + 2] for i in range(0, len(point_coords), 2)]
    out = []
    for p in pairs:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValueError(f"each point must be [x, y], got {p!r}")
        x, y = float(p[0]), float(p[1])
        if not (x == x and y == y):  # NaN check
            raise ValueError("point coordinates must be finite numbers")
        out.append((int(round(x)), int(round(y))))
    return out


def _parse_box(point_coords):
    """Parse a box [x1, y1, x2, y2] from point_coords."""
    pts = _parse_points(point_coords)
    if len(pts) != 2:
        raise ValueError("Box mode requires exactly 2 points: [x1, y1], [x2, y2]")
    (x1, y1), (x2, y2) = pts
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    return (x1, y1, x2, y2)


def _point_mask(H, W, points, radius=16):
    """Generate a mask from points: union of disks around each point."""
    mask = torch.zeros(H, W, dtype=torch.float32)
    if not points:
        return mask
    yy, xx = torch.meshgrid(
        torch.arange(H, dtype=torch.float32),
        torch.arange(W, dtype=torch.float32),
        indexing="ij",
    )
    for (px, py) in points:
        d2 = (xx - px) ** 2 + (yy - py) ** 2
        mask = torch.maximum(mask, (d2 <= radius * radius).float())
    return mask


def _box_mask(H, W, box):
    """Generate a mask from a box [x1, y1, x2, y2]."""
    mask = torch.zeros(H, W, dtype=torch.float32)
    x1, y1, x2, y2 = box
    x1 = max(0, min(W - 1, x1))
    y1 = max(0, min(H - 1, y1))
    x2 = max(0, min(W - 1, x2))
    y2 = max(0, min(H - 1, y2))
    if x2 >= x1 and y2 >= y1:
        mask[y1:y2 + 1, x1:x2 + 1] = 1.0
    return mask


def _auto_mask(H, W, points):
    """Auto mode: if points given, use them; otherwise centre disk."""
    if points:
        return _point_mask(H, W, points)
    cx, cy = W // 2, H // 2
    r = max(8, min(H, W) // 8)
    return _point_mask(H, W, [(cx, cy)], radius=r)


def _generate_mask(H, W, points, box, mask_mode):
    """Dispatch to the right mask generator."""
    if mask_mode == "Box":
        return _box_mask(H, W, box)
    if mask_mode == "Point":
        return _point_mask(H, W, points)
    if mask_mode == "Auto":
        return _auto_mask(H, W, points)
    raise ValueError(f"unknown mask_mode: {mask_mode!r}")


class PSN_SAM_Segmenter:
    """Generate a segmentation mask from point/box prompts (SAM stand-in).

    NOTE: This is a geometric stand-in for the real SAM model.  The real
    SAM inference requires the `segment_anything` package and a model
    checkpoint, which are not available in this environment.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "point_coords": ("STRING", {"default": "[128, 128]"}),
                "mask_mode": (["Point", "Box", "Auto"], {"default": "Point"}),
                "sam_model_path": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("MASK", "IMAGE")
    RETURN_NAMES = ("mask", "segmented_image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, point_coords, mask_mode, sam_model_path):
        img = _validate_image(image)
        B, H, W, C = img.shape

        # Parse point_coords: accept JSON string or list/tensor
        if isinstance(point_coords, str):
            import json
            try:
                parsed = json.loads(point_coords)
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"point_coords string is not valid JSON: {e}")
        else:
            parsed = point_coords

        points = _parse_points(parsed)
        box = None
        if mask_mode == "Box":
            box = _parse_box(parsed)

        # Generate per-batch mask (same mask for all batch items)
        mask_hw = _generate_mask(H, W, points, box, mask_mode)
        mask = mask_hw.unsqueeze(0).expand(B, H, W).clone()

        # Isolate the segmented region: image * mask (broadcast over C)
        mask_bc = mask.unsqueeze(-1)  # [B, H, W, 1]
        segmented = img * mask_bc

        return (mask, segmented)


NODE_CLASS_MAPPINGS = {
    "PSN_SAM_Segmenter": PSN_SAM_Segmenter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SAM_Segmenter": "SAM Segmenter (Inpainting)",
}
