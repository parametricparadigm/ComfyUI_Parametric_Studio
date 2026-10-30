"""PSN_BM3D_Denoise — pure-logic, secure-by-design control plane for a BM3D denoise step.

This module does NOT run the GPU/torch/cupy BM3D pipeline (no torch, no ComfyUI,
no network, no file/OS access). It implements only the deterministic, CPU-safe
parts of the spec:

  * config validation (sigma / block_size / nbd_threshold / image shape),
  * a soft-thresholding helper (the core BM3D shrinkage op),
  * a small pure-Python 1-D DCT-II (used to build the 2-D DCT for the
    "3D FFT -> threshold -> inverse" step, implemented as a DCT for clarity),
  * a patch-extraction / reassembly helper,
  * a PSNR metric,
  * a VRAM-guard estimate (bytes) so the real node can refuse to run when the
    estimated working-set exceeds a budget (the "PSN_VRAM_Guard" risk).

The real GPU node would call these helpers to validate its inputs and to
compute the soft-thresholded coefficients; the heavy patch-grouping / 3D-FFT
work stays on the GPU and is intentionally out of scope here.
"""

import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Image"

# ComfyUI uses the string "ANY" as a type marker; we mirror that here.
ANY = "ANY"

# Soft-thresholding modes (mirrors the gate-style "mode" convention).
THRESH_MODES = ("soft", "hard", "none")


def _soft_threshold(x, lam):
    """Soft-threshold a single coefficient: sign(x) * max(|x|-lam, 0)."""
    if lam <= 0.0:
        return x
    ax = abs(x)
    if ax <= lam:
        return 0.0
    return (x - lam) if x > 0 else (x + lam)


def _hard_threshold(x, lam):
    """Hard-threshold: keep x if |x| > lam else 0."""
    if lam <= 0.0:
        return x
    return x if abs(x) > lam else 0.0


def _dct1d(vec):
    """1-D DCT-II (orthonormal-ish, unnormalized) of a list of floats."""
    n = len(vec)
    out = []
    for k in range(n):
        s = 0.0
        for i in range(n):
            s += vec[i] * math.cos(math.pi * (2 * i + 1) * k / (2 * n))
        out.append(s)
    return out


def _idct1d(vec):
    """Inverse of _dct1d (DCT-II inverse), returns the original (scaled)."""
    n = len(vec)
    out = []
    for i in range(n):
        s = vec[0] * 0.5
        for k in range(1, n):
            s += vec[k] * math.cos(math.pi * (2 * i + 1) * k / (2 * n))
        out.append(s * (2.0 / n))
    return out


def _dct2d(block):
    """2-D DCT-II of a square 2-D list (rows x cols)."""
    rows = len(block)
    cols = len(block[0]) if rows else 0
    # transform along columns (each row)
    t = [_dct1d(row) for row in block]
    # transform along rows (each column)
    out = []
    for c in range(cols):
        col = [t[r][c] for r in range(rows)]
        out.append(_dct1d(col))
    # transpose back to row-major
    res = [[out[c][r] for c in range(cols)] for r in range(rows)]
    return res


def _idct2d(block):
    """Inverse 2-D DCT of a square 2-D list."""
    rows = len(block)
    cols = len(block[0]) if rows else 0
    # inverse along columns
    t = []
    for c in range(cols):
        col = [block[r][c] for r in range(rows)]
        t.append(_idct1d(col))
    # t is now col-major; build row-major then inverse along rows
    mid = [[t[c][r] for c in range(cols)] for r in range(rows)]
    res = [_idct1d(row) for row in mid]
    return res


def _extract_patches(image, block_size, stride):
    """Extract overlapping square patches from a 2-D image (list of rows)."""
    h = len(image)
    w = len(image[0]) if h else 0
    patches = []
    for r in range(0, h - block_size + 1, stride):
        for c in range(0, w - block_size + 1, stride):
            patch = []
            for i in range(block_size):
                row = []
                for j in range(block_size):
                    row.append(image[r + i][c + j])
                patch.append(row)
            patches.append((r, c, patch))
    return patches


def _reassemble(patches, block_size, stride, h, w):
    """Average-reassemble patches back into an h x w image."""
    acc = [[0.0] * w for _ in range(h)]
    cnt = [[0] * w for _ in range(h)]
    for (r, c, patch) in patches:
        for i in range(block_size):
            for j in range(block_size):
                acc[r + i][c + j] += patch[i][j]
                cnt[r + i][c + j] += 1
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            row.append(acc[r][c] / cnt[r][c] if cnt[r][c] else 0.0)
        out.append(row)
    return out


def _psnr(clean, noisy, max_val=1.0):
    """Peak signal-to-noise ratio in dB between two 2-D images."""
    h = len(clean)
    w = len(clean[0]) if h else 0
    if h == 0 or w == 0:
        return float("inf")
    mse = 0.0
    for r in range(h):
        for c in range(w):
            d = clean[r][c] - noisy[r][c]
            mse += d * d
    mse /= (h * w)
    if mse <= 0.0:
        return float("inf")
    return 10.0 * math.log10((max_val * max_val) / mse)


