"""ParametricStudio - Stable Motion Correction.

Two ComfyUI nodes:

* PSN_VideoStabilizer - removes camera shake from a video batch using a
  pure-torch optical-flow estimate (block matching on downsampled
  grayscale frames), a moving-average global-motion smoother and an
  inverse affine warp.  No cv2 dependency: the flow is computed with
  torch ops only, which keeps the node portable to CPU.

* PSN_TimelineStabilizer - resamples a variable-timing video batch to a
  constant target FPS using linear interpolation between neighbouring
  frames (frame duplication when the target rate is lower than the
  source rate, blending when it is higher).

Both nodes are pure torch (CPU friendly) and never modify their inputs
in place.
"""

import math

import torch

CAT = "ParametricStudio/Motion"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _as_image(img):
    """Validate an IMAGE tensor and return a float32 copy in [0, 1]."""
    if not isinstance(img, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if img.dim() != 4:
        raise ValueError("IMAGE must be a 4D tensor [B, H, W, C], got %dD" % img.dim())
    if img.shape[-1] not in (1, 3, 4):
        raise ValueError("IMAGE channels must be 1, 3 or 4, got %d" % img.shape[-1])
    x = img.detach().to(torch.float32).clone()
    return x


def _clamp01(x):
    return torch.clamp(x, 0.0, 1.0)


def _to_gray(x):
    """[B,H,W,C] -> [B,H,W] float32 in [0,1]."""
    c = x.shape[-1]
    if c == 1:
        return x[..., 0]
    if c == 3:
        return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
    return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]


def _downsample(g, target_h, target_w):
    """Nearest-neighbour resize of a [B,H,W] tensor to [B,target_h,target_w]."""
    b, h, w = g.shape
    if h == target_h and w == target_w:
        return g
    ys = (torch.arange(target_h, dtype=torch.float32) * (h - 1) / max(target_h - 1, 1)).long()
    xs = (torch.arange(target_w, dtype=torch.float32) * (w - 1) / max(target_w - 1, 1)).long()
    return g[:, ys][:, :, xs]


def _optical_flow(prev, curr, search=3, win=3):
    """Block-matching optical flow between two grayscale frames.

    prev, curr : [B,H,W] float32 in [0,1]
    returns    : (fx, fy) each [B,H,W] float32, displacement in pixels
                 (fx = x displacement, fy = y displacement).
    """
    b, h, w = prev.shape
    fx = torch.zeros(b, h, w, dtype=torch.float32)
    fy = torch.zeros(b, h, w, dtype=torch.float32)
    half = win // 2
    for bi in range(b):
        p = prev[bi]
        c = curr[bi]
        for y in range(half, h - half):
            for x in range(half, w - half):
                patch = p[y - half:y + half + 1, x - half:x + half + 1]
                best_dx, best_dy = 0, 0
                best_err = float("inf")
                for dy in range(-search, search + 1):
                    ny = y + dy
                    if ny - half < 0 or ny + half >= h:
                        continue
                    for dx in range(-search, search + 1):
                        nx = x + dx
                        if nx - half < 0 or nx + half >= w:
                            continue
                        cand = c[ny - half:ny + half + 1, nx - half:nx + half + 1]
                        err = float(((patch - cand) ** 2).mean())
                        if err < best_err:
                            best_err = err
                            best_dx, best_dy = dx, dy
                fx[bi, y, x] = best_dx
                fy[bi, y, x] = best_dy
    return fx, fy


