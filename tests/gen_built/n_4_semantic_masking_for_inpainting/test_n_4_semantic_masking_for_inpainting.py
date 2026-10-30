"""Tests for n_4_semantic_masking_for_inpainting.py"""

import torch
from n_4_semantic_masking_for_inpainting import (
    PSN_Semantic_Mask_Gen,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _as_image,
    _as_mask,
    _foreground_score,
    _morphology,
)

node = PSN_Semantic_Mask_Gen()

# ---------------------------------------------------------------------------
# 1. Basic shape and type check
# ---------------------------------------------------------------------------
img = torch.rand(1, 8, 8, 3)  # small 8x8 RGB image
mask, conf = node.run(img, class_id=0, confidence_threshold=0.5, morphology_radius=0)
assert isinstance(mask, torch.Tensor), "mask must be a Tensor"
assert isinstance(conf, torch.Tensor), "conf must be a Tensor"
assert mask.shape == (1, 8, 8), f"mask shape {mask.shape} != (1,8,8)"
assert conf.shape == (1, 8, 8, 1), f"conf shape {conf.shape} != (1,8,8,1)"
assert mask.dtype == torch.float32
assert conf.dtype == torch.float32

# ---------------------------------------------------------------------------
# 2. Mask is binary (0 or 1)
# ---------------------------------------------------------------------------
unique = mask.unique()
assert set(unique.tolist()).issubset({0.0, 1.0}), f"mask not binary: {unique.tolist()}"

# ---------------------------------------------------------------------------
# 3. Confidence map is in [0, 1]
# ---------------------------------------------------------------------------
assert conf.min() >= 0.0 and conf.max() <= 1.0, "conf out of [0,1]"

# ---------------------------------------------------------------------------
# 4. Bright-object prior: a bright pixel should be foreground at low threshold
# ---------------------------------------------------------------------------
# Create an image that is mostly dark with one bright pixel.
img2 = torch.zeros(1, 4, 4, 3)
img2[0, 2, 2, :] = 1.0  # bright pixel at (2,2)
mask2, _ = node.run(img2, class_id=1, confidence_threshold=0.9, morphology_radius=0)
assert mask2[0, 2, 2] == 1.0, "bright pixel should be foreground"
# Most other pixels should be background
assert mask2[0, 0, 0] == 0.0, "dark pixel should be background"

# ---------------------------------------------------------------------------
# 5. Dark-object prior: a dark pixel should be foreground
# ---------------------------------------------------------------------------
img3 = torch.ones(1, 4, 4, 3)  # all bright
img3[0, 1, 1, :] = 0.0  # one dark pixel
mask3, _ = node.run(img3, class_id=2, confidence_threshold=0.9, morphology_radius=0)
assert mask3[0, 1, 1] == 1.0, "dark pixel should be foreground for class_id=2"
assert mask3[0, 0, 0] == 0.0, "bright pixel should be background for class_id=2"

# ---------------------------------------------------------------------------
# 6. Saturated-object prior: a colourful pixel should be foreground
# ---------------------------------------------------------------------------
img4 = torch.zeros(1, 4, 4, 3)  # all black (low saturation)
img4[0, 3, 3, 0] = 1.0  # pure red (high saturation)
mask4, _ = node.run(img4, class_id=3, confidence_threshold=0.5, morphology_radius=0)
assert mask4[0, 3, 3] == 1.0, "saturated pixel should be foreground for class_id=3"

# ---------------------------------------------------------------------------
# 7. Morphology: erosion shrinks a mask, dilation grows it
# ---------------------------------------------------------------------------
# Create a 5x5 mask with a 3x3 block of 1s in the centre.
m = torch.zeros(1, 5, 5)
m[0, 1:4, 1:4] = 1.0
m_eroded = _morphology(m, "erode", 1)
m_dilated = _morphology(m, "dilate", 1)
# After erosion the centre pixel should still be 1, but corners of the block should be 0.
assert m_eroded[0, 2, 2] == 1.0, "centre should survive erosion"
assert m_eroded[0, 1, 1] == 0.0, "corner of block should be eroded"
# After dilation the block should be larger.
assert m_dilated[0, 0, 0] == 1.0, "dilation should grow the mask"

