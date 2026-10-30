"""Tests for PSN_FashionItemSegmenter."""

import torch
from n_7_fashion_item_segmentation import (
    PSN_FashionItemSegmenter,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _make_image(h=32, w=32, color=(0.0, 0.0, 0.0)):
    """Create a solid-color image tensor [1, H, W, 3]."""
    img = torch.zeros(1, h, w, 3)
    img[..., 0] = color[0]
    img[..., 1] = color[1]
    img[..., 2] = color[2]
    return img


def _make_shoe_image(h=32, w=32):
    """Create an image with a red 'shoe' region in the center."""
    img = torch.zeros(1, h, w, 3)
    # Red shoe: high R, low G, low B
    img[0, 8:24, 8:24, 0] = 0.9
    img[0, 8:24, 8:24, 1] = 0.1
    img[0, 8:24, 8:24, 2] = 0.1
    return img


def _make_bag_image(h=32, w=32):
    """Create an image with a brown 'bag' region."""
    img = torch.zeros(1, h, w, 3)
    # Brown: moderate R, low-moderate G, low B
    img[0, 10:22, 10:22, 0] = 0.6
    img[0, 10:22, 10:22, 1] = 0.35
    img[0, 10:22, 10:22, 2] = 0.15
    return img


def _make_dress_image(h=32, w=32):
    """Create an image with a colorful 'dress' region."""
    img = torch.zeros(1, h, w, 3)
    # Blue dress: low R, low G, high B
    img[0, 5:27, 5:27, 0] = 0.1
    img[0, 5:27, 5:27, 1] = 0.2
    img[0, 5:27, 5:27, 2] = 0.9
    return img


def test_module_mappings():
    """NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS exist and are correct."""
    assert "PSN_FashionItemSegmenter" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_FashionItemSegmenter"] is PSN_FashionItemSegmenter
    assert "PSN_FashionItemSegmenter" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_FashionItemSegmenter"], str)


def test_input_types():
    """INPUT_TYPES has required image and item_type."""
    it = PSN_FashionItemSegmenter.INPUT_TYPES()
    assert "required" in it
    assert "image" in it["required"]
    assert "item_type" in it["required"]
    assert it["required"]["image"] == ("IMAGE",)
    assert it["required"]["item_type"][0] == ["shoes", "bags", "dresses", "all"]


def test_return_types():
    """RETURN_TYPES and RETURN_NAMES are correct."""
    assert PSN_FashionItemSegmenter.RETURN_TYPES == ("MASK", "BBOX")
    assert PSN_FashionItemSegmenter.RETURN_NAMES == ("mask", "bounding_boxes")
    assert PSN_FashionItemSegmenter.FUNCTION == "run"
    assert PSN_FashionItemSegmenter.CATEGORY == "ParametricStudio/Segmentation"


def test_shoe_segmentation():
    """Segment a synthetic red shoe image; mask should cover the shoe region."""
    node = PSN_FashionItemSegmenter()
    img = _make_shoe_image(32, 32)
    mask, bboxes = node.run(img, "shoes")

    # Mask shape
    assert mask.shape == (1, 32, 32)
    assert mask.dtype == torch.float32

    # Mask should have non-zero pixels in the shoe region
    shoe_region = mask[0, 8:24, 8:24]
    assert shoe_region.sum() > 0, "mask should cover the shoe region"

    # Mask should be zero (or near-zero) outside the shoe region
    outside = mask[0, 0:8, 0:8]
    assert outside.sum() == 0, "mask should be zero outside the shoe"

    # Bounding box
    assert len(bboxes) == 1
    bb = bboxes[0]
    assert bb["x"] >= 8 and bb["x"] < 24
    assert bb["y"] >= 8 and bb["y"] < 24
    assert bb["width"] > 0 and bb["height"] > 0
    assert bb["item_type"] == "shoes"


def test_bag_segmentation():
    """Segment a synthetic brown bag image."""
    node = PSN_FashionItemSegmenter()
    img = _make_bag_image(32, 32)
    mask, bboxes = node.run(img, "bags")

    assert mask.shape == (1, 32, 32)
    bag_region = mask[0, 10:22, 10:22]
    assert bag_region.sum() > 0, "mask should cover the bag region"

    assert len(bboxes) == 1
    bb = bboxes[0]
    assert bb["width"] > 0 and bb["height"] > 0
    assert bb["item_type"] == "bags"


def test_dress_segmentation():
    """Segment a synthetic blue dress image."""
    node = PSN_FashionItemSegmenter()
    img = _make_dress_image(32, 32)
    mask, bboxes = node.run(img, "dresses")

    assert mask.shape == (1, 32, 32)
    dress_region = mask[0, 5:27, 5:27]
    assert dress_region.sum() > 0, "mask should cover the dress region"

    assert len(bboxes) == 1
    bb = bboxes[0]
    assert bb["width"] > 0 and bb["height"] > 0
    assert bb["item_type"] == "dresses"


def test_all_items():
    """Segment with item_type='all' on a multi-color image."""
    node = PSN_FashionItemSegmenter()
    img = _make_shoe_image(32, 32)
    mask, bboxes = node.run(img, "all")

    assert mask.shape == (1, 32, 32)
    assert mask.sum() > 0, "mask should have some pixels for 'all'"
    assert len(bboxes) == 1


def test_empty_image():
    """A fully black image should produce an empty mask and zero-size bbox."""
    node = PSN_FashionItemSegmenter()
    img = _make_image(16, 16, (0.0, 0.0, 0.0))
    mask, bboxes = node.run(img, "shoes")

    assert mask.shape == (1, 16, 16)
    assert mask.sum() == 0, "mask should be all zeros for black image"
    assert len(bboxes) == 1
    bb = bboxes[0]
    assert bb["width"] == 0 and bb["height"] == 0


def test_bad_image_shape():
    """Invalid image shape should raise ValueError."""
    node = PSN_FashionItemSegmenter()
    bad = torch.zeros(1, 32, 32, 4)  # wrong channel count
    try:
        node.run(bad, "shoes")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_image_type():
    """Non-tensor image should raise ValueError."""
    node = PSN_FashionItemSegmenter()
    try:
        node.run("not a tensor", "shoes")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_item_type():
    """Invalid item_type should raise ValueError."""
    node = PSN_FashionItemSegmenter()
    img = _make_shoe_image(16, 16)
    try:
        node.run(img, "hats")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_batch():
    """Batch of 2 images should produce mask [2, H, W] and 2 bboxes."""
    node = PSN_FashionItemSegmenter()
    img1 = _make_shoe_image(16, 16)
    img2 = _make_bag_image(16, 16)
    batch = torch.cat([img1, img2], dim=0)  # [2, 16, 16, 3]
    mask, bboxes = node.run(batch, "all")

    assert mask.shape == (2, 16, 16)
    assert len(bboxes) == 2


def test_no_inplace_modification():
    """Input image should not be modified in place."""
    node = PSN_FashionItemSegmenter()
    img = _make_shoe_image(16, 16)
    img_copy = img.clone()
    node.run(img, "shoes")
    assert torch.equal(img, img_copy), "input image was modified in place"


if __name__ == "__main__":
    test_module_mappings()
    test_input_types()
    test_return_types()
    test_shoe_segmentation()
    test_bag_segmentation()
    test_dress_segmentation()
    test_all_items()
    test_empty_image()
    test_bad_image_shape()
    test_bad_image_type()
    test_bad_item_type()
    test_batch()
    test_no_inplace_modification()
    print("ok")
