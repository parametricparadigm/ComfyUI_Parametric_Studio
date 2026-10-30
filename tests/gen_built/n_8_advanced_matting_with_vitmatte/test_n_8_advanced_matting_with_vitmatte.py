"""Tests for n_8_advanced_matting_with_vitmatte.py."""

import torch

from n_8_advanced_matting_with_vitmatte import (
    PSN_VitMatteAlpha,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _build_trimap,
    _dilate,
    _erode,
    _diffuse,
    _gaussian_blur,
    _validate_image,
    _validate_mask,
)


def _make_image(b=1, h=32, w=32, c=3):
    """Create a simple gradient image [B,H,W,C] in 0..1."""
    x = torch.linspace(0, 1, w).repeat(b, h, 1)
    img = x.unsqueeze(-1).expand(b, h, w, c)
    return img.contiguous()


def _make_rough_mask(b=1, h=32, w=32):
    """Create a rough mask: a filled circle in the centre."""
    yy, xx = torch.meshgrid(
        torch.linspace(-1, 1, h), torch.linspace(-1, 1, w), indexing="ij"
    )
    r = torch.sqrt(xx ** 2 + yy ** 2)
    mask = (r < 0.5).float()
    return mask.unsqueeze(0).expand(b, h, w).contiguous()


def _grad_mag(x):
    """Mean gradient magnitude of a [B,H,W] tensor (both dims cropped)."""
    gx = x[:, 1:, 1:] - x[:, :-1, 1:]
    gy = x[:, 1:, 1:] - x[:, 1:, :-1]
    return (gx ** 2 + gy ** 2).sqrt().mean().item()


def test_module_mappings():
    """NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS exist and are correct."""
    assert "PSN_VitMatteAlpha" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VitMatteAlpha"] is PSN_VitMatteAlpha
    assert "PSN_VitMatteAlpha" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_VitMatteAlpha"], str)
    assert len(NODE_DISPLAY_NAME_MAPPINGS["PSN_VitMatteAlpha"]) > 0


def test_input_types():
    """INPUT_TYPES has required image and rough_mask, plus optional params."""
    it = PSN_VitMatteAlpha.INPUT_TYPES()
    assert "required" in it
    assert "image" in it["required"]
    assert "rough_mask" in it["required"]
    assert it["required"]["image"] == ("IMAGE",)
    assert it["required"]["rough_mask"] == ("MASK",)
    assert "optional" in it
    assert "fg_radius" in it["optional"]
    assert "iterations" in it["optional"]


def test_return_types():
    """RETURN_TYPES and RETURN_NAMES are correct."""
    assert PSN_VitMatteAlpha.RETURN_TYPES == ("MASK",)
    assert PSN_VitMatteAlpha.RETURN_NAMES == ("alpha_mask",)
    assert PSN_VitMatteAlpha.FUNCTION == "run"
    assert PSN_VitMatteAlpha.CATEGORY.startswith("ParametricStudio/")


def test_basic_matting():
    """Run the node on a simple image + rough mask; check output shape and range."""
    node = PSN_VitMatteAlpha()
    img = _make_image(1, 32, 32, 3)
    mask = _make_rough_mask(1, 32, 32)
    (alpha,) = node.run(img, mask, fg_radius=3, bg_radius=3, iterations=30, sigma=0.5, blur_radius=1)
    assert isinstance(alpha, torch.Tensor)
    assert alpha.shape == (1, 32, 32)
    assert alpha.min() >= 0.0
    assert alpha.max() <= 1.0
    # Centre of the mask should be close to 1 (definite foreground)
    centre = alpha[0, 16, 16]
    assert centre > 0.9, f"centre alpha {centre.item()} should be > 0.9"
    # Corner should be close to 0 (definite background)
    corner = alpha[0, 0, 0]
    assert corner < 0.1, f"corner alpha {corner.item()} should be < 0.1"


def test_alpha_smoothness():
    """The alpha channel should be smoother than the rough mask in the transition zone."""
    node = PSN_VitMatteAlpha()
    img = _make_image(1, 32, 32, 3)
    mask = _make_rough_mask(1, 32, 32)
    (alpha,) = node.run(img, mask, fg_radius=3, bg_radius=3, iterations=50, sigma=0.5, blur_radius=1)
    alpha_grad = _grad_mag(alpha)
    mask_grad = _grad_mag(mask.float())
    # Alpha should be smoother (lower gradient magnitude) than the hard mask
    assert alpha_grad < mask_grad, f"alpha grad {alpha_grad} should be < mask grad {mask_grad}"


def test_batch_processing():
    """Multiple images in a batch should all get alpha masks."""
    node = PSN_VitMatteAlpha()
    img = _make_image(3, 16, 16, 3)
    mask = _make_rough_mask(3, 16, 16)
    (alpha,) = node.run(img, mask, fg_radius=2, bg_radius=2, iterations=20, sigma=0.5, blur_radius=0)
    assert alpha.shape == (3, 16, 16)
    assert alpha.min() >= 0.0
    assert alpha.max() <= 1.0