# ---------------------------------------------------------------------------
# 8. Bad input: wrong number of dimensions
# ---------------------------------------------------------------------------
try:
    _as_image(torch.rand(8, 8, 3))  # 3-D, not 4-D
    assert False, "should have raised"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 9. Bad input: wrong channel count
# ---------------------------------------------------------------------------
try:
    _as_image(torch.rand(1, 8, 8, 5))  # 5 channels
    assert False, "should have raised"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 10. Bad input: non-tensor
# ---------------------------------------------------------------------------
try:
    _as_image("not a tensor")
    assert False, "should have raised"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 11. Bad class_id
# ---------------------------------------------------------------------------
try:
    node.run(img, class_id=99, confidence_threshold=0.5, morphology_radius=0)
    assert False, "should have raised for bad class_id"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 12. Bad confidence_threshold
# ---------------------------------------------------------------------------
try:
    node.run(img, class_id=0, confidence_threshold=1.5, morphology_radius=0)
    assert False, "should have raised for bad threshold"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 13. Node registration
# ---------------------------------------------------------------------------
assert "PSN_Semantic_Mask_Gen" in NODE_CLASS_MAPPINGS
assert "PSN_Semantic_Mask_Gen" in NODE_DISPLAY_NAME_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Semantic_Mask_Gen"] is PSN_Semantic_Mask_Gen

# ---------------------------------------------------------------------------
# 14. INPUT_TYPES structure
# ---------------------------------------------------------------------------
it = PSN_Semantic_Mask_Gen.INPUT_TYPES()
assert "required" in it
assert "image" in it["required"]
assert "class_id" in it["required"]
assert "confidence_threshold" in it["required"]

# ---------------------------------------------------------------------------
# 15. Batch > 1
# ---------------------------------------------------------------------------
img_batch = torch.rand(3, 6, 6, 3)
mask_b, conf_b = node.run(img_batch, class_id=0, confidence_threshold=0.5, morphology_radius=0)
assert mask_b.shape == (3, 6, 6)
assert conf_b.shape == (3, 6, 6, 1)

# ---------------------------------------------------------------------------
# 16. Grayscale image (1 channel)
# ---------------------------------------------------------------------------
img_gray = torch.rand(1, 5, 5, 1)
mask_g, conf_g = node.run(img_gray, class_id=0, confidence_threshold=0.5, morphology_radius=0)
assert mask_g.shape == (1, 5, 5)
assert conf_g.shape == (1, 5, 5, 1)

# ---------------------------------------------------------------------------
# 17. RGBA image (4 channels)
# ---------------------------------------------------------------------------
img_rgba = torch.rand(1, 5, 5, 4)
mask_r, conf_r = node.run(img_rgba, class_id=0, confidence_threshold=0.5, morphology_radius=0)
assert mask_r.shape == (1, 5, 5)
assert conf_r.shape == (1, 5, 5, 1)

# ---------------------------------------------------------------------------
# 18. Input is not modified in place
# ---------------------------------------------------------------------------
img_orig = torch.rand(1, 4, 4, 3)
img_copy = img_orig.clone()
node.run(img_orig, class_id=0, confidence_threshold=0.5, morphology_radius=0)
assert torch.equal(img_orig, img_copy), "input image was modified in place"

# ---------------------------------------------------------------------------
# 19. All-zero image -> all-background mask (generic prior)
# ---------------------------------------------------------------------------
img_zero = torch.zeros(1, 4, 4, 3)
mask_z, _ = node.run(img_zero, class_id=0, confidence_threshold=0.5, morphology_radius=0)
# With all-zero luminance, deviation from median is 0, so score is 0 < 0.5
assert mask_z.sum() == 0.0, "all-zero image should give all-background mask"

# ---------------------------------------------------------------------------
# 20. All-ones image -> all-background mask (generic prior)
# ---------------------------------------------------------------------------
img_one = torch.ones(1, 4, 4, 3)
mask_o, _ = node.run(img_one, class_id=0, confidence_threshold=0.5, morphology_radius=0)
assert mask_o.sum() == 0.0, "all-ones image should give all-background mask"

print("ok")