def _global_translation(prev, curr, search=4):
    """Estimate the global translation (dx, dy) between two grayscale frames
    by exhaustive search over a small displacement grid, using the mean
    squared difference of the overlapping region as the cost.

    prev, curr : [H,W] float32 in [0,1]
    returns    : (dx, dy) float, displacement in pixels.
    """
    h, w = prev.shape
    best_dx, best_dy = 0, 0
    best_err = float("inf")
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            # overlap region in prev coordinates
            y0 = max(0, dy)
            y1 = min(h, h + dy)
            x0 = max(0, dx)
            x1 = min(w, w + dx)
            if y1 <= y0 or x1 <= x0:
                continue
            a = prev[y0:y1, x0:x1]
            b_ = curr[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
            err = float(((a - b_) ** 2).mean())
            if err < best_err:
                best_err = err
                best_dx, best_dy = dx, dy
    return best_dx, best_dy


def _smooth_window(v, window):
    """Centered moving average over a 1-D tensor (edge clamped)."""
    if window <= 1:
        return v.clone()
    n = v.numel()
    half = window // 2
    out = torch.zeros_like(v)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        out[i] = v[lo:hi].mean()
    return out


def _warp_image(x, dx, dy):
    """Inverse affine warp of [B,H,W,C] by per-pixel displacement (dx,dy).

    The output pixel (y,x) is sampled from (y+dy, x+dx) of the input with
    bilinear interpolation and zero padding outside the frame.
    """
    b, h, w, c = x.shape
    gy, gx = torch.meshgrid(
        torch.arange(h, dtype=torch.float32),
        torch.arange(w, dtype=torch.float32),
        indexing="ij",
    )
    sx = gx[None].expand(b, h, w) + dx
    sy = gy[None].expand(b, h, w) + dy
    x0 = torch.floor(sx).long()
    y0 = torch.floor(sy).long()
    x1 = x0 + 1
    y1 = y0 + 1
    wx = sx - x0.float()
    wy = sy - y0.float()

    def _sample(xx, yy):
        xx = xx.clamp(0, w - 1)
        yy = yy.clamp(0, h - 1)
        return x[torch.arange(b)[:, None, None].expand(b, h, w), yy, xx]

    i00 = _sample(x0, y0)
    i10 = _sample(x1, y0)
    i01 = _sample(x0, y1)
    i11 = _sample(x1, y1)
    wx = wx[..., None]
    wy = wy[..., None]
    top = i00 * (1 - wx) + i10 * wx
    bot = i01 * (1 - wx) + i11 * wx
    out = top * (1 - wy) + bot * wy
    mask = (sx < 0) | (sx > w - 1) | (sy < 0) | (sy > h - 1)
    out = torch.where(mask[..., None], torch.zeros_like(out), out)
    return out


# ---------------------------------------------------------------------------
# node 1: video stabilizer
# ---------------------------------------------------------------------------

class PSN_VideoStabilizer:
    """Remove camera shake from a video batch using optical flow + inverse warp."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
                "smoothing": ("INT", {"default": 5, "min": 1, "max": 63}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, strength, smoothing):
        x = _as_image(image)
        b, h, w, c = x.shape
        if b < 2:
            # nothing to stabilize with a single frame
            return (_clamp01(x),)
        if not (0.0 <= strength <= 1.0):
            raise ValueError("strength must be in [0, 1]")
        if smoothing < 1:
            raise ValueError("smoothing must be >= 1")

        gray = _to_gray(x)
        # downsample for a cheap global-motion estimate
        th = max(8, h // 4)
        tw = max(8, w // 4)
        g_small = _downsample(gray, th, tw)

        # global translation per transition (exhaustive search on small frames)
        gx = torch.zeros(b - 1, dtype=torch.float32)
        gy = torch.zeros(b - 1, dtype=torch.float32)
        for i in range(b - 1):
            dx, dy = _global_translation(g_small[i], g_small[i + 1], search=4)
            gx[i] = dx
            gy[i] = dy
        # smooth the per-transition motion, then re-derive the cumulative
        # displacement so that the first frame stays anchored at the origin
        # (this is what actually removes the shake from the output).
        gx = _smooth_window(gx, smoothing)
        gy = _smooth_window(gy, smoothing)
        cum_x = torch.zeros(b, dtype=torch.float32)
        cum_y = torch.zeros(b, dtype=torch.float32)
        for i in range(1, b):
            cum_x[i] = cum_x[i - 1] + gx[i - 1]
            cum_y[i] = cum_y[i - 1] + gy[i - 1]
        # subtract the mean so the stabilized clip is centred (avoids the
        # "drunk" drift that pure cumulative smoothing can produce)
        cum_x = cum_x - cum_x.mean()
        cum_y = cum_y - cum_y.mean()

        scale = strength
        out = torch.empty_like(x)
        for i in range(b):
            dx = torch.full((h, w), -cum_x[i] * scale, dtype=torch.float32)
            dy = torch.full((h, w), -cum_y[i] * scale, dtype=torch.float32)
            out[i] = _warp_image(x[i:i + 1], dx[None], dy[None])[0]
        return (_clamp01(out),)


# ---------------------------------------------------------------------------
# node 2: timeline stabilizer
# ---------------------------------------------------------------------------

class PSN_TimelineStabilizer:
    """Resample a video batch to a constant target frame rate.

    The input batch is assumed to be evenly spaced at ``src_fps``.  The
    output contains ``round(duration * fps) + 1`` frames where each
    output frame is a linear blend of the two surrounding source frames,
    which removes timing jitter without duplicating whole frames.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 240.0, "step": 0.5}),
                "src_fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 240.0, "step": 0.5}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, fps, src_fps):
        x = _as_image(image)
        b, h, w, c = x.shape
        if b < 1:
            raise ValueError("image batch must contain at least one frame")
        if fps <= 0 or src_fps <= 0:
            raise ValueError("fps and src_fps must be positive")

        duration = (b - 1) / src_fps if b > 1 else 0.0
        if duration <= 0:
            return (_clamp01(x),)
        n_out = max(1, int(round(duration * fps)) + 1)
        if n_out == b and math.isclose(fps, src_fps, rel_tol=1e-6):
            return (_clamp01(x),)

        out = torch.empty(n_out, h, w, c, dtype=torch.float32)
        for i in range(n_out):
            t = i / fps
            s = t * src_fps
            i0 = int(math.floor(s))
            i1 = min(i0 + 1, b - 1)
            i0 = max(0, min(i0, b - 1))
            frac = s - i0
            if i0 == i1 or frac <= 0:
                out[i] = x[i0]
            else:
                out[i] = x[i0] * (1.0 - frac) + x[i1] * frac
        return (_clamp01(out),)


NODE_CLASS_MAPPINGS = {
    "PSN_VideoStabilizer": PSN_VideoStabilizer,
    "PSN_TimelineStabilizer": PSN_TimelineStabilizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VideoStabilizer": "PSN Video Stabilizer (Motion Correction)",
    "PSN_TimelineStabilizer": "PSN Timeline Stabilizer (FPS Resample)",
}
