"""PSN_VideoQualityMetric: pure-logic video quality metric computation.

This module implements the pure-logic, secure-by-design part of a video quality
metric node. It does NOT use torch, ComfyUI, or any GPU/IO. Instead, it accepts
plain Python lists (representing frames as nested lists of pixel values) and
computes PSNR, SSIM, and a simplified LPIPS-like perceptual metric using only
the standard library.

Inputs:
    frames: A list of frames, where each frame is a list of rows, each row is a
            list of pixel values (floats in [0, 1] or [0, 255]).
    reference: A list of reference frames in the same structure.
    metric: One of "psnr", "ssim", "lpips".

Outputs:
    average_metric: FLOAT - The average metric value across all frames.
    heatmap: A list of frames (same shape as input) where each pixel is the
             per-pixel metric contribution (for PSNR: local error; for SSIM:
             local similarity; for LPIPS: local perceptual difference).

All pixel values are normalized to [0, 1] internally.
"""

import math

METRICS = ["psnr", "ssim", "lpips"]

def _normalize_frame(frame):
    """Normalize a frame to [0, 1] range. Detects if values are in [0, 255]."""
    if not frame or not frame[0]:
        return frame
    max_val = 0.0
    for row in frame:
        for v in row:
            if v > max_val:
                max_val = v
    if max_val > 1.0:
        scale = 1.0 / max_val
        return [[v * scale for v in row] for row in frame]
    return frame

def _compute_psnr_frame(frame, ref_frame):
    """Compute PSNR for a single frame pair. Returns (psnr_value, heatmap_frame)."""
    if not frame or not ref_frame:
        return 0.0, frame
    mse = 0.0
    heatmap = []
    total_pixels = 0
    for i, row in enumerate(frame):
        heat_row = []
        for j, v in enumerate(row):
            rv = ref_frame[i][j] if i < len(ref_frame) and j < len(ref_frame[i]) else 0.0
            diff = v - rv
            mse += diff * diff
            heat_row.append(abs(diff))
            total_pixels += 1
        heatmap.append(heat_row)
    if total_pixels == 0:
        return 0.0, heatmap
    mse /= total_pixels
    if mse == 0:
        return 100.0, heatmap
    psnr = 10.0 * math.log10(1.0 / mse)
    return psnr, heatmap

def _compute_ssim_frame(frame, ref_frame):
    """Compute a simplified SSIM for a single frame pair. Returns (ssim_value, heatmap_frame)."""
    if not frame or not ref_frame:
        return 0.0, frame
    c1 = (0.01 * 1.0) ** 2
    c2 = (0.03 * 1.0) ** 2
    total_pixels = 0
    ssim_sum = 0.0
    heatmap = []
    for i, row in enumerate(frame):
        heat_row = []
        for j, v in enumerate(row):
            rv = ref_frame[i][j] if i < len(ref_frame) and j < len(ref_frame[i]) else 0.0
            # Simplified: treat each pixel as its own window
            mu_x = v
            mu_y = rv
            sigma_x = 0.0
            sigma_y = 0.0
            sigma_xy = 0.0
            num = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
            den = (mu_x ** 2 + mu_y ** 2 + c1) * (sigma_x ** 2 + sigma_y ** 2 + c2)
            if den == 0:
                ssim_val = 1.0
            else:
                ssim_val = num / den
            ssim_sum += ssim_val
            heat_row.append(1.0 - ssim_val)  # Difference from perfect similarity
            total_pixels += 1
        heatmap.append(heat_row)
    if total_pixels == 0:
        return 0.0, heatmap
    return ssim_sum / total_pixels, heatmap

def _compute_lpips_frame(frame, ref_frame):
    """Compute a simplified LPIPS-like metric for a single frame pair.
    Uses weighted L1 distance as a proxy for perceptual difference.
    Returns (lpips_value, heatmap_frame). Lower is better."""
    if not frame or not ref_frame:
        return 0.0, frame
    total_pixels = 0
    lpips_sum = 0.0
    heatmap = []
    for i, row in enumerate(frame):
        heat_row = []
        for j, v in enumerate(row):
            rv = ref_frame[i][j] if i < len(ref_frame) and j < len(ref_frame[i]) else 0.0
            diff = abs(v - rv)
            # Weight by a simple perceptual curve (emphasize mid-range differences)
            weight = 1.0 + 0.5 * math.sin(math.pi * (v + rv) / 2.0)
            lpips_sum += diff * weight
            heat_row.append(diff * weight)
            total_pixels += 1
        heatmap.append(heat_row)
    if total_pixels == 0:
        return 0.0, heatmap
    return lpips_sum / total_pixels, heatmap

def compute_metric(frames, reference, metric):
    """Compute the specified metric across all frames.
    
    Args:
        frames: List of frames (list of list of floats).
        reference: List of reference frames (list of list of floats).
        metric: One of "psnr", "ssim", "lpips".
    
    Returns:
        (average_metric, heatmap) where heatmap is a list of frames.
    """
    if metric not in METRICS:
        raise ValueError(f"Unknown metric: {metric}. Must be one of {METRICS}")
    if not frames or not reference:
        return 0.0, frames if frames else []
    if len(frames) != len(reference):
        raise ValueError("Number of frames must match number of reference frames")
    
    frames_norm = [_normalize_frame(f) for f in frames]
    ref_norm = [_normalize_frame(f) for f in reference]
    
    values = []
    heatmaps = []
    for i in range(len(frames_norm)):
        if metric == "psnr":
            val, heat = _compute_psnr_frame(frames_norm[i], ref_norm[i])
        elif metric == "ssim":
            val, heat = _compute_ssim_frame(frames_norm[i], ref_norm[i])
        else:  # lpips
            val, heat = _compute_lpips_frame(frames_norm[i], ref_norm[i])
        values.append(val)
        heatmaps.append(heat)
    
    if not values:
        return 0.0, heatmaps
    avg = sum(values) / len(values)
    return avg, heatmaps

class PSN_VideoQualityMetric:
    """Calculates quality metrics for video frames (pure logic, no GPU)."""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frames": ("LIST", {"default": []}),
                "reference": ("LIST", {"default": []}),
                "metric": (METRICS,),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("FLOAT", "LIST")
    RETURN_NAMES = ("average_metric", "heatmap")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Video"
    
    def run(self, frames, reference, metric):
        avg, heatmap = compute_metric(frames, reference, metric)
        return (avg, heatmap)

NODE_CLASS_MAPPINGS = {"PSN_VideoQualityMetric": PSN_VideoQualityMetric}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_VideoQualityMetric": "PSN Video Quality Metric"}
