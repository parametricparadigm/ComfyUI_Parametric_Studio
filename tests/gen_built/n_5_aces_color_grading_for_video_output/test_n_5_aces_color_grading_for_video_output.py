"""Tests for PSN_OCIO_Color_Grade (ACES color grading for video output)."""

import torch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_5_aces_color_grading_for_video_output import (
    PSN_OCIO_Color_Grade,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _srgb_to_linear,
    _linear_to_srgb,
    _aces_rrt,
    _aces_sdr_tonemap,
    _convert_colorspace,
    _apply_lut_adjustment,
    _grade_frames,
    _normalize_cs,
)


def test_module_structure():
    """Test that module-level mappings exist and are correct."""
    assert "PSN_OCIO_Color_Grade" in NODE_CLASS_MAPPINGS
    assert "PSN_OCIO_Color_Grade" in NODE_DISPLAY_NAME_MAPPINGS
    node_cls = NODE_CLASS_MAPPINGS["PSN_OCIO_Color_Grade"]
    assert node_cls.FUNCTION == "run"
    assert node_cls.RETURN_TYPES == ("IMAGE",)
    assert node_cls.RETURN_NAMES == ("image",)
    assert node_cls.CATEGORY == "ParametricStudio/ColorGrading"
    it = node_cls.INPUT_TYPES()
    assert "required" in it
    assert "image" in it["required"]
    assert it["required"]["image"] == ("IMAGE",)
    assert "input_colorspace" in it["required"]
    assert "output_colorspace" in it["required"]
    assert "optional" in it
    assert "lut_name" in it["optional"]
    print("  PASS: module structure")


def test_srgb_roundtrip():
    """sRGB -> linear -> sRGB should be approximately identity."""
    x = torch.tensor([[0.0, 0.18, 0.5, 1.0]], dtype=torch.float32)
    lin = _srgb_to_linear(x)
    back = _linear_to_srgb(lin)
    assert torch.allclose(x, back, atol=1e-5), f"sRGB roundtrip failed: {x} vs {back}"
    print("  PASS: sRGB gamma roundtrip")


def test_identity_conversion():
    """Converting from a colorspace to itself should be identity."""
    x = torch.rand(4, 3, dtype=torch.float32)
    out = _convert_colorspace(x, "sRGB", "sRGB")
    assert torch.allclose(x, out, atol=1e-6)
    out2 = _convert_colorspace(x, "ACEScg", "ACEScg")
    assert torch.allclose(x, out2, atol=1e-6)
    print("  PASS: identity color space conversion")


def test_srgb_to_acescg_matrix():
    """Verify sRGB->ACEScg matrix produces expected values for a known input."""
    white = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)
    out = _convert_colorspace(white, "sRGB", "ACEScg")
    assert out.shape == (1, 3)
    assert out[0, 0].item() > 0.5, f"R too low: {out[0,0].item()}"
    assert out[0, 0].item() < 2.0, f"R too high: {out[0,0].item()}"
    assert out[0, 1].item() > 0.5, f"G too low: {out[0,1].item()}"
    assert out[0, 2].item() > 0.5, f"B too low: {out[0,2].item()}"
    print("  PASS: sRGB->ACEScg matrix conversion")


def test_aces_rrt_behavior():
    """RRT should be ~identity in midtones and compress highlights."""
    mid = torch.tensor([[0.5]], dtype=torch.float32)
    out_mid = _aces_rrt(mid)
    assert abs(out_mid[0, 0].item() - 0.5) < 0.1, f"RRT midtone too far: {out_mid[0,0].item()}"
    hi = torch.tensor([[2.0]], dtype=torch.float32)
    out_hi = _aces_rrt(hi)
    assert out_hi[0, 0].item() < 2.0, f"RRT should compress highlights: {out_hi[0,0].item()}"
    assert out_hi[0, 0].item() > 0.0
    zero = torch.tensor([[0.0]], dtype=torch.float32)
    out_zero = _aces_rrt(zero)
    assert abs(out_zero[0, 0].item()) < 1e-6
    print("  PASS: ACES RRT behavior")


def test_full_pipeline_srgb_to_srgb():
    """Full pipeline sRGB->sRGB should produce valid output in [0,1]."""
    node = PSN_OCIO_Color_Grade()
    img = torch.rand(2, 4, 4, 3, dtype=torch.float32)
    out = node.run(img, "sRGB", "sRGB")
    assert isinstance(out, tuple)
    assert len(out) == 1
    result = out[0]
    assert result.shape == (2, 4, 4, 3), f"Wrong shape: {result.shape}"
    assert result.dtype == torch.float32
    assert result.min().item() >= 0.0, f"Output below 0: {result.min().item()}"
    assert result.max().item() <= 1.0, f"Output above 1: {result.max().item()}"
    print("  PASS: full pipeline sRGB->sRGB")


def test_full_pipeline_srgb_to_acescg():
    """sRGB -> ACEScg should produce linear output (no gamma)."""
    node = PSN_OCIO_Color_Grade()
    img = torch.rand(1, 8, 8, 3, dtype=torch.float32)
    out = node.run(img, "sRGB", "ACEScg")
    result = out[0]
    assert result.shape == (1, 8, 8, 3)
    assert result.min().item() >= 0.0
    assert result.max().item() <= 1.0
    print("  PASS: full pipeline sRGB->ACEScg")


