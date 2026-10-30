"""Tests for psn_nodes.gen.psn_bm3d_denoise (pure-logic BM3D control node)."""

import math

from psn_nodes.gen.psn_bm3d_denoise import (
    PSN_BM3D_Denoise,
    _soft_threshold,
    _hard_threshold,
    _dct1d,
    _idct1d,
    _dct2d,
    _idct2d,
    _extract_patches,
    _reassemble,
    _psnr,
    _validate,
    _vram_estimate,
)


def _make_image(h, w, fn):
    return [[fn(r, c) for c in range(w)] for r in range(h)]


def test_soft_threshold_zero_and_sign():
    assert _soft_threshold(0.0, 0.5) == 0.0
    assert _soft_threshold(0.3, 0.5) == 0.0
    assert abs(_soft_threshold(0.8, 0.5) - 0.3) < 1e-9
    assert abs(_soft_threshold(-0.8, 0.5) - (-0.3)) < 1e-9
    assert _soft_threshold(1.0, 0.0) == 1.0  # lam=0 passthrough


def test_hard_threshold():
    assert _hard_threshold(0.3, 0.5) == 0.0
    assert _hard_threshold(0.8, 0.5) == 0.8
    assert _hard_threshold(-0.8, 0.5) == -0.8
    assert _hard_threshold(0.5, 0.5) == 0.0  # strict >


def test_dct1d_roundtrip():
    vec = [1.0, 2.0, 3.0, 4.0]
    f = _dct1d(vec)
    back = _idct1d(f)
    for a, b in zip(vec, back):
        assert abs(a - b) < 1e-9


def test_dct2d_roundtrip():
    block = [[1.0, 2.0], [3.0, 4.0]]
    f = _dct2d(block)
    back = _idct2d(f)
    for r in range(2):
        for c in range(2):
            assert abs(block[r][c] - back[r][c]) < 1e-9


def test_extract_and_reassemble_identity():
    img = _make_image(8, 8, lambda r, c: float((r * 8 + c) % 5))
    bs = 4
    stride = 2
    patches = _extract_patches(img, bs, stride)
    out = _reassemble(patches, bs, stride, 8, 8)
    for r in range(8):
        for c in range(8):
            assert abs(img[r][c] - out[r][c]) < 1e-9


def test_psnr_identical_is_inf_and_noisy_is_finite():
    a = _make_image(4, 4, lambda r, c: 0.5)
    assert _psnr(a, a) == float("inf")
    b = _make_image(4, 4, lambda r, c: 0.5 + 0.1)
    p = _psnr(a, b)
    assert math.isfinite(p) and p > 0


def test_validate_bad_inputs():
    assert _validate(-1.0, 4, 0.01, 8, 8)[0] is False
    assert _validate(0.1, 1, 0.01, 8, 8)[0] is False  # block_size < 2
    assert _validate(0.1, 4, -0.1, 8, 8)[0] is False  # nbd < 0
    assert _validate(0.1, 4, 0.01, 2, 2)[0] is False  # too small
    assert _validate(0.1, 4, 0.01, 8, 8)[0] is True
    assert _validate(True, 4, 0.01, 8, 8)[0] is False  # bool not a number


def test_vram_estimate_positive_and_scales():
    small = _vram_estimate(8, 8, 4, 0.01)
    big = _vram_estimate(16, 16, 4, 0.01)
    assert small > 0 and big > small


def test_node_run_ok_and_denoise_changes_image():
    node = PSN_BM3D_Denoise()
    # noisy image: constant + small noise
    img = _make_image(8, 8, lambda r, c: 0.5 + 0.05 * ((r * 3 + c * 7) % 3 - 1))
    denoised, psnr, reason, vram_ok = node.run(
        sigma=0.1, block_size=4, nbd_threshold=0.01, image=img,
        threshold_mode="soft", vram_budget_bytes=0,
    )
    assert vram_ok is True
    assert reason == "ok"
    assert isinstance(denoised, list) and len(denoised) == 8
    assert math.isfinite(psnr)
    # denoised should be closer to the constant 0.5 than the noisy input
    def mean_abs_to_const(m):
        s = 0.0
        for row in m:
            for v in row:
                s += abs(v - 0.5)
        return s / (8 * 8)
    assert mean_abs_to_const(denoised) <= mean_abs_to_const(img) + 1e-9


def test_node_run_vram_budget_exceeded():
    node = PSN_BM3D_Denoise()
    img = _make_image(8, 8, lambda r, c: 0.5)
    denoised, psnr, reason, vram_ok = node.run(
        sigma=0.1, block_size=4, nbd_threshold=0.01, image=img,
        threshold_mode="soft", vram_budget_bytes=1,  # tiny budget
    )
    assert vram_ok is False
    assert reason == "vram budget exceeded"
    assert denoised is img  # passthrough on refusal


def test_node_run_bad_image_passthrough():
    node = PSN_BM3D_Denoise()
    denoised, psnr, reason, vram_ok = node.run(
        sigma=0.1, block_size=4, nbd_threshold=0.01, image="not-an-image",
    )
    assert vram_ok is False
    assert denoised == "not-an-image"
    assert "image" in reason


def test_node_run_image_too_small():
    node = PSN_BM3D_Denoise()
    img = _make_image(2, 2, lambda r, c: 0.5)
    denoised, psnr, reason, vram_ok = node.run(
        sigma=0.1, block_size=4, nbd_threshold=0.01, image=img,
    )
    assert vram_ok is False
    assert "block_size" in reason
