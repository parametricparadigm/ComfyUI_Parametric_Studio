import torch

from n_3_automated_aspect_ratio_cropping_for_sd import (
    PSN_Auto_Aspect_Crop,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _target_wh,
    _crop_box,
)

node = PSN_Auto_Aspect_Crop()

# 1. Module-level mappings exist and are consistent.
assert "PSN_Auto_Aspect_Crop" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Auto_Aspect_Crop"] is PSN_Auto_Aspect_Crop
assert "PSN_Auto_Aspect_Crop" in NODE_DISPLAY_NAME_MAPPINGS

# 2. INPUT_TYPES / RETURN metadata.
it = PSN_Auto_Aspect_Crop.INPUT_TYPES()
assert "image" in it["required"]
assert "target_ratio" in it["required"]
assert "crop_mode" in it["required"]
assert "custom_w" in it["optional"]
assert PSN_Auto_Aspect_Crop.RETURN_TYPES == ("IMAGE", "INT", "INT")
assert PSN_Auto_Aspect_Crop.FUNCTION == "run"
assert PSN_Auto_Aspect_Crop.CATEGORY.startswith("ParametricStudio/")

# 3. 1000x1000 -> 1:1 center crop gives 1000x1000 (already square, rounded to 8).
img = torch.rand(1, 1000, 1000, 3)
out, ow, oh = node.run(img, "1:1", "center")
assert ow == 1000 and oh == 1000
assert out.shape == (1, 1000, 1000, 3)

# 4. 1024x512 -> 16:9 center crop: keep width 1024, height = 1024*9/16 = 576,
# but source is only 512 tall so it shrinks to 904x512 (rounded to 8).
img = torch.rand(2, 512, 1024, 3)
out, ow, oh = node.run(img, "16:9", "center")
assert ow == 1024 and oh == 512
assert out.shape[1] == 512 and out.shape[2] == 904 and out.shape[0] == 2 and out.shape[3] == 3

# 5. 512x1024 -> 9:16 center crop: keep height 1024, width = 1024*9/16 = 576,
# but source is only 512 wide so it shrinks to 904x512 (rounded to 8).
img = torch.rand(1, 1024, 512, 3)
out, ow, oh = node.run(img, "9:16", "center")
assert out.shape[1] == 904 and out.shape[2] == 512 and out.shape[0] == 1 and out.shape[3] == 3

# 6. Custom ratio 4:3 on a 600x800 image: keep height 800, width = 800*4/3 = 1066 -> but limited by source width 600.
img = torch.rand(1, 800, 600, 3)
out, ow, oh = node.run(img, "4:3", "center")
# target would be 1066x800 but source is only 600 wide, so it shrinks to fit.
assert out.shape[2] <= 600 and out.shape[1] <= 800
assert out.shape[2] % 8 == 0 and out.shape[1] % 8 == 0

# 7. Custom W/H: 1000x1000 -> custom 512x256.
img = torch.rand(1, 1000, 1000, 3)
out, ow, oh = node.run(img, "custom", "center", custom_w=512, custom_h=256)
assert out.shape == (1, 256, 512, 3)

# 8. Face mode on a synthetic image with a skin-tone blob in the upper half.
img = torch.full((1, 200, 200, 3), 0.1)
img[0, 40:80, 80:120, 0] = 0.8  # red
img[0, 40:80, 80:120, 1] = 0.6  # green
img[0, 40:80, 80:120, 2] = 0.4  # blue
out, ow, oh = node.run(img, "1:1", "face")
assert out.shape == (1, 200, 200, 3)

# 9. Smart mode runs and returns correct shape (300x400 -> 1:1 = 296x296).
img = torch.rand(1, 300, 400, 3)
out, ow, oh = node.run(img, "1:1", "smart")
assert out.shape[1] == 296 and out.shape[2] == 296 and out.shape[0] == 1 and out.shape[3] == 3

# 10. Bad input: wrong number of dims raises ValueError.
try:
    node.run(torch.rand(100, 100, 3), "1:1", "center")
    raise AssertionError("expected ValueError for 3D tensor")
except ValueError:
    pass

# 11. Bad input: unknown ratio raises ValueError.
try:
    node.run(torch.rand(1, 100, 100, 3), "7:5", "center")
    raise AssertionError("expected ValueError for bad ratio")
except ValueError:
    pass

# 12. Bad input: unknown crop mode raises ValueError.
try:
    node.run(torch.rand(1, 100, 100, 3), "1:1", "diagonal")
    raise AssertionError("expected ValueError for bad crop_mode")
except ValueError:
    pass

# 13. Input is not modified in place.
img = torch.rand(1, 128, 128, 3)
snapshot = img.clone()
out, _, _ = node.run(img, "16:9", "center")
assert torch.equal(img, snapshot)

# 14. _target_wh helper sanity.
assert _target_wh(1000, 1000, "1:1", 0, 0) == (1000, 1000)
assert _target_wh(512, 1024, "16:9", 0, 0) == (1024, 576)
assert _target_wh(1024, 512, "9:16", 0, 0) == (576, 1024)

# 15. _crop_box clamps inside the image.
x0, y0, x1, y1 = _crop_box(100, 100, 50, 50, 10, 10)
assert x0 == 0 and y0 == 0 and x1 == 50 and y1 == 50
x0, y0, x1, y1 = _crop_box(100, 100, 50, 50, 95, 95)
assert x1 == 100 and y1 == 100

print("ok")