def _validate(sigma, block_size, nbd_threshold, h, w):
    """Return (ok, reason). Pure validation, no side effects."""
    if not isinstance(sigma, (int, float)) or isinstance(sigma, bool):
        return False, "sigma must be a number"
    if sigma < 0.0:
        return False, "sigma must be >= 0"
    if not isinstance(block_size, int) or isinstance(block_size, bool):
        return False, "block_size must be an int"
    if block_size < 2:
        return False, "block_size must be >= 2"
    if not isinstance(nbd_threshold, (int, float)) or isinstance(nbd_threshold, bool):
        return False, "nbd_threshold must be a number"
    if nbd_threshold < 0.0:
        return False, "nbd_threshold must be >= 0"
    if h < block_size or w < block_size:
        return False, "image must be at least block_size x block_size"
    return True, "ok"


def _vram_estimate(h, w, block_size, nbd_threshold):
    """Rough working-set estimate in bytes for the GPU patch-grouping step.

    BM3D keeps a 3-D stack of patches; a conservative estimate is
    (num_patches * block_size^2 * 4 bytes) for the stack plus a copy for the
    FFT domain. This is only used to gate on a VRAM budget.
    """
    num_patches = max(0, h - block_size + 1) * max(0, w - block_size + 1)
    stack_bytes = num_patches * (block_size * block_size) * 4
    fft_bytes = stack_bytes  # one extra domain copy
    return stack_bytes + fft_bytes


class PSN_BM3D_Denoise:
    """Pure-logic BM3D denoise control node (no GPU/torch).

    Validates config, computes a soft-thresholded DCT-domain denoise on a
    small pure-Python image, and reports PSNR + VRAM estimate. The real GPU
    node would replace the DCT/patch loop with torch.fft + CUDA patch grouping
    but keep this validation and metric logic.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sigma": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1e9, "step": 0.001}),
                "block_size": ("INT", {"default": 4, "min": 2, "max": 64, "step": 1}),
                "nbd_threshold": ("FLOAT", {"default": 0.01, "min": 0.0, "max": 1e9, "step": 0.001}),
                "image": (ANY,),
            },
            "optional": {
                "threshold_mode": (list(THRESH_MODES),),
                "vram_budget_bytes": ("INT", {"default": 0, "min": 0, "max": 1 << 62, "step": 1}),
            },
        }

    RETURN_TYPES = (ANY, "FLOAT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("denoised_image", "psnr_db", "reason", "vram_ok")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, sigma, block_size, nbd_threshold, image,
            threshold_mode="soft", vram_budget_bytes=0):
        # image is expected to be a 2-D list of floats (pure-logic stand-in
        # for an IMAGE tensor). If it is not, we report and pass through.
        if not isinstance(image, (list, tuple)) or len(image) == 0:
            return (image, 0.0, "image must be a non-empty 2-D list", False)
        h = len(image)
        if not all(isinstance(row, (list, tuple)) for row in image):
            return (image, 0.0, "image rows must be lists", False)
        w = len(image[0])
        if any(len(row) != w for row in image):
            return (image, 0.0, "image rows must be equal length", False)

        ok, why = _validate(sigma, block_size, nbd_threshold, h, w)
        if not ok:
            return (image, 0.0, why, False)

        vram = _vram_estimate(h, w, block_size, nbd_threshold)
        vram_ok = (vram_budget_bytes <= 0) or (vram <= vram_budget_bytes)
        if not vram_ok:
            return (image, 0.0, "vram budget exceeded", False)

        # Pure-Python BM3D-lite: DCT each patch, soft-threshold, inverse DCT.
        stride = max(1, block_size // 2)
        patches = _extract_patches(image, block_size, stride)
        lam = sigma * 0.5  # simple shrinkage level derived from sigma
        denoised_patches = []
        for (r, c, patch) in patches:
            f = _dct2d(patch)
            if threshold_mode == "soft":
                f = [[_soft_threshold(v, lam) for v in row] for row in f]
            elif threshold_mode == "hard":
                f = [[_hard_threshold(v, lam) for v in row] for row in f]
            g = _idct2d(f)
            denoised_patches.append((r, c, g))
        denoised = _reassemble(denoised_patches, block_size, stride, h, w)

        # PSNR vs the (noisy) input is not meaningful without a clean ref;
        # report PSNR of denoised vs input as a stability metric (higher = less change).
        psnr = _psnr(image, denoised, max_val=1.0)
        return (denoised, psnr, "ok", True)


NODE_CLASS_MAPPINGS = {"PSN_BM3D_Denoise": PSN_BM3D_Denoise}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_BM3D_Denoise": "PSN BM3D Denoise (logic)"}