def test_lut_warm_vs_cool():
    """Warm LUT should boost reds, cool should boost blues."""
    x = torch.tensor([[0.5, 0.5, 0.5]], dtype=torch.float32)
    warm = _apply_lut_adjustment(x, "warm")
    cool = _apply_lut_adjustment(x, "cool")
    assert warm[0, 0].item() > warm[0, 2].item(), f"Warm: R {warm[0,0].item()} should > B {warm[0,2].item()}"
    assert cool[0, 2].item() > cool[0, 0].item(), f"Cool: B {cool[0,2].item()} should > R {cool[0,0].item()}"
    print("  PASS: warm vs cool LUT")


def test_lut_identity():
    """Identity/empty LUT should not change values."""
    x = torch.rand(10, 3, dtype=torch.float32)
    out = _apply_lut_adjustment(x, "")
    assert torch.allclose(x, out)
    out2 = _apply_lut_adjustment(x, "identity")
    assert torch.allclose(x, out2)
    out3 = _apply_lut_adjustment(x, "none")
    assert torch.allclose(x, out3)
    print("  PASS: identity LUT")


def test_bad_input_not_tensor():
    """Should raise TypeError for non-tensor input."""
    node = PSN_OCIO_Color_Grade()
    try:
        node.run("not a tensor", "sRGB", "sRGB")
        assert False, "Should have raised TypeError"
    except TypeError:
        pass
    print("  PASS: bad input (not tensor) raises TypeError")


def test_bad_input_wrong_dims():
    """Should raise ValueError for wrong number of dimensions."""
    node = PSN_OCIO_Color_Grade()
    bad = torch.rand(4, 4, 3, dtype=torch.float32)
    try:
        node.run(bad, "sRGB", "sRGB")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  PASS: bad input (wrong dims) raises ValueError")


def test_bad_input_wrong_channels():
    """Should raise ValueError for wrong channel count."""
    node = PSN_OCIO_Color_Grade()
    bad = torch.rand(1, 4, 4, 4, dtype=torch.float32)
    try:
        node.run(bad, "sRGB", "sRGB")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  PASS: bad input (wrong channels) raises ValueError")


def test_bad_input_empty_batch():
    """Should raise ValueError for empty batch."""
    node = PSN_OCIO_Color_Grade()
    bad = torch.rand(0, 4, 4, 3, dtype=torch.float32)
    try:
        node.run(bad, "sRGB", "sRGB")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  PASS: bad input (empty batch) raises ValueError")


def test_no_inplace_modification():
    """Input tensor should not be modified in place."""
    node = PSN_OCIO_Color_Grade()
    img = torch.rand(2, 4, 4, 3, dtype=torch.float32)
    img_copy = img.clone()
    node.run(img, "sRGB", "ACEScg", lut_name="warm")
    assert torch.allclose(img, img_copy), "Input was modified in place!"
    print("  PASS: no in-place modification")


def test_normalize_cs():
    """Color space name normalization."""
    assert _normalize_cs("sRGB") == "srgb"
    assert _normalize_cs("Srgb") == "srgb"
    assert _normalize_cs("ACEScg") == "acescg"
    assert _normalize_cs("ACES2065-1") == "aces"
    assert _normalize_cs("aces_2065_1") == "aces"
    print("  PASS: color space name normalization")


def test_video_batch():
    """Test with a larger video-like batch (10 frames)."""
    node = PSN_OCIO_Color_Grade()
    img = torch.rand(10, 16, 16, 3, dtype=torch.float32)
    out = node.run(img, "sRGB", "sRGB", lut_name="film")
    result = out[0]
    assert result.shape == (10, 16, 16, 3)
    assert result.min().item() >= 0.0
    assert result.max().item() <= 1.0
    assert not torch.allclose(result[0], result[1]), "Different frames should differ"
    print("  PASS: video batch (10 frames)")


def test_acescg_to_srgb():
    """ACEScg -> sRGB should produce gamma-encoded output."""
    node = PSN_OCIO_Color_Grade()
    img = torch.rand(1, 4, 4, 3, dtype=torch.float32) * 0.5
    out = node.run(img, "ACEScg", "sRGB")
    result = out[0]
    assert result.shape == (1, 4, 4, 3)
    assert result.min().item() >= 0.0
    assert result.max().item() <= 1.0
    print("  PASS: ACEScg->sRGB pipeline")


def test_sdr_tonemap():
    """SDR tonemap should compress highlights and be monotonic."""
    x = torch.tensor([[0.0, 0.25, 0.5, 0.75, 1.0, 2.0]], dtype=torch.float32)
    out = _aces_sdr_tonemap(x)
    assert out[0, 5].item() < 2.0, f"Tonemap should compress: {out[0,5].item()}"
    assert abs(out[0, 0].item()) < 1e-5
    for i in range(5):
        assert out[0, i+1].item() >= out[0, i].item() - 1e-6, "Tonemap not monotonic"
    print("  PASS: SDR tonemap")


if __name__ == "__main__":
    print("Running tests for PSN_OCIO_Color_Grade...")
    test_module_structure()
    test_srgb_roundtrip()
    test_identity_conversion()
    test_srgb_to_acescg_matrix()
    test_aces_rrt_behavior()
    test_full_pipeline_srgb_to_srgb()
    test_full_pipeline_srgb_to_acescg()
    test_lut_warm_vs_cool()
    test_lut_identity()
    test_bad_input_not_tensor()
    test_bad_input_wrong_dims()
    test_bad_input_wrong_channels()
    test_bad_input_empty_batch()
    test_no_inplace_modification()
    test_normalize_cs()
    test_video_batch()
    test_acescg_to_srgb()
    test_sdr_tonemap()
    print("ok")
