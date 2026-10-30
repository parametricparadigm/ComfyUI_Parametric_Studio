import torch
from n_9_lab_space_product_recoloring import (
    PSN_LAB_Recolor,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _rgb_to_lab,
    _lab_to_rgb,
)

node = PSN_LAB_Recolor()

# 1. Module-level mappings exist and are consistent
assert "PSN_LAB_Recolor" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_LAB_Recolor"] is PSN_LAB_Recolor
assert "PSN_LAB_Recolor" in NODE_DISPLAY_NAME_MAPPINGS

# 2. INPUT_TYPES has required and optional keys
it = PSN_LAB_Recolor.INPUT_TYPES()
assert "required" in it and "optional" in it
assert "image" in it["required"]
assert "mask" in it["optional"]

# 3. RETURN_TYPES / FUNCTION / CATEGORY
assert PSN_LAB_Recolor.RETURN_TYPES == ("IMAGE",)
assert PSN_LAB_Recolor.FUNCTION == "run"
assert PSN_LAB_Recolor.CATEGORY.startswith("ParametricStudio/")

# 4. Red image recolored toward blue: dominant channel shifts to blue
red = torch.full((1, 4, 4, 3), 0.0, dtype=torch.float32)
red[..., 0] = 1.0  # pure red
out, = node.run(red, target_L=50.0, target_A=0.0, target_B=-100.0, strength=1.0)
assert out.shape == (1, 4, 4, 3)
assert out.min() >= 0.0 and out.max() <= 1.0
# After shifting B* to -100 (blue), the blue channel should dominate
assert out[0, 0, 0, 2] > out[0, 0, 0, 0], f"blue {out[0,0,0,2]} should exceed red {out[0,0,0,0]}"

# 5. strength=0 leaves image unchanged
out0, = node.run(red, target_L=50.0, target_A=0.0, target_B=-100.0, strength=0.0)
assert torch.allclose(out0, red, atol=1e-5), "strength=0 should not change the image"

# 6. Mask: masked-out pixels stay original, masked-in pixels change
img = torch.full((1, 2, 2, 3), 0.5, dtype=torch.float32)
mask = torch.tensor([[[1.0, 0.0], [0.0, 1.0]]], dtype=torch.float32)
out_m, = node.run(img, target_L=10.0, target_A=0.0, target_B=0.0, strength=1.0, mask=mask)
# pixel (0,0) is masked in -> should be darker (L=10)
assert out_m[0, 0, 0, 0] < img[0, 0, 0, 0], "masked-in pixel should be darker"
# pixel (0,1) is masked out -> unchanged
assert torch.allclose(out_m[0, 0, 1], img[0, 0, 1], atol=1e-5), "masked-out pixel should be unchanged"

# 7. Bad input: wrong shape raises ValueError
try:
    node.run(torch.zeros(1, 4, 4, 4), target_L=50.0, target_A=0.0, target_B=0.0, strength=1.0)
    raise AssertionError("expected ValueError for wrong channel count")
except ValueError:
    pass

# 8. Bad input: non-tensor raises TypeError
try:
    node.run("not a tensor", target_L=50.0, target_A=0.0, target_B=0.0, strength=1.0)
    raise AssertionError("expected TypeError for non-tensor image")
except TypeError:
    pass

# 9. LAB round-trip: rgb -> lab -> rgb should be close to original
rgb = torch.rand(1, 3, 3, 3, dtype=torch.float32)
lab = _rgb_to_lab(rgb)
back = _lab_to_rgb(lab)
assert torch.allclose(rgb, back, atol=1e-3), f"round-trip error too large: {(rgb - back).abs().max()}"

# 10. Input is not modified in place
orig = torch.full((1, 2, 2, 3), 0.8, dtype=torch.float32)
orig_copy = orig.clone()
node.run(orig, target_L=10.0, target_A=0.0, target_B=0.0, strength=1.0)
assert torch.equal(orig, orig_copy), "input tensor must not be modified in place"

print("ok")