def test_no_in_place_modification():
    """The input mask must not be modified in place."""
    node = PSN_VitMatteAlpha()
    img = _make_image(1, 32, 32, 3)
    mask = _make_rough_mask(1, 32, 32)
    mask_copy = mask.clone()
    node.run(img, mask, fg_radius=3, bg_radius=3, iterations=10, sigma=0.5, blur_radius=1)
    assert torch.equal(mask, mask_copy), "input mask was modified in place"


def test_bad_image_dim():
    """A 3-D image (missing batch dim) should raise ValueError."""
    node = PSN_VitMatteAlpha()
    bad_img = torch.rand(32, 32, 3)  # missing batch dim
    mask = _make_rough_mask(1, 32, 32)
    try:
        node.run(bad_img, mask)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_mask_size():
    """A mask with wrong spatial size should raise ValueError."""
    node = PSN_VitMatteAlpha()
    img = _make_image(1, 32, 32, 3)
    bad_mask = torch.rand(1, 16, 16)  # wrong size
    try:
        node.run(img, bad_mask)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_mask_range():
    """A mask with values outside [0,1] should raise ValueError."""
    node = PSN_VitMatteAlpha()
    img = _make_image(1, 32, 32, 3)
    bad_mask = torch.rand(1, 32, 32) * 2.0  # values up to 2
    try:
        node.run(img, bad_mask)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_all_zero_mask():
    """An all-zero rough mask should produce an all-zero alpha."""
    node = PSN_VitMatteAlpha()
    img = _make_image(1, 32, 32, 3)
    mask = torch.zeros(1, 32, 32)
    (alpha,) = node.run(img, mask, fg_radius=3, bg_radius=3, iterations=20, sigma=0.5, blur_radius=1)
    assert alpha.max() < 0.05, f"all-zero mask should give near-zero alpha, got max {alpha.max().item()}"


def test_all_ones_mask():
    """An all-ones rough mask should produce an all-ones alpha."""
    node = PSN_VitMatteAlpha()
    img = _make_image(1, 32, 32, 3)
    mask = torch.ones(1, 32, 32)
    (alpha,) = node.run(img, mask, fg_radius=3, bg_radius=3, iterations=20, sigma=0.5, blur_radius=1)
    assert alpha.min() > 0.95, f"all-ones mask should give near-one alpha, got min {alpha.min().item()}"


def test_trimap_construction():
    """Trimap: fg + bg + unknown should cover the whole image."""
    mask = _make_rough_mask(1, 32, 32)
    fg, bg, unknown = _build_trimap(mask, 3, 3)
    total = fg + bg + unknown
    assert torch.allclose(total, torch.ones_like(total)), "trimap parts must sum to 1"
    # fg and bg should not overlap
    assert (fg * bg).sum() == 0, "fg and bg must not overlap"


def test_dilate_erode():
    """Dilation increases the mask, erosion decreases it."""
    mask = _make_rough_mask(1, 32, 32)
    dilated = _dilate(mask, 2)
    eroded = _erode(mask, 2)
    assert dilated.sum() >= mask.sum(), "dilation should not shrink the mask"
    assert eroded.sum() <= mask.sum(), "erosion should not grow the mask"


def test_gaussian_blur():
    """Blurring a sharp edge should reduce the max gradient."""
    mask = torch.zeros(1, 32, 32)
    mask[:, :, 16:] = 1.0  # hard vertical edge
    blurred = _gaussian_blur(mask, 2)
    def grad_max(x):
        gx = x[:, 1:, 1:] - x[:, :-1, 1:]
        gy = x[:, 1:, 1:] - x[:, 1:, :-1]
        return (gx ** 2 + gy ** 2).sqrt().max().item()
    assert grad_max(blurred) < grad_max(mask), "blur should reduce max gradient"


def test_non_tensor_input():
    """Passing a non-tensor image should raise TypeError."""
    node = PSN_VitMatteAlpha()
    mask = _make_rough_mask(1, 32, 32)
    try:
        node.run("not a tensor", mask)
        assert False, "should have raised TypeError"
    except TypeError:
        pass


if __name__ == "__main__":
    test_module_mappings()
    test_input_types()
    test_return_types()
    test_basic_matting()
    test_alpha_smoothness()
    test_batch_processing()
    test_no_in_place_modification()
    test_bad_image_dim()
    test_bad_mask_size()
    test_bad_mask_range()
    test_all_zero_mask()
    test_all_ones_mask()
    test_trimap_construction()
    test_dilate_erode()
    test_gaussian_blur()
    test_non_tensor_input()
    print("ok")
