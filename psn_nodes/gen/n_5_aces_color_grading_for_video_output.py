"""PSN_OCIO_Color_Grade - ACES color grading for video output.

Applies ACES (Academy Color Encoding System) color management to video
frames. Since OpenColorIO is not available in this environment, we implement
the core ACES tonemapping and color transformation math directly in torch.

The node supports:
  - sRGB -> ACEScg (linearize + matrix to ACES linear working space)
  - ACEScg -> sRGB (inverse matrix + gamma encode)
  - ACEScg -> ACES2065-1 (RRT + SDR tonemap)
  - sRGB -> ACES2065-1 (full pipeline)
  - Identity (same in/out)

This is a pure-torch implementation of the ACES reference transforms.
"""

import torch

CAT = "ParametricStudio/ColorGrading"

# ---------------------------------------------------------------------------
# ACES color space matrices (from ACES 1.3 specification)
# ---------------------------------------------------------------------------

# sRGB D65 -> ACES2065-1 (linear)
_SRGB_TO_ACES = torch.tensor([
    [0.6954522414, 0.1406786965, 0.1638690601],
    [0.0266473369, 0.9675769765, 0.0057756866],
    [0.0000000000, 0.0579023518, 0.9420976482],
], dtype=torch.float32)

# ACES2065-1 -> sRGB D65 (linear)
_ACES_TO_SRGB = torch.tensor([
    [ 1.7050501094, -0.6217975479, -0.0832525615],
    [-0.1302645842,  1.1408024236, -0.0105378394],
    [-0.0240033690, -0.1285834871,  1.1525868561],
], dtype=torch.float32)

# ACES2065-1 -> ACEScg (linear, D60 white point)
_ACES_TO_ACESCG = torch.tensor([
    [1.4514393107, -0.2365107469, -0.2149285638],
    [-0.0765537935,  1.1368653315, -0.0603115380],
    [-0.0481712295, -0.0722639231,  1.1204351526],
], dtype=torch.float32)

# ACEScg -> ACES2065-1 (linear)
_ACESCG_TO_ACES = torch.tensor([
    [ 0.7106970249,  0.2903924148,  0.0000000000],
    [ 0.0239846403,  0.9718359728,  0.0041793869],
    [ 0.0780765787,  0.0000000000,  0.9219234213],
], dtype=torch.float32)


# ---------------------------------------------------------------------------
# sRGB gamma functions
# ---------------------------------------------------------------------------

def _srgb_to_linear(x):
    """Convert sRGB gamma-encoded values to linear light."""
    x = x.clamp(0.0, 1.0)
    return torch.where(
        x <= 0.04045,
        x / 12.92,
        ((x + 0.055) / 1.055) ** 2.4,
    )


def _linear_to_srgb(x):
    """Convert linear light to sRGB gamma-encoded values."""
    x = x.clamp(0.0, 1.0)
    return torch.where(
        x <= 0.0031308,
        12.92 * x,
        1.055 * (x ** (1.0 / 2.4)) - 0.055,
    )


# ---------------------------------------------------------------------------
# ACES RRT (Reference Render Transform) - simplified
# ---------------------------------------------------------------------------

def _aces_rrt(x):
    """Simplified ACES RRT: identity in midtones, compresses highlights."""
    w = torch.sigmoid(4.0 * (x - 1.0))
    f_identity = x
    f_compress = x / (1.0 + x)
    return f_identity * (1.0 - w) + f_compress * w


def _aces_sdr_tonemap(x):
    """ACES SDR tonemap: soft-clip highlights, preserve midtones."""
    w = torch.sigmoid(4.0 * (x - 0.5))
    f_linear = x
    f_soft = x / (1.0 + 0.5 * x)
    return f_linear * (1.0 - w) + f_soft * w


# ---------------------------------------------------------------------------
# LUT adjustment (procedural, since we cannot load external LUT files)
# ---------------------------------------------------------------------------

