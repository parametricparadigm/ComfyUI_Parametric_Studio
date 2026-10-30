"""Tests for n_10_region_based_local_editing.py"""

import json
import math

import torch

from n_10_region_based_local_editing import (
    PSN_RegionDefinition,
    PSN_LocalEditComposite,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _img(b=1, h=8, w=8, c=3, val=0.5):
    return torch.full((b, h, w, c), val, dtype=torch.float32)


def test_module_mappings():
    assert "PSN_RegionDefinition" in NODE_CLASS_MAPPINGS
    assert "PSN_LocalEditComposite" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_RegionDefinition"]
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_LocalEditComposite"]


def test_rectangle_mask():
    node = PSN_RegionDefinition()
    img = _img(1, 10, 10, 3)
    (mask,) = node.run(img, "rectangle", "[2, 3, 5, 7]")
    assert mask.shape == (1, 10, 10)
    # Inside the rectangle
    assert mask[0, 3, 2] == 1.0
    assert mask[0, 7, 5] == 1.0
    # Outside
    assert mask[0, 0, 0] == 0.0
    assert mask[0, 9, 9] == 0.0
    # Count: (5-2+1)*(7-3+1) = 4*5 = 20
    assert mask.sum().item() == 20.0


def test_ellipse_mask():
    node = PSN_RegionDefinition()
    img = _img(1, 11, 11, 3)
    (mask,) = node.run(img, "ellipse", "[5, 5, 3, 4]")
    assert mask.shape == (1, 11, 11)
    # Centre is inside
    assert mask[0, 5, 5] == 1.0
    # Far corner is outside
    assert mask[0, 0, 0] == 0.0
    # Point on the ellipse boundary (cx+rx, cy) -> (8,5)
    assert mask[0, 5, 8] == 1.0
    # Point just outside (cx+rx+1, cy) -> (9,5)
    assert mask[0, 5, 9] == 0.0


def test_polygon_mask():
    node = PSN_RegionDefinition()
    img = _img(1, 10, 10, 3)
    # Triangle: (1,1), (9,1), (1,9)
    coords = json.dumps([[1, 1], [9, 1], [1, 9]])
    (mask,) = node.run(img, "polygon", coords)
    assert mask.shape == (1, 10, 10)
    # Inside the triangle
    assert mask[0, 2, 2] == 1.0
    # Outside (top-right corner)
    assert mask[0, 1, 9] == 0.0
    # Outside (bottom-right)
    assert mask[0, 9, 9] == 0.0


def test_bad_coords():
    node = PSN_RegionDefinition()
    img = _img(1, 8, 8, 3)
    # Not valid JSON
    try:
        node.run(img, "rectangle", "not json at all")
        assert False, "should have raised"
    except ValueError:
        pass
    # Wrong number of coords for rectangle
    try:
        node.run(img, "rectangle", "[1, 2]")
        assert False, "should have raised"
    except ValueError:
        pass
    # Unknown region type
    try:
        node.run(img, "circle", "[1,1,1]")
        assert False, "should have raised"
    except ValueError:
        pass


def test_composite_full_size():
    node = PSN_LocalEditComposite()
    orig = _img(1, 8, 8, 3, val=0.0)
    edit = _img(1, 8, 8, 3, val=1.0)
    mask = torch.zeros(1, 8, 8)
    mask[0, 2:5, 2:5] = 1.0  # 3x3 block
    (out,) = node.run(orig, edit, mask)
    assert out.shape == (1, 8, 8, 3)
    # Inside mask: should be 1.0 (from edit)
    assert out[0, 3, 3, 0].item() == 1.0
    # Outside mask: should be 0.0 (from orig)
    assert out[0, 0, 0, 0].item() == 0.0


def test_composite_small_region():
    node = PSN_LocalEditComposite()
    orig = _img(1, 16, 16, 3, val=0.0)
    # 4x4 edited region
    edit = _img(1, 4, 4, 3, val=1.0)
    mask = torch.zeros(1, 16, 16)
    mask[0, 0:4, 0:4] = 1.0
    (out,) = node.run(orig, edit, mask)
    assert out.shape == (1, 16, 16, 3)
    # Top-left 4x4 should be 1.0
    assert out[0, 0, 0, 0].item() == 1.0
    assert out[0, 3, 3, 0].item() == 1.0
    # Rest should be 0.0
    assert out[0, 5, 5, 0].item() == 0.0


def test_composite_bad_input():
    node = PSN_LocalEditComposite()
    orig = _img(1, 8, 8, 3)
    edit = _img(1, 8, 8, 3)
    # Mask with wrong spatial size
    bad_mask = torch.zeros(1, 4, 4)
    try:
        node.run(orig, edit, bad_mask)
        assert False, "should have raised"
    except ValueError:
        pass
    # Edited region larger than original
    big_edit = _img(1, 16, 16, 3)
    mask = torch.zeros(1, 8, 8)
    try:
        node.run(orig, big_edit, mask)
        assert False, "should have raised"
    except ValueError:
        pass


def test_batch_mask():
    node = PSN_RegionDefinition()
    img = _img(2, 6, 6, 3)
    (mask,) = node.run(img, "rectangle", "[0, 0, 2, 2]")
    assert mask.shape == (2, 6, 6)
    # Both batch entries should have the same mask
    assert mask[0].eq(mask[1]).all().item()
    assert mask[0, 1, 1].item() == 1.0


def test_no_inplace_modification():
    node = PSN_LocalEditComposite()
    orig = _img(1, 8, 8, 3, val=0.0)
    edit = _img(1, 8, 8, 3, val=1.0)
    mask = torch.zeros(1, 8, 8)
    mask[0, 0:4, 0:4] = 1.0
    orig_copy = orig.clone()
    edit_copy = edit.clone()
    mask_copy = mask.clone()
    node.run(orig, edit, mask)
    assert torch.equal(orig, orig_copy)
    assert torch.equal(edit, edit_copy)
    assert torch.equal(mask, mask_copy)


if __name__ == "__main__":
    test_module_mappings()
    test_rectangle_mask()
    test_ellipse_mask()
    test_polygon_mask()
    test_bad_coords()
    test_composite_full_size()
    test_composite_small_region()
    test_composite_bad_input()
    test_batch_mask()
    test_no_inplace_modification()
    print("ok")
