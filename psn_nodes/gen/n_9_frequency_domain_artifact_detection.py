"""Frequency-domain artifact detection for ComfyUI (ParametricStudio).

Computes the Radial Average Amplitude Spectrum (RAAS) of an image and flags
high-frequency spikes that typically indicate compression artifacts, ringing,
or other frequency-domain noise.

Implemented purely with torch (CPU) + stdlib. No opencv/numpy/matplotlib.
"""

import math

import torch

CAT = "ParametricStudio/CV"


def _as_image(image):
    """Validate and return a float32 CPU tensor [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    x = image.detach().float().cpu()
    if x.dim() != 4 or x.shape[-1] not in (1, 3, 4):
        raise ValueError("image must have shape [B,H,W,C] with C in {1,3,4}")
    if x.shape[1] < 2 or x.shape[2] < 2:
        raise ValueError("image H and W must be >= 2")
    if torch.isnan(x).any() or torch.isinf(x).any():
        raise ValueError("image contains NaN/Inf")
    return x


def _grayscale(x):
    """[B,H,W,C] -> [B,H,W] grayscale in 0..1 (luminance weights)."""
    c = x.shape[-1]
    if c == 1:
        return x[..., 0]
    if c == 3:
        return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
    # RGBA: ignore alpha
    return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]


def _radial_average_amplitude(g):
    """g: [B,H,W] -> [B, R] radial average amplitude spectrum (centered).

    R = min(H,W)//2 bins. Bin 0 is the DC (zero frequency) component.
    """
    b, h, w = g.shape
    r = min(h, w) // 2
    # Center the zero frequency: fftshift via roll by half
    f = torch.fft.fft2(g)
    f = torch.fft.fftshift(f)
    amp = f.abs()  # [B,H,W]

    # Build a radius map once (shared across batch)
    ys = torch.arange(h, dtype=torch.float32) - (h - 1) / 2.0
    xs = torch.arange(w, dtype=torch.float32) - (w - 1) / 2.0
    yy, xx = torch.meshgrid(ys, xs, indexing="ij")
    radius = torch.sqrt(yy * yy + xx * xx).long().clamp(max=r - 1)  # [H,W]

    # Accumulate sums and counts per radius bin
    sums = torch.zeros(b, r, dtype=torch.float32)
    counts = torch.zeros(b, r, dtype=torch.float32)
    # Use scatter_add over flattened (H*W) with bin index
    flat = radius.reshape(1, -1).expand(b, -1)  # [B, H*W]
    amp_flat = amp.reshape(b, -1)  # [B, H*W]
    sums.scatter_add_(1, flat, amp_flat)
    counts.scatter_add_(1, flat, torch.ones_like(amp_flat))
    counts = counts.clamp(min=1.0)
    return sums / counts  # [B, R]


def _artifact_score(raas, threshold):
    """Score in 0..1: how much energy sits in the high-frequency tail relative
    to the low-frequency content, compared against `threshold`.

    High-frequency tail = the top 25% of radial bins (excluding DC).
    """
    b, r = raas.shape
    if r < 4:
        return torch.zeros(b, dtype=torch.float32)
    # Exclude DC bin
    tail_start = max(1, int(r * 0.75))
    tail = raas[:, tail_start:]
    low = raas[:, 1:tail_start]
    tail_mean = tail.mean(dim=1)
    low_mean = low.mean(dim=1).clamp(min=1e-8)
    ratio = tail_mean / low_mean
    # Map ratio to 0..1: ratio >= threshold -> 1.0, ratio <= 0 -> 0.0
    score = (ratio / threshold).clamp(max=1.0)
    return score


def _plot_image(raas, score, threshold):
    """Render the radial average spectrum as a 1D plot image [1,H,W,3] in 0..1.

    The plot shows the spectrum (log-ish scaled) with a horizontal threshold
    line and the artifact score encoded in the border color.
    """
    b, r = raas.shape
    plot_h = 256
    plot_w = 512
    # Normalize spectrum for display: use log1p to make low freqs visible
    spec = raas  # [B, R]
    spec_max = spec.max(dim=1, keepdim=True).values.clamp(min=1e-8)
    spec_norm = torch.log1p(spec) / torch.log1p(spec_max)  # [B, R] in 0..1

    # Build a single plot for the first batch element (or average)
    if b > 1:
        spec_norm = spec_norm.mean(dim=0, keepdim=True)
    s = spec_norm[0]  # [R]

    # Upsample to plot_w
    if r != plot_w:
        idx = (torch.arange(plot_w, dtype=torch.float32) * (r - 1) / max(plot_w - 1, 1)).long().clamp(max=r - 1)
        s = s[idx]

    # Draw: white background, black spectrum line, red threshold line
    canvas = torch.ones(1, plot_h, plot_w, 3, dtype=torch.float32)
    # Spectrum line: for each x, y = plot_h - s[x]*plot_h
    xs = torch.arange(plot_w)
    ys = (plot_h - 1 - s * (plot_h - 1)).long().clamp(0, plot_h - 1)
    canvas[0, ys, xs, 0] = 0.0
    canvas[0, ys, xs, 1] = 0.0
    canvas[0, ys, xs, 2] = 0.0
    # Fill under the curve lightly
    for x in range(plot_w):
        y = int(ys[x])
        canvas[0, y:, x, 0] = 0.85
        canvas[0, y:, x, 1] = 0.85
        canvas[0, y:, x, 2] = 0.85

    # Threshold line: threshold maps to a y position (score=1 means ratio=threshold)
    # We draw it at a fixed 75% height as a visual guide
    ty = int(plot_h * 0.25)
    canvas[0, ty, :, 0] = 1.0
    canvas[0, ty, :, 1] = 0.2
    canvas[0, ty, :, 2] = 0.2

    # Border color encodes score: green (0) -> red (1)
    sc = float(score[0]) if b > 0 else 0.0
    border_r = sc
    border_g = 1.0 - sc
    border = torch.tensor([border_r, border_g, 0.0], dtype=torch.float32)
    canvas[0, 0, :, :] = border
    canvas[0, -1, :, :] = border
    canvas[0, :, 0, :] = border
    canvas[0, :, -1, :] = border

    return canvas


class PSN_CV_FrequencyArtifact:
    """Detect high-frequency artifacts via Radial Average Amplitude Spectrum."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "artifact_threshold": ("FLOAT", {"default": 0.1, "min": 0.001, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "BOOLEAN")
    RETURN_NAMES = ("spectrum_plot", "artifact_score", "has_artifacts")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, artifact_threshold):
        x = _as_image(image)
        g = _grayscale(x)  # [B,H,W]
        raas = _radial_average_amplitude(g)  # [B,R]
        score = _artifact_score(raas, artifact_threshold)  # [B]
        # Average score across batch for a single scalar
        score_scalar = float(score.mean().item())
        has_artifacts = bool(score_scalar >= artifact_threshold)
        plot = _plot_image(raas, score, artifact_threshold)
        return (plot, score_scalar, has_artifacts)


NODE_CLASS_MAPPINGS = {
    "PSN_CV_FrequencyArtifact": PSN_CV_FrequencyArtifact,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CV_FrequencyArtifact": "Frequency Domain Artifact Detection",
}
