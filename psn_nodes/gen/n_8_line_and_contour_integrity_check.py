"""PSN_CV_LineIntegrity - Line and Contour Integrity Check.

Detects straight lines and closes gaps in broken contours to validate the
structural integrity of technical drawings.

Pipeline (pure torch + numpy, CPU):
  1. If the input is not binary, binarise it with a Canny-style edge
     detector (Sobel gradients + non-maximum suppression + hysteresis).
  2. Detect contours (8-connected boundary tracing).
  3. Identify endpoints of broken line segments (pixels with exactly one
     8-neighbour).
  4. Draw lines between nearby endpoints (within ``gap_threshold``).
  5. Count resulting straight lines with a Hough transform.

Outputs:
  * ``cleaned_image``  - IMAGE [B,H,W,C] with gaps closed (white lines on
    black background, values in 0..1).
  * ``line_count``     - INT, number of straight lines found by Hough.
  * ``integrity_score``- FLOAT in 0..1, fraction of endpoints that were
    successfully bridged (1.0 = no open endpoints remain).
"""

import math

import numpy as np
import torch

CAT = "ParametricStudio/CV"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _as_np(image: torch.Tensor) -> np.ndarray:
    """IMAGE [B,H,W,C] float 0..1 -> (B,H,W) float64 in 0..1 (copy)."""
    if not torch.is_tensor(image):
        raise TypeError("image must be a torch tensor")
    if image.dim() != 4 or image.shape[3] < 1:
        raise ValueError("image must have shape [B,H,W,C]")
    x = image.detach().to(torch.float32).cpu().numpy().astype(np.float64)
    x = np.clip(x, 0.0, 1.0)
    if x.shape[3] == 1:
        return x[:, :, :, 0].copy()
    # grayscale via Rec.601 luma
    g = 0.299 * x[:, :, :, 0] + 0.587 * x[:, :, :, 1] + 0.114 * x[:, :, :, 2]
    # take the first batch element (line drawings are single-frame)
    return g[0].copy()


def _to_image(mask: np.ndarray) -> torch.Tensor:
    """(H,W) 0/1 mask -> IMAGE [1,H,W,3] float32 0..1."""
    m = (mask > 0).astype(np.float32)
    t = torch.from_numpy(m)[None, :, :, None].repeat(1, 1, 1, 3)
    return t


# ---------------------------------------------------------------------------
# Canny-style edge detection (torch-free, numpy)
# ---------------------------------------------------------------------------

def _sobel(g: np.ndarray):
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    ky = kx.T.copy()
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    for i in range(1, g.shape[0] - 1):
        for j in range(1, g.shape[1] - 1):
            patch = g[i - 1:i + 2, j - 1:j + 2]
            gx[i, j] = float(np.dot(patch.ravel(), kx.ravel()))
            gy[i, j] = float(np.dot(patch.ravel(), ky.ravel()))
    return gx, gy


def _canny(g: np.ndarray, low: float = 20.0, high: float = 50.0) -> np.ndarray:
    """Canny edge detector on a grayscale image (0..1). Returns 0/1 mask."""
    h, w = g.shape
    if h < 3 or w < 3:
        return np.zeros((h, w), dtype=np.int32)
    # normalise gradient scale: g is 0..1 so gradients are small
    gx, gy = _sobel(g)
    mag = np.sqrt(gx * gx + gy * gy) * 255.0
    ang = np.arctan2(gy, gx)
    # non-maximum suppression
    nms = np.zeros_like(mag)
    for i in range(1, h - 1):
        for j in range(1, w - 1):
            a = (ang[i, j] * 180.0 / math.pi) % 180.0
            m = mag[i, j]
            if 22.5 <= a < 67.5:  # ~135 deg
                c1, c2 = mag[i - 1, j + 1], mag[i + 1, j - 1]
            elif 67.5 <= a < 112.5:  # ~0 deg
                c1, c2 = mag[i, j - 1], mag[i, j + 1]
            elif 112.5 <= a < 157.5:  # ~45 deg
                c1, c2 = mag[i - 1, j - 1], mag[i + 1, j + 1]
            else:  # ~90 deg
                c1, c2 = mag[i - 1, j], mag[i + 1, j]
            if m >= c1 and m >= c2:
                nms[i, j] = m
    # hysteresis
    strong = nms >= high
    weak = (nms >= low) & (~strong)
    out = np.zeros((h, w), dtype=np.int32)
    out[strong] = 1
    # propagate weak connected to strong (8-conn BFS)
    stack = np.argwhere(strong)
    seen = strong.copy()
    while stack.size:
        i, j = stack[-1].tolist()
        stack = stack[:-1]
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                ni, nj = i + di, j + dj
                if 0 <= ni < h and 0 <= nj < w and weak[ni, nj] and not seen[ni, nj]:
                    seen[ni, nj] = True
                    out[ni, nj] = 1
                    stack = np.vstack([stack, [[ni, nj]]]) if stack.size else np.array([[ni, nj]])
    return out


# ---------------------------------------------------------------------------
# binarisation
# ---------------------------------------------------------------------------

def _binarise(g: np.ndarray, use_canny: bool) -> np.ndarray:
    """Return a 0/1 edge mask. If ``use_canny`` is False, simple threshold."""
    if use_canny:
        return _canny(g)
    # Otsu-lite: threshold at 0.5 of the max (works for line drawings)
    t = 0.5 * float(g.max()) if g.max() > 0 else 0.5
    return (g >= t).astype(np.int32)


