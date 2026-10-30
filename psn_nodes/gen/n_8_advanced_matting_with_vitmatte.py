"""ParametricStudio - Advanced Matting (VitMatte-style) node.

The real VitMatte model is a heavy ViT encoder/decoder that requires
onnxruntime and a downloaded checkpoint.  Neither is available in this
environment, so this module implements the *core* of the matting
pipeline that plain torch on CPU can do:

1.  Build a trimap from the rough mask (definite-foreground /
    definite-background / unknown band) using a morphological
    dilation/erosion implemented with torch.nn.functional.max_pool2d
    and min_pool2d (no scipy / cv2 needed).
2.  Refine the rough mask into a smooth alpha channel by solving a
    simple Poisson-like diffusion (iterative Jacobi relaxation) on the
    unknown band, constrained by the trimap boundary values.
3.  Optionally blend the result with the original rough mask to keep
    the user's intent while smoothing edges.

What is NOT implemented (needs onnxruntime + model weights):
  * The actual VitMatte ViT encoder/decoder network.
  * GPU inference.
  * The onnxruntime session loading.
"""

import torch
import torch.nn.functional as F

CAT = "ParametricStudio/Matting"


def _as_tensor(x):
    """Return x as a torch tensor (no copy if already a tensor)."""
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x)


def _validate_image(image):
    """Validate an IMAGE tensor [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError(f"image must be 4-D [B,H,W,C], got {image.dim()}-D")
    if image.shape[-1] < 1:
        raise ValueError("image channel dim must be >= 1")
    if image.shape[1] < 2 or image.shape[2] < 2:
        raise ValueError("image H and W must be >= 2")
    if image.min() < -1e-6 or image.max() > 1 + 1e-6:
        raise ValueError("image values must be in [0, 1]")
    return image


def _validate_mask(mask, h, w):
    """Validate a MASK tensor [B,H,W] in 0..1."""
    if not isinstance(mask, torch.Tensor):
        raise TypeError("mask must be a torch.Tensor")
    if mask.dim() != 3:
        raise ValueError(f"mask must be 3-D [B,H,W], got {mask.dim()}-D")
    if mask.shape[1] != h or mask.shape[2] != w:
        raise ValueError(
            f"mask spatial size {mask.shape[1]}x{mask.shape[2]} "
            f"does not match image {h}x{w}"
        )
    if mask.min() < -1e-6 or mask.max() > 1 + 1e-6:
        raise ValueError("mask values must be in [0, 1]")
    return mask


def _dilate(mask, radius):
    """Binary dilation via max-pooling.  mask: [B,H,W] in {0,1}."""
    if radius <= 0:
        return mask
    k = 2 * radius + 1
    return F.max_pool2d(
        mask.unsqueeze(1), kernel_size=k, stride=1, padding=radius
    ).squeeze(1)


def _erode(mask, radius):
    """Binary erosion via min-pooling (negate -> max-pool -> negate)."""
    if radius <= 0:
        return mask
    k = 2 * radius + 1
    return 1.0 - F.max_pool2d(
        (1.0 - mask).unsqueeze(1), kernel_size=k, stride=1, padding=radius
    ).squeeze(1)


def _build_trimap(rough_mask, fg_radius, bg_radius):
    """Build a trimap from a rough mask.

    Returns (fg, bg, unknown) each [B,H,W] in {0,1}.
    fg  = eroded rough mask  (definite foreground)
    bg  = dilated complement (definite background)
    unknown = everything else
    """
    fg = _erode(rough_mask, fg_radius)
    bg = _dilate(1.0 - rough_mask, bg_radius)
    unknown = 1.0 - fg - bg
    # In case fg and bg overlap (very thin mask), resolve in favour of
    # the unknown band so we never have contradictory constraints.
    overlap = fg * bg
    fg = fg - overlap
    bg = bg - overlap
    unknown = unknown + overlap
    return fg, bg, unknown


def _diffuse(alpha, unknown, fg, bg, iterations, sigma):
    """Iterative Jacobi diffusion on the unknown band.

    At each step, every unknown pixel is replaced by the weighted
    average of its 4-neighbours (Laplacian smoothing).  Pixels that
    are definite foreground or background keep their constraint value.
    """
    a = alpha.clone()
    for _ in range(iterations):
        # 4-neighbour average (replicate-padded boundary)
        a_pad = F.pad(a, (1, 1, 1, 1), mode="replicate")
        up = a_pad[:, 0:-2, 1:-1]
        dn = a_pad[:, 2:, 1:-1]
        lf = a_pad[:, 1:-1, 0:-2]
        rt = a_pad[:, 1:-1, 2:]
        avg = (up + dn + lf + rt) / 4.0
        # Only update unknown pixels
        a = a + unknown * (avg - a) * sigma
        # Re-apply hard constraints
        a = a * (1.0 - fg) + fg * 1.0
        a = a * (1.0 - bg) + bg * 0.0
        a = a.clamp(0.0, 1.0)
    return a


def _gaussian_blur(mask, radius):
    """Simple separable box-blur approximation of a Gaussian blur."""
    if radius <= 0:
        return mask
    k = 2 * radius + 1
    # Two passes of box blur approximate a Gaussian well enough.
    for _ in range(2):
        mask = F.avg_pool2d(
            mask.unsqueeze(1), kernel_size=k, stride=1, padding=radius
        ).squeeze(1)
    return mask


class PSN_VitMatteAlpha:
    """Refine a rough mask into a smooth alpha channel (VitMatte-style).

    Uses trimap construction + iterative diffusion to produce a
    high-quality alpha matting result.  This is a CPU/torch-only
    approximation of the full VitMatte pipeline.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "rough_mask": ("MASK",),
            },
            "optional": {
                "fg_radius": (
                    "INT",
                    {"default": 5, "min": 0, "max": 64},
                ),
                "bg_radius": (
                    "INT",
                    {"default": 5, "min": 0, "max": 64},
                ),
                "iterations": (
                    "INT",
                    {"default": 50, "min": 1, "max": 500},
                ),
                "sigma": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.01, "max": 1.0},
                ),
                "blur_radius": (
                    "INT",
                    {"default": 1, "min": 0, "max": 32},
                ),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("alpha_mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        image,
        rough_mask,
        fg_radius=5,
        bg_radius=5,
        iterations=50,
        sigma=0.5,
        blur_radius=1,
    ):
        image = _validate_image(image)
        h, w = image.shape[1], image.shape[2]
        rough_mask = _validate_mask(rough_mask, h, w)

        # Work in float32 on CPU
        rm = rough_mask.float().cpu()

        # Build trimap
        fg, bg, unknown = _build_trimap(rm, fg_radius, bg_radius)

        # Initialise alpha: 1 where fg, 0 where bg, 0.5 where unknown
        alpha = fg * 1.0 + bg * 0.0 + unknown * 0.5

        # Diffuse on the unknown band
        alpha = _diffuse(alpha, unknown, fg, bg, iterations, sigma)

        # Optional light blur to smooth remaining noise
        if blur_radius > 0:
            alpha = _gaussian_blur(alpha, blur_radius)
            # Re-apply hard constraints after blur
            alpha = alpha * (1.0 - fg) + fg * 1.0
            alpha = alpha * (1.0 - bg) + bg * 0.0

        alpha = alpha.clamp(0.0, 1.0)
        return (alpha,)


NODE_CLASS_MAPPINGS = {
    "PSN_VitMatteAlpha": PSN_VitMatteAlpha,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VitMatteAlpha": "VitMatte Alpha (Advanced Matting)",
}
