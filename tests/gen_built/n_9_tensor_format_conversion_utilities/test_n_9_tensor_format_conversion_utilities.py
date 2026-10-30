"""Tests for n_9_tensor_format_conversion_utilities."""

import torch

from n_9_tensor_format_conversion_utilities import (
    PSN_Image_To_Latent,
    PSN_Latent_To_Image,
    PSN_Mask_To_Latent,
    PSN_Latent_To_Mask,
    PSN_Image_To_Mask,
    PSN_Mask_To_Image,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _PseudoVAE,
)

# ---------------------------------------------------------------------------
# 1. Round-trip: Image -> Latent -> Image preserves spatial shape
# ---------------------------------------------------------------------------
img = torch.rand(1, 64, 64, 3)  # [B,H,W,C]
enc = PSN_Image_To_Latent()
dec = PSN_Latent_To_Image()

latent, = enc.run(img, None)  # None -> pseudo-VAE
assert isinstance(latent, dict), "latent output must be a dict"
assert "samples" in latent, "latent dict must have 'samples'"
assert latent["samples"].dim() == 4, "latent samples must be 4-D"

img2, = dec.run(latent, None)
assert img2.shape == img.shape, f"round-trip shape mismatch: {img2.shape} vs {img.shape}"
assert img2.min() >= 0.0 and img2.max() <= 1.0, "decoded image must be in 0..1"

# ---------------------------------------------------------------------------
# 2. Latent spatial shape is downsampled by the pseudo-VAE factor
# ---------------------------------------------------------------------------
f = _PseudoVAE().downscale
assert latent["samples"].shape[2] == 64 // f, "latent H should be H//f"
assert latent["samples"].shape[3] == 64 // f, "latent W should be W//f"

# ---------------------------------------------------------------------------
# 3. Mask -> Latent produces a valid latent dict
# ---------------------------------------------------------------------------
mask = torch.rand(1, 32, 32)  # [B,H,W]
m2l = PSN_Mask_To_Latent()
mlatent, = m2l.run(mask, None)
assert isinstance(mlatent, dict)
assert mlatent["samples"].dim() == 4
assert mlatent["samples"].shape[0] == 1

# ---------------------------------------------------------------------------
# 4. Latent -> Mask reduces channels to a single-channel mask
# ---------------------------------------------------------------------------
l2m = PSN_Latent_To_Mask()
m_out, = l2m.run(latent)
assert m_out.dim() == 3, "mask must be 3-D [B,H,W]"
assert m_out.shape[0] == 1
assert m_out.min() >= 0.0 and m_out.max() <= 1.0

# ---------------------------------------------------------------------------
# 5. Image -> Mask averages channels
# ---------------------------------------------------------------------------
i2m = PSN_Image_To_Mask()
m_img, = i2m.run(img)
assert m_img.shape == (1, 64, 64), f"image-to-mask shape: {m_img.shape}"
# verify it is the mean over channels
expected = img.mean(dim=-1)
assert torch.allclose(m_img, expected, atol=1e-6), "image-to-mask should be channel mean"

# ---------------------------------------------------------------------------
# 6. Mask -> Image adds a channel dimension
# ---------------------------------------------------------------------------
m2i = PSN_Mask_To_Image()
img_from_mask, = m2i.run(mask)
assert img_from_mask.shape == (1, 32, 32, 1), f"mask-to-image shape: {img_from_mask.shape}"

# ---------------------------------------------------------------------------
# 7. Bad input: non-tensor image raises TypeError
# ---------------------------------------------------------------------------
try:
    enc.run("not a tensor", None)
    assert False, "should have raised TypeError"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 8. Bad input: non-dict latent raises TypeError
# ---------------------------------------------------------------------------
try:
    dec.run(torch.rand(1, 4, 8, 8), None)
    assert False, "should have raised TypeError"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 9. Bad input: wrong-dim image raises ValueError
# ---------------------------------------------------------------------------
try:
    enc.run(torch.rand(5, 5), None)  # 2-D, not an image
    assert False, "should have raised ValueError"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 10. Inputs are not modified in place
# ---------------------------------------------------------------------------
img_orig = img.clone()
latent, = enc.run(img, None)
assert torch.equal(img, img_orig), "input image must not be modified in place"

# ---------------------------------------------------------------------------
# 11. NODE_CLASS_MAPPINGS and DISPLAY_NAME_MAPPINGS are consistent
# ---------------------------------------------------------------------------
assert len(NODE_CLASS_MAPPINGS) == 6
assert len(NODE_DISPLAY_NAME_MAPPINGS) == 6
for k in NODE_CLASS_MAPPINGS:
    assert k in NODE_DISPLAY_NAME_MAPPINGS, f"missing display name for {k}"
    assert hasattr(NODE_CLASS_MAPPINGS[k], "INPUT_TYPES")
    assert hasattr(NODE_CLASS_MAPPINGS[k], "RETURN_TYPES")
    assert NODE_CLASS_MAPPINGS[k].FUNCTION == "run"
    assert NODE_CLASS_MAPPINGS[k].CATEGORY.startswith("ParametricStudio/")

# ---------------------------------------------------------------------------
# 12. Batch > 1 works
# ---------------------------------------------------------------------------
img_batch = torch.rand(3, 16, 16, 3)
latent_b, = enc.run(img_batch, None)
assert latent_b["samples"].shape[0] == 3, "batch dim must be preserved"
img_b2, = dec.run(latent_b, None)
assert img_b2.shape == img_batch.shape

print("ok")
