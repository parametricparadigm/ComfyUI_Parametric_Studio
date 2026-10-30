"""ParametricStudio - High-FPS Temporal Smoothing.

Two nodes:
  * PSN_FrameInterpolator: linearly blends neighbouring frames to synthesise
    intermediate frames (a lightweight stand-in for RIFE; no external model).
  * PSN_FPSResampler: resamples a frame batch to a target FPS using
    nearest-neighbour or linear sampling (drop / duplicate / blend).

Both operate on ComfyUI IMAGE tensors: float [B, H, W, C] in 0..1.
Inputs are never modified in place.
"""

import math

import torch

CAT = "ParametricStudio/Video"


def _as_image(img):
    """Validate and return a float copy of an IMAGE tensor [B,H,W,C]."""
    if not isinstance(img, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if img.dim() != 4:
        raise ValueError("IMAGE must be 4D [B, H, W, C], got %dD" % img.dim())
    if img.shape[-1] not in (1, 3, 4):
        raise ValueError("IMAGE channels must be 1, 3 or 4, got %d" % img.shape[-1])
    if img.shape[0] < 1:
        raise ValueError("IMAGE batch must be >= 1")
    x = img.detach().float().clone()
    return x


def _check_fps(fps, name):
    if not isinstance(fps, (int, float)) or isinstance(fps, bool):
        raise TypeError("%s must be a number" % name)
    fps = float(fps)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("%s must be a positive finite number, got %r" % (name, fps))
    return fps


def _expected_frames(n, source_fps, target_fps):
    """Number of output frames for a resample/interpolation.

    Uses round(n * target / source) with a floor of 1 so that a single
    input frame always yields at least one output frame.
    """
    if n <= 0:
        return 0
    return max(1, int(round(n * target_fps / source_fps)))


class PSN_FrameInterpolator:
    """Increase FPS by synthesising intermediate frames via linear blending.

    This is a dependency-free stand-in for RIFE: for every pair of source
    frames it inserts `k - 1` blended frames, where k is the per-pair
    interpolation factor derived from target_fps / source_fps.  The result
    is a smooth temporal upsample without any learned model.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "source_fps": ("FLOAT", {"default": 24.0, "min": 0.1, "max": 240.0}),
                "target_fps": ("FLOAT", {"default": 48.0, "min": 0.1, "max": 480.0}),
            },
            "optional": {
                "model_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, source_fps, target_fps, model_path=""):
        x = _as_image(image)
        source_fps = _check_fps(source_fps, "source_fps")
        target_fps = _check_fps(target_fps, "target_fps")
        n = x.shape[0]

        ratio = target_fps / source_fps
        if ratio <= 1.0:
            # Nothing to interpolate; return a copy.
            return (x,)

        # Total number of intermediate frames to insert between the n
        # source frames so that the output count matches the expected
        # resampled count n * target_fps / source_fps (rounded).
        m = _expected_frames(n, source_fps, target_fps)
        inserts = m - n  # >= 0 because ratio > 1

        # Distribute the inserts across the n - 1 gaps as evenly as
        # possible (largest-remainder method).
        gaps = n - 1
        base, extra = divmod(inserts, gaps)
        per_gap = [base + (1 if i < extra else 0) for i in range(gaps)]

        out = [x[0]]
        for i in range(gaps):
            a = x[i]
            b = x[i + 1]
            k = per_gap[i]
            for j in range(1, k + 1):
                t = j / float(k + 1)
                out.append(a * (1.0 - t) + b * t)
            out.append(b)

        result = torch.stack(out, dim=0)
        return (result,)


class PSN_FPSResampler:
    """Resample a frame batch to a target FPS (drop / duplicate / blend).

    Uses continuous-time sampling: each output frame index maps to a
    fractional source position `p = i * source_fps / target_fps`.  With
    mode='nearest' the frame at round(p) is taken (drop/duplicate);
    with mode='linear' the two surrounding frames are blended (smoother).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "source_fps": ("FLOAT", {"default": 30.0, "min": 0.1, "max": 240.0}),
                "target_fps": ("FLOAT", {"default": 60.0, "min": 0.1, "max": 480.0}),
                "mode": (["nearest", "linear"],),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, source_fps, target_fps, mode="nearest"):
        x = _as_image(image)
        source_fps = _check_fps(source_fps, "source_fps")
        target_fps = _check_fps(target_fps, "target_fps")
        if mode not in ("nearest", "linear"):
            raise ValueError("mode must be 'nearest' or 'linear', got %r" % (mode,))

        n = x.shape[0]
        m = _expected_frames(n, source_fps, target_fps)
        if m == 0:
            return (x,)

        # Fractional source positions for each output frame.
        step = source_fps / target_fps
        positions = [min(n - 1, i * step) for i in range(m)]

        frames = []
        for p in positions:
            lo = int(math.floor(p))
            hi = min(n - 1, lo + 1)
            t = p - lo
            if mode == "nearest" or t < 1e-9:
                frames.append(x[round(p)])
            else:
                frames.append(x[lo] * (1.0 - t) + x[hi] * t)

        result = torch.stack(frames, dim=0)
        return (result,)


NODE_CLASS_MAPPINGS = {
    "PSN_FrameInterpolator": PSN_FrameInterpolator,
    "PSN_FPSResampler": PSN_FPSResampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FrameInterpolator": "Frame Interpolator (High FPS)",
    "PSN_FPSResampler": "FPS Resampler",
}