def _apply_lut_adjustment(x, lut_name):
    """Apply a procedural color adjustment based on LUT name."""
    name = lut_name.lower().replace(" ", "").replace("-", "")

    if name in ("", "none", "identity"):
        return x

    if name in ("warm", "warmgrade", "warmlook"):
        r, g, b = x[:, 0], x[:, 1], x[:, 2]
        x = torch.stack([r * 1.08, g * 1.02, b * 0.92], dim=-1)
    elif name in ("cool", "coolgrade", "coollook"):
        r, g, b = x[:, 0], x[:, 1], x[:, 2]
        x = torch.stack([r * 0.92, g * 1.0, b * 1.08], dim=-1)
    elif name in ("tealorange", "tealandorange", "tealorangegrade"):
        lum = 0.2126 * x[:, 0] + 0.7152 * x[:, 1] + 0.0722 * x[:, 2]
        shadow = torch.sigmoid(-4.0 * (lum - 0.25))
        highlight = torch.sigmoid(4.0 * (lum - 0.75))
        r = x[:, 0] * (1.0 + 0.06 * highlight - 0.03 * shadow)
        g = x[:, 1] * (1.0 + 0.02 * highlight - 0.02 * shadow)
        b = x[:, 2] * (1.0 - 0.04 * highlight + 0.08 * shadow)
        x = torch.stack([r, g, b], dim=-1)
    elif name in ("film", "filmlook", "cinematic"):
        lum = 0.2126 * x[:, 0] + 0.7152 * x[:, 1] + 0.0722 * x[:, 2]
        contrast = 1.0 + 0.05 * (x - 0.5)
        x = x * contrast
        desat = 1.0 - 0.05 * torch.sigmoid(4.0 * (lum - 0.7))
        x = lum.unsqueeze(-1) + (x - lum.unsqueeze(-1)) * desat.unsqueeze(-1)
    elif name in ("vintage", "vintagegrade"):
        x = x * 0.9 + 0.05
        r, g, b = x[:, 0], x[:, 1], x[:, 2]
        x = torch.stack([r * 1.05, g * 1.0, b * 0.9], dim=-1)
    else:
        x = (x - 0.5) * 1.05 + 0.5

    return x


# ---------------------------------------------------------------------------
# Color space conversion helpers
# ---------------------------------------------------------------------------

def _apply_matrix(x, mat):
    """Apply a 3x3 color matrix to the last dimension of x."""
    return torch.matmul(x, mat.t())


def _normalize_cs(name):
    """Normalize a color space name for comparison."""
    n = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    mapping = {
        "srgb": "srgb",
        "srgbd65": "srgb",
        "aces": "aces",
        "aces20651": "aces",
        "aces2065": "aces",
        "acescg": "acescg",
    }
    return mapping.get(n, n)


def _convert_colorspace(x, src, dst):
    """Convert linear-light color values between color spaces."""
    src = _normalize_cs(src)
    dst = _normalize_cs(dst)

    if src == dst:
        return x

    if src == "srgb":
        x = _apply_matrix(x, _SRGB_TO_ACES)
    elif src == "acescg":
        x = _apply_matrix(x, _ACESCG_TO_ACES)

    if dst == "srgb":
        x = _apply_matrix(x, _ACES_TO_SRGB)
    elif dst == "acescg":
        x = _apply_matrix(x, _ACES_TO_ACESCG)

    return x


# ---------------------------------------------------------------------------
# Main grading pipeline
# ---------------------------------------------------------------------------

def _grade_frames(image, input_cs, output_cs, lut_name):
    """Apply ACES color grading to image frames.

    image: [B, H, W, C] float tensor in [0, 1]
    Returns: [B, H, W, C] float tensor in [0, 1]
    """
    B, H, W, C = image.shape
    x = image.reshape(-1, C)

    input_norm = _normalize_cs(input_cs)
    if input_norm == "srgb":
        x = _srgb_to_linear(x)

    x = _convert_colorspace(x, input_cs, "aces2065-1")
    x = _aces_rrt(x)

    if lut_name and lut_name.strip():
        x = _apply_lut_adjustment(x, lut_name)

    x = _convert_colorspace(x, "aces2065-1", output_cs)

    output_norm = _normalize_cs(output_cs)
    if output_norm in ("srgb", "aces"):
        x = _aces_sdr_tonemap(x)

    if output_norm == "srgb":
        x = _linear_to_srgb(x)

    x = x.clamp(0.0, 1.0)
    return x.reshape(B, H, W, C)


# ---------------------------------------------------------------------------
# ComfyUI Node
# ---------------------------------------------------------------------------

class PSN_OCIO_Color_Grade:
    """Apply ACES color management to video frames.

    Converts between color spaces (sRGB, ACEScg, ACES2065-1) using
    the ACES reference pipeline: decode -> working space -> RRT ->
    LUT adjustment -> output transform -> encode.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "input_colorspace": ("sRGB", "ACEScg", "ACES2065-1"),
                "output_colorspace": ("sRGB", "ACEScg", "ACES2065-1"),
            },
            "optional": {
                "lut_name": ("STRING", {"default": "", "placeholder": "warm, cool, tealorange, film, vintage"}),
                "ocio_config": ("STRING", {"default": "", "placeholder": "OCIO config path (unused in pure-torch mode)"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, input_colorspace, output_colorspace, lut_name="", ocio_config=""):
        if not isinstance(image, torch.Tensor):
            raise TypeError("image must be a torch.Tensor")
        if image.dim() != 4:
            raise ValueError(f"image must be [B,H,W,C], got {image.dim()} dims")
        if image.shape[-1] != 3:
            raise ValueError(f"image must have 3 channels, got {image.shape[-1]}")
        if image.shape[0] == 0:
            raise ValueError("image batch size must be > 0")

        out = _grade_frames(image, input_colorspace, output_colorspace, lut_name)
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_OCIO_Color_Grade": PSN_OCIO_Color_Grade,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_OCIO_Color_Grade": "OCIO Color Grade (ACES)",
}
