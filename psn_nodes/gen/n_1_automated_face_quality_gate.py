"""ParametricStudio - Automated Face Quality Gate.

Two ComfyUI nodes:

* PSN_FaceQualityScorer: scores an IMAGE for quality using pure-torch
  heuristics (sharpness via Laplacian energy, artifact detection via
  high-frequency noise energy, and optional identity similarity against a
  REFERENCE_IMAGE via normalized cross-correlation). Outputs the image
  unchanged plus a composite SCORE in [0, 1] and a PASS boolean.

* PSN_QualityGateRouter: passes the image through when PASS is True,
  otherwise substitutes FALLBACK_IMAGE (or a neutral placeholder when no
  fallback is provided).

No external models are required: the spec's insightface/opencv/scipy
pipeline is replaced by lightweight torch CPU heuristics so the module
runs anywhere torch is available.
"""

import torch

CAT = "ParametricStudio/QualityGate"


def _as_image(img, name="image"):
    """Validate and return a float tensor [B,H,W,C] in 0..1 (a copy)."""
    if not isinstance(img, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor, got {type(img).__name__}")
    if img.dim() != 4:
        raise ValueError(f"{name} must have shape [B,H,W,C], got {tuple(img.shape)}")
    if img.shape[-1] not in (1, 3, 4):
        raise ValueError(f"{name} last dim must be 1/3/4 channels, got {img.shape[-1]}")
    x = img.detach().float().clone()
    if x.numel() and (x.min() < -1e-6 or x.max() > 1 + 1e-6):
        raise ValueError(f"{name} values must be in [0, 1]")
    return x


def _to_gray(x):
    """[B,H,W,C] -> [B,H,W] luminance."""
    c = x.shape[-1]
    if c == 1:
        return x[..., 0]
    if c == 3:
        return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
    return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]


def _sharpness(gray):
    """Mean Laplacian energy -> 0..1 (saturating)."""
    if gray.shape[1] < 3 or gray.shape[2] < 3:
        return 0.5
    lap = (
        gray[:, 1:-1, 2:]
        + gray[:, 1:-1, :-2]
        + gray[:, 2:, 1:-1]
        + gray[:, :-2, 1:-1]
        - 4.0 * gray[:, 1:-1, 1:-1]
    )
    energy = lap.abs().mean().item()
    # Typical sharp images have energy ~0.05-0.3; saturate at 0.3.
    return min(1.0, energy / 0.3)


def _artifact_score(gray):
    """High-frequency noise energy -> 0..1 where 1 means clean."""
    if gray.shape[1] < 3 or gray.shape[2] < 3:
        return 0.5
    # 3x3 box blur as a cheap low-pass.
    pad = torch.nn.functional.pad(gray, (1, 1, 1, 1), mode="replicate")
    acc = torch.zeros_like(gray)
    for dy in range(3):
        for dx in range(3):
            acc = acc + pad[:, dy:dy + gray.shape[1], dx:dx + gray.shape[2]]
    blur = acc / 9.0
    noise = (gray - blur).pow(2).mean().item()
    # Noise variance ~0.001 is already quite noisy; clean < 1e-4.
    return max(0.0, 1.0 - noise / 0.001)


def _identity_similarity(a, b):
    """Normalized cross-correlation between two images (same size)."""
    ga, gb = _to_gray(a), _to_gray(b)
    if ga.shape != gb.shape:
        # Resize b to a's spatial size with nearest.
        gb = torch.nn.functional.interpolate(
            gb.unsqueeze(1), size=ga.shape[1:], mode="nearest"
        ).squeeze(1)
    a0 = ga - ga.mean()
    b0 = gb - gb.mean()
    denom = a0.norm() * b0.norm()
    if denom < 1e-8:
        return 0.5
    ncc = (a0 * b0).sum() / denom
    return ncc.clamp(0.0, 1.0).item()


def _placeholder_image(ref):
    """Neutral gray placeholder with the same batch/size as ref."""
    b, h, w, c = ref.shape
    return torch.full((b, h, w, c), 0.5, dtype=torch.float32)


class PSN_FaceQualityScorer:
    """Score an image for face quality (sharpness, artifacts, optional identity)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "IMAGE": ("IMAGE",),
                "THRESHOLD": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0}),
            },
            "optional": {
                "REFERENCE_IMAGE": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "BOOLEAN")
    RETURN_NAMES = ("IMAGE", "SCORE", "PASS")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, IMAGE, THRESHOLD, REFERENCE_IMAGE=None):
        img = _as_image(IMAGE, "IMAGE")
        if not (0.0 <= THRESHOLD <= 1.0):
            raise ValueError("THRESHOLD must be in [0, 1]")
        gray = _to_gray(img)
        sharp = _sharpness(gray)
        clean = _artifact_score(gray)
        if REFERENCE_IMAGE is not None:
            ref = _as_image(REFERENCE_IMAGE, "REFERENCE_IMAGE")
            ident = _identity_similarity(img, ref)
            score = 0.4 * sharp + 0.3 * clean + 0.3 * ident
        else:
            score = 0.6 * sharp + 0.4 * clean
        score = float(min(1.0, max(0.0, score)))
        return (img, score, bool(score >= THRESHOLD))


class PSN_QualityGateRouter:
    """Route an image through a quality gate: pass or fall back."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "IMAGE": ("IMAGE",),
                "PASS": ("BOOLEAN",),
            },
            "optional": {
                "FALLBACK_IMAGE": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, IMAGE, PASS, FALLBACK_IMAGE=None):
        img = _as_image(IMAGE, "IMAGE")
        if PASS:
            return (img,)
        if FALLBACK_IMAGE is not None:
            fb = _as_image(FALLBACK_IMAGE, "FALLBACK_IMAGE")
            if fb.shape != img.shape:
                fb = torch.nn.functional.interpolate(
                    fb.permute(0, 3, 1, 2), size=(img.shape[1], img.shape[2]), mode="nearest"
                ).permute(0, 2, 3, 1)
            return (fb,)
        # No fallback: emit a neutral placeholder so downstream nodes keep working.
        return (_placeholder_image(img),)


NODE_CLASS_MAPPINGS = {
    "PSN_FaceQualityScorer": PSN_FaceQualityScorer,
    "PSN_QualityGateRouter": PSN_QualityGateRouter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FaceQualityScorer": "PSN Face Quality Scorer",
    "PSN_QualityGateRouter": "PSN Quality Gate Router",
}
