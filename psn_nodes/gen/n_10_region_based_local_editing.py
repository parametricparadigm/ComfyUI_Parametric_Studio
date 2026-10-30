"""ParametricStudio region-based local editing nodes.

Two nodes:
  * PSN_RegionDefinition  - build a MASK from rectangle / ellipse / polygon coords
  * PSN_LocalEditComposite - alpha-blend an edited image back into the original

Only torch (CPU) and the Python standard library are used.  No cv2, no
network, no subprocess, no file I/O.
"""

import json
import math

import torch

CAT = "ParametricStudio/RegionEdit"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_tensor(x):
    """Return x as a torch tensor (no copy when already a tensor)."""
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x)


def _validate_image(image, name="image"):
    t = _as_tensor(image)
    if t.dim() != 4 or t.shape[-1] < 1:
        raise ValueError(f"{name} must be a [B,H,W,C] tensor, got shape {tuple(t.shape)}")
    return t.float()


def _validate_mask(mask, name="region_mask"):
    t = _as_tensor(mask)
    if t.dim() != 3:
        raise ValueError(f"{name} must be a [B,H,W] tensor, got shape {tuple(t.shape)}")
    return t.float()


def _parse_coords(coords):
    """Parse the JSON coords string into a Python object.

    Accepted formats:
      rectangle : [x0, y0, x1, y1]          (pixel coords, inclusive)
      ellipse   : [cx, cy, rx, ry]          (centre + radii)
      polygon   : [[x0,y0],[x1,y1],...]     (>= 3 points)
    """
    if isinstance(coords, (list, tuple)):
        return coords
    if isinstance(coords, str):
        try:
            return json.loads(coords)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"coords is not valid JSON: {exc}") from exc
    raise ValueError("coords must be a JSON string or a list")


def _point_in_polygon(x, y, poly):
    """Ray-casting point-in-polygon test.  poly = [(x,y), ...]."""
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _build_mask_2d(h, w, region_type, coords):
    """Return a float tensor [H,W] in {0,1} for a single image."""
    mask = torch.zeros(h, w, dtype=torch.float32)

    if region_type == "rectangle":
        if len(coords) != 4:
            raise ValueError("rectangle coords must be [x0, y0, x1, y1]")
        x0, y0, x1, y1 = (int(round(float(c))) for c in coords)
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        x0 = max(0, x0); y0 = max(0, y0)
        x1 = min(w - 1, x1); y1 = min(h - 1, y1)
        if x1 >= x0 and y1 >= y0:
            mask[y0:y1 + 1, x0:x1 + 1] = 1.0

    elif region_type == "ellipse":
        if len(coords) != 4:
            raise ValueError("ellipse coords must be [cx, cy, rx, ry]")
        cx, cy, rx, ry = (float(c) for c in coords)
        if rx <= 0 or ry <= 0:
            raise ValueError("ellipse radii must be positive")
        ys, xs = torch.meshgrid(
            torch.arange(h, dtype=torch.float32),
            torch.arange(w, dtype=torch.float32),
            indexing="ij",
        )
        mask = (((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 <= 1.0).float()

    elif region_type == "polygon":
        if not isinstance(coords, (list, tuple)) or len(coords) < 3:
            raise ValueError("polygon coords must be a list of >= 3 [x,y] points")
        poly = [(float(p[0]), float(p[1])) for p in coords]
        for y in range(h):
            for x in range(w):
                if _point_in_polygon(x + 0.5, y + 0.5, poly):
                    mask[y, x] = 1.0

    else:
        raise ValueError(f"unknown region_type: {region_type!r}")

    return mask


# ---------------------------------------------------------------------------
# Node 1: PSN_RegionDefinition
# ---------------------------------------------------------------------------

class PSN_RegionDefinition:
    """Create a binary MASK for a rectangle, ellipse or polygon region."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "region_type": (["rectangle", "ellipse", "polygon"],),
                "coords": ("STRING", {"default": "[0, 0, 63, 63]"}),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("region_mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, region_type, coords):
        img = _validate_image(image, "image")
        b, h, w, _c = img.shape
        parsed = _parse_coords(coords)
        single = _build_mask_2d(h, w, region_type, parsed)
        mask = single.unsqueeze(0).expand(b, h, w).clone()
        return (mask,)


# ---------------------------------------------------------------------------
# Node 2: PSN_LocalEditComposite
# ---------------------------------------------------------------------------

class PSN_LocalEditComposite:
    """Alpha-blend *edited_region* into *original_image* using *region_mask*.

    The edited image may be the same size as the original (full-frame edit)
    or a smaller crop that is placed at the top-left of the mask region.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original_image": ("IMAGE",),
                "edited_region": ("IMAGE",),
                "region_mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("final_image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, original_image, edited_region, region_mask):
        orig = _validate_image(original_image, "original_image")
        edit = _validate_image(edited_region, "edited_region")
        mask = _validate_mask(region_mask, "region_mask")

        b, h, w, c = orig.shape

        if mask.shape[0] != b:
            raise ValueError(
                f"mask batch {mask.shape[0]} != image batch {b}"
            )
        if mask.shape[1] != h or mask.shape[2] != w:
            raise ValueError(
                f"mask spatial {tuple(mask.shape[1:])} != image spatial {(h, w)}"
            )
        if edit.shape[0] != b:
            raise ValueError(
                f"edited batch {edit.shape[0]} != image batch {b}"
            )

        # If the edited image is smaller, pad it to the full size (top-left).
        eh, ew, ec = edit.shape[1], edit.shape[2], edit.shape[3]
        if eh != h or ew != w:
            if eh > h or ew > w:
                raise ValueError(
                    f"edited_region {eh}x{ew} is larger than original {h}x{w}"
                )
            padded = torch.zeros(b, h, w, ec, dtype=torch.float32)
            padded[:, :eh, :ew, :] = edit
            edit = padded

        if ec != c:
            raise ValueError(
                f"edited_region channels {ec} != original channels {c}"
            )

        m = mask.unsqueeze(-1)  # [B,H,W,1]
        out = orig * (1.0 - m) + edit * m
        return (out,)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_RegionDefinition": PSN_RegionDefinition,
    "PSN_LocalEditComposite": PSN_LocalEditComposite,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RegionDefinition": "PSN Region Definition",
    "PSN_LocalEditComposite": "PSN Local Edit Composite",
}
