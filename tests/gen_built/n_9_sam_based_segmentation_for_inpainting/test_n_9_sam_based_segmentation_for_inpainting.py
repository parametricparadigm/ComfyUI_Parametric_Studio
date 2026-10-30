"""Tests for n_9_sam_based_segmentation_for_inpainting.py"""

import torch
import json

from n_9_sam_based_segmentation_for_inpainting import (
    PSN_SAM_Segmenter,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_image,
    _parse_points,
    _parse_box,
    _point_mask,
    _box_mask,
    _auto_mask,
)

node = PSN_SAM_Segmenter()

# --- 1. Basic point-mode segmentation: mask shape matches image ---
img = torch.rand(1, 64, 64, 3)  # [B,H,W,C]
mask, seg = node.run(img, "[32, 32]", "Point", "")
assert mask.shape == (1, 64, 64), f"mask shape {mask.shape} != (1,64,64)"
assert seg.shape == (1, 64, 64, 3), f"seg shape {seg.shape}"
assert mask.dtype == torch.float32
assert seg.dtype == torch.float32

# --- 2. Mask values are binary (0 or 1) and non-empty ---
assert set(mask.unique().tolist()) <= {0.0, 1.0}, "mask must be binary"
assert mask.sum() > 0, "mask must have some foreground pixels"

# --- 3. Segmented image: outside mask is zero, inside matches original ---
mask_bc = mask.unsqueeze(-1)
outside = (1 - mask_bc) > 0
assert (seg[outside.expand_as(seg)] == 0).all(), "outside mask must be zero"
inside = mask_bc > 0
assert torch.allclose(seg[inside.expand_as(seg)], img[inside.expand_as(seg)]), \
    "inside mask must match original"

# --- 4. Box mode: rectangular mask ---
mask_box, seg_box = node.run(img, "[10, 10, 50, 50]", "Box", "")
assert mask_box.shape == (1, 64, 64)
# The box region should be fully 1
assert mask_box[0, 10:51, 10:51].min() == 1.0, "box interior must be 1"
# Outside the box should be 0
assert mask_box[0, 0:10, :].max() == 0.0, "above box must be 0"
assert mask_box[0, 51:, :].max() == 0.0, "below box must be 0"

# --- 5. Auto mode with no points: centre disk ---
mask_auto, _ = node.run(img, "[]", "Auto", "")
assert mask_auto.shape == (1, 64, 64)
assert mask_auto.sum() > 0, "auto mode must produce a non-empty mask"
# Centre pixel should be in the mask
assert mask_auto[0, 32, 32] == 1.0, "centre pixel should be masked in auto mode"

# --- 6. Batch > 1: mask replicates across batch ---
img_b = torch.rand(3, 32, 32, 3)
mask_b, seg_b = node.run(img_b, "[16, 16]", "Point", "")
assert mask_b.shape == (3, 32, 32)
assert seg_b.shape == (3, 32, 32, 3)
# All batch items should have the same mask
assert torch.equal(mask_b[0], mask_b[1]), "batch masks must be identical"
assert torch.equal(mask_b[1], mask_b[2]), "batch masks must be identical"

# --- 7. Bad input: wrong dimensionality raises ValueError ---
try:
    node.run(torch.rand(64, 64, 3), "[32, 32]", "Point", "")  # 3D, not 4D
    assert False, "should have raised ValueError"
except ValueError:
    pass

# --- 8. Bad input: out-of-range values raise ValueError ---
try:
    bad_img = torch.rand(1, 16, 16, 3) * 2.0  # values up to 2
    node.run(bad_img, "[8, 8]", "Point", "")
    assert False, "should have raised ValueError for out-of-range"
except ValueError:
    pass

# --- 9. Bad input: invalid JSON string raises ValueError ---
try:
    node.run(img, "not valid json", "Point", "")
    assert False, "should have raised ValueError for bad JSON"
except ValueError:
    pass

# --- 10. Bad input: Box mode with wrong number of points ---
try:
    node.run(img, "[10, 10]", "Box", "")  # only 1 point, need 2
    assert False, "should have raised ValueError for box with 1 point"
except ValueError:
    pass

# --- 11. _parse_points: flat list and nested list both work ---
pts_flat = _parse_points([10, 20, 30, 40])
assert pts_flat == [(10, 20), (30, 40)], f"flat parse: {pts_flat}"
pts_nested = _parse_points([[10, 20], [30, 40]])
assert pts_nested == [(10, 20), (30, 40)], f"nested parse: {pts_nested}"

# --- 12. _parse_points: odd-length flat list raises ---
try:
    _parse_points([1, 2, 3])
    assert False, "should have raised for odd-length flat list"
except ValueError:
    pass

# --- 13. _parse_points: NaN raises ---
try:
    _parse_points([float('nan'), 5])
    assert False, "should have raised for NaN"
except ValueError:
    pass

# --- 14. _box_mask: clamps to image bounds ---
m = _box_mask(32, 32, (-10, -10, 50, 50))
assert m.shape == (32, 32)
assert m.max() == 1.0
assert m.sum() == 32 * 32, "clamped box should cover entire image"

# --- 15. _point_mask: empty points gives all-zero mask ---
m_empty = _point_mask(16, 16, [])
assert m_empty.shape == (16, 16)
assert m_empty.sum() == 0.0

# --- 16. Input is not modified in place ---
img_orig = torch.rand(1, 32, 32, 3)
img_copy = img_orig.clone()
_, _ = node.run(img_orig, "[16, 16]", "Point", "")
assert torch.equal(img_orig, img_copy), "input image must not be modified"

# --- 17. Module-level mappings exist and are correct ---
assert "PSN_SAM_Segmenter" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_SAM_Segmenter"] is PSN_SAM_Segmenter
assert "PSN_SAM_Segmenter" in NODE_DISPLAY_NAME_MAPPINGS
assert PSN_SAM_Segmenter.RETURN_TYPES == ("MASK", "IMAGE")
assert PSN_SAM_Segmenter.RETURN_NAMES == ("mask", "segmented_image")
assert PSN_SAM_Segmenter.FUNCTION == "run"
assert PSN_SAM_Segmenter.CATEGORY == "ParametricStudio/Segmentation"

# --- 18. INPUT_TYPES has required fields ---
it = PSN_SAM_Segmenter.INPUT_TYPES()
assert "required" in it
for key in ("image", "point_coords", "mask_mode", "sam_model_path"):
    assert key in it["required"], f"missing input: {key}"

print('ok')