# ---------------------------------------------------------------------------
# endpoints & gap closing
# ---------------------------------------------------------------------------

def _endpoints(mask: np.ndarray):
    """Pixels with exactly one 8-neighbour (line endpoints)."""
    h, w = mask.shape
    eps = []
    for i in range(h):
        for j in range(w):
            if not mask[i, j]:
                continue
            n = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < h and 0 <= nj < w and mask[ni, nj]:
                        n += 1
            if n == 1:
                eps.append((i, j))
    return eps


def _draw_line(mask: np.ndarray, p0, p1):
    """Bresenham line on a copy-safe mask (mutates in place, caller copies)."""
    i0, j0 = p0
    i1, j1 = p1
    di = abs(i1 - i0)
    dj = -abs(j1 - j0)
    si = 1 if i0 < i1 else -1
    sj = 1 if j0 < j1 else -1
    err = di + dj
    while True:
        mask[i0, j0] = 1
        if i0 == i1 and j0 == j1:
            break
        e2 = 2 * err
        if e2 >= dj:
            err += dj
            i0 += si
        if e2 <= di:
            err += di
            j0 += sj


def _close_gaps(mask: np.ndarray, gap_threshold: int):
    """Bridge endpoints within ``gap_threshold`` pixels.

    Returns (new_mask, bridged, total) where ``total`` is the number of open
    endpoints present in the *original* mask and ``bridged`` is the number of
    those endpoints that were successfully closed.  ``integrity_score`` is
    ``bridged / total`` (1.0 when there are no open endpoints).
    """
    out = mask.copy()
    total = len(_endpoints(out))
    bridged = 0
    while True:
        eps = _endpoints(out)
        if len(eps) < 2:
            break
        used = [False] * len(eps)
        progress = False
        for a in range(len(eps)):
            if used[a]:
                continue
            ia, ja = eps[a]
            best = -1
            bestd = gap_threshold + 1
            for b in range(a + 1, len(eps)):
                if used[b]:
                    continue
                ib, jb = eps[b]
                d = math.hypot(ia - ib, ja - jb)
                if d <= gap_threshold and d < bestd:
                    bestd = d
                    best = b
            if best >= 0:
                _draw_line(out, eps[a], eps[best])
                used[a] = True
                used[best] = True
                bridged += 2  # both endpoints of the pair are closed
                progress = True
        if not progress:
            break
    return out, bridged, total


# ---------------------------------------------------------------------------
# Hough line counting (standard accumulator, no cv2)
# ---------------------------------------------------------------------------

def _hough_count(mask: np.ndarray, min_line_length: int) -> int:
    """Count distinct straight lines via a theta/rho Hough transform."""
    h, w = mask.shape
    pts = np.argwhere(mask)
    if len(pts) < max(2, min_line_length):
        return 0
    diag = math.hypot(h, w)
    thetas = np.arange(0, 180, 1, dtype=np.float64)  # 1 deg resolution
    cos_t = np.cos(np.deg2rad(thetas))
    sin_t = np.sin(np.deg2rad(thetas))
    rho_max = int(math.ceil(diag))
    acc = np.zeros((2 * rho_max + 1, len(thetas)), dtype=np.int32)
    for i, j in pts:
        r = i * sin_t + j * cos_t + rho_max
        r = np.clip(np.round(r).astype(np.int64), 0, 2 * rho_max)
        acc[r, np.arange(len(thetas))] += 1
    # peak threshold: a line of length L votes in L cells
    thr = max(3, min_line_length)
    peaks = np.argwhere(acc >= thr)
    if len(peaks) == 0:
        return 0
    # non-maximum suppression in (rho, theta) space
    peaks = peaks.tolist()
    peaks.sort(key=lambda p: -acc[p[0], p[1]])
    kept = []
    for p in peaks:
        r, t = p
        dup = False
        for kr, kt in kept:
            dr = abs(r - kr)
            dt = abs(t - kt)
            if dt > 90:
                dt = 180 - dt
            if dr <= 3 and dt <= 3:
                dup = True
                break
        if not dup:
            kept.append((r, t))
    return len(kept)


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------

class PSN_CV_LineIntegrity:
    """Detect straight lines and close gaps in broken contours (technical drawings)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "gap_threshold": ("INT", {"default": 8, "min": 0, "max": 256}),
                "min_line_length": ("INT", {"default": 10, "min": 2, "max": 4096}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "FLOAT")
    RETURN_NAMES = ("cleaned_image", "line_count", "integrity_score")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, gap_threshold, min_line_length):
        g = _as_np(image)
        # decide binary vs grayscale: if >95% of pixels are near 0 or near 1
        flat = g.ravel()
        binary_frac = float(np.mean((flat < 0.05) | (flat > 0.95)))
        use_canny = binary_frac < 0.95
        mask = _binarise(g, use_canny)
        cleaned, bridged, total = _close_gaps(mask, int(gap_threshold))
        lines = _hough_count(cleaned, int(min_line_length))
        score = 1.0 if total == 0 else float(bridged) / float(total)
        return (_to_image(cleaned), int(lines), float(score))


NODE_CLASS_MAPPINGS = {"PSN_CV_LineIntegrity": PSN_CV_LineIntegrity}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_CV_LineIntegrity": "CV Line Integrity Check"}
