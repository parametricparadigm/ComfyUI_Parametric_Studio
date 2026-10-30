"""Nuke-style compositing suite for ComfyUI (ParametricStudio).

Nodes:
  - PSN_Composite_Merge: blend two images with a mask and a blend mode.
  - PSN_Composite_Grading: 3-way Lift/Gamma/Gain color correction.
  - PSN_Composite_Mask_Generator: luminance/alpha mask with feathering.

All tensor work is done with torch on CPU; inputs are never mutated.
"""

import torch

CAT = "ParametricStudio/Compositing"

BLEND_MODES = ["normal", "multiply", "screen", "overlay"]


def _as_image(x, name="image"):
    """Validate and return a float tensor [B,H,W,C] in 0..1 (cloned)."""
    if not isinstance(x, torch.Tensor):
        raise ValueError(f"{name} must be a torch.Tensor, got {type(x).__name__}")
    if x.dim() != 4:
        raise ValueError(f"{name} must be a 4D tensor [B,H,W,C], got shape {tuple(x.shape)}")
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError(f"{name} last dim must be 1, 3 or 4 channels, got {x.shape[-1]}")
    return x.detach().to(torch.float32).clone()


def _as_mask(m, name="mask"):
    """Validate and return a float tensor [B,H,W] in 0..1 (cloned)."""
    if not isinstance(m, torch.Tensor):
        raise ValueError(f"{name} must be a torch.Tensor, got {type(m).__name__}")
    if m.dim() != 3:
        raise ValueError(f"{name} must be a 3D tensor [B,H,W], got shape {tuple(m.shape)}")
    return m.detach().to(torch.float32).clone().clamp(0.0, 1.0)


def _match_spatial(a, b, name_a, name_b):
    """Broadcast spatial dims: if one is 1 in H or W, expand to the other."""
    if a.shape[1:3] != b.shape[1:3]:
        if a.shape[1] == 1 and a.shape[2] == 1:
            a = a.expand(-1, b.shape[1], b.shape[2], -1)
        elif b.shape[1] == 1 and b.shape[2] == 1:
            b = b.expand(-1, a.shape[1], a.shape[2], -1)
        else:
            raise ValueError(
                f"Spatial size mismatch between {name_a} {tuple(a.shape[1:3])} "
                f"and {name_b} {tuple(b.shape[1:3])}"
            )
    return a, b


def _blend(a, b, mode):
    """Apply a blend mode elementwise on [B,H,W,C] tensors in 0..1."""
    if mode == "normal":
        return b
    if mode == "multiply":
        return a * b
    if mode == "screen":
        return 1.0 - (1.0 - a) * (1.0 - b)
    if mode == "overlay":
        # Standard overlay: base a, blend b
        return torch.where(a < 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))
    raise ValueError(f"Unknown blend mode: {mode!r}. Valid: {BLEND_MODES}")


def _vec3(v, name):
    """Coerce a 3-element sequence to a float tensor [3]."""
    if isinstance(v, torch.Tensor):
        t = v.detach().to(torch.float32).reshape(-1)
    else:
        try:
            t = torch.tensor(list(v), dtype=torch.float32)
        except Exception:
            raise ValueError(f"{name} must be a 3-element numeric sequence")
    if t.numel() != 3:
        raise ValueError(f"{name} must have exactly 3 elements, got {t.numel()}")
    return t


class PSN_Composite_Merge:
    """Merge image_b over image_a using a mask and a blend mode (Nuke-style)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
                "mask": ("MASK",),
                "blend_mode": (BLEND_MODES,),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_a, image_b, mask, blend_mode):
        a = _as_image(image_a, "image_a")
        b = _as_image(image_b, "image_b")
        m = _as_mask(mask, "mask")

        a, b = _match_spatial(a, b, "image_a", "image_b")
        # Expand mask to [B,H,W,1] for broadcasting over channels.
        if m.shape[0] == 1 and a.shape[0] != 1:
            m = m.expand(a.shape[0], -1, -1)
        elif m.shape[0] != a.shape[0]:
            raise ValueError(f"mask batch {m.shape[0]} != image batch {a.shape[0]}")
        if m.shape[1:3] != a.shape[1:3]:
            if m.shape[1] == 1 and m.shape[2] == 1:
                m = m.expand(-1, a.shape[1], a.shape[2])
            else:
                raise ValueError(
                    f"mask spatial {tuple(m.shape[1:3])} != image spatial {tuple(a.shape[1:3])}"
                )

        m4 = m.unsqueeze(-1)
        blended = _blend(a, b, blend_mode)
        out = a * (1.0 - m4) + blended * m4
        return (out.clamp(0.0, 1.0),)


class PSN_Composite_Grading:
    """3-way Lift/Gamma/Gain color correction (Nuke-style grade)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "lift": ("VEC3", {"default": [0.0, 0.0, 0.0]}),
                "gamma": ("VEC3", {"default": [1.0, 1.0, 1.0]}),
                "gain": ("VEC3", {"default": [1.0, 1.0, 1.0]}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, lift, gamma, gain):
        img = _as_image(image, "image")
        lift_t = _vec3(lift, "lift")
        gamma_t = _vec3(gamma, "gamma")
        gain_t = _vec3(gain, "gain")

        # Work on the first 3 channels (RGB); keep any alpha untouched.
        rgb = img[..., :3]
        alpha = img[..., 3:]

        # Guard against gamma <= 0 (pow would be undefined).
        gamma_safe = gamma_t.clamp(min=1e-6)

        # Standard 3-way: out = (in * gain) ** gamma + lift, clamped to 0..1.
        graded = (rgb * gain_t) ** gamma_safe + lift_t
        graded = graded.clamp(0.0, 1.0)

        if alpha.shape[-1] > 0:
            out = torch.cat([graded, alpha], dim=-1)
        else:
            out = graded
        return (out,)


class PSN_Composite_Mask_Generator:
    """Generate a soft mask from image luminance (or alpha) with feathering."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
                "feather": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, threshold, feather):
        img = _as_image(image, "image")
        threshold = float(threshold)
        feather = float(feather)
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"threshold must be in [0,1], got {threshold}")
        if not (0.0 <= feather <= 1.0):
            raise ValueError(f"feather must be in [0,1], got {feather}")

        # Use alpha channel if present, otherwise luminance (Rec.709-ish).
        if img.shape[-1] == 4:
            lum = img[..., 3:4]
        else:
            rgb = img[..., :3]
            lum = 0.2126 * rgb[..., 0:1] + 0.7152 * rgb[..., 1:2] + 0.0722 * rgb[..., 2:3]

        # Soft threshold: linear ramp from (threshold - feather) to (threshold + feather).
        lo = threshold - feather
        hi = threshold + feather
        if hi - lo < 1e-6:
            mask = (lum >= threshold).to(torch.float32)
        else:
            mask = ((lum - lo) / (hi - lo)).clamp(0.0, 1.0)

        # Squeeze to [B,H,W].
        return (mask.squeeze(-1),)


NODE_CLASS_MAPPINGS = {
    "PSN_Composite_Merge": PSN_Composite_Merge,
    "PSN_Composite_Grading": PSN_Composite_Grading,
    "PSN_Composite_Mask_Generator": PSN_Composite_Mask_Generator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Composite_Merge": "Composite Merge (Nuke)",
    "PSN_Composite_Grading": "Composite Grading (Nuke)",
    "PSN_Composite_Mask_Generator": "Composite Mask Generator (Nuke)",
}
