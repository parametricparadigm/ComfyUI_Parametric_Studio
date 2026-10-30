import torch

from n_8_anime_specific_pose_segmentation import (
    PSN_Anime_Pose_Estimator,
    PSN_Anime_Segmentor,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _make_image(b=1, h=64, w=64, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(b, h, w, c, generator=g)


# 1. module-level mappings exist and are consistent
assert "PSN_Anime_Pose_Estimator" in NODE_CLASS_MAPPINGS
assert "PSN_Anime_Segmentor" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Anime_Pose_Estimator"] is PSN_Anime_Pose_Estimator
assert NODE_CLASS_MAPPINGS["PSN_Anime_Segmentor"] is PSN_Anime_Segmentor
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)

# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
it = PSN_Anime_Pose_Estimator.INPUT_TYPES()
assert "image" in it["required"]
assert "resolution" in it["required"]
assert PSN_Anime_Pose_Estimator.RETURN_TYPES == ("IMAGE", "POSE_KEYPOINT")
assert PSN_Anime_Pose_Estimator.FUNCTION == "run"
assert PSN_Anime_Pose_Estimator.CATEGORY.startswith("ParametricStudio/")

it2 = PSN_Anime_Segmentor.INPUT_TYPES()
assert "image" in it2["required"]
assert "classes" in it2["required"]
assert PSN_Anime_Segmentor.RETURN_TYPES == ("MASK",)
assert PSN_Anime_Segmentor.FUNCTION == "run"

# 3. pose estimator returns correct shapes and keypoint format
node = PSN_Anime_Pose_Estimator()
img = _make_image(2, 48, 32, 3, seed=1)
pose_map, keypoints = node.run(img, resolution=64)
assert isinstance(pose_map, torch.Tensor)
assert pose_map.shape[0] == 2 and pose_map.shape[-1] == 3
assert pose_map.min() >= 0.0 and pose_map.max() <= 1.0
assert isinstance(keypoints, dict)
assert "names" in keypoints and "keypoints" in keypoints
assert len(keypoints["names"]) == 17
assert keypoints["keypoints"].shape == (2, 17, 3)
# scores in [0,1]
assert keypoints["keypoints"][..., 2].min() >= 0.0
assert keypoints["keypoints"][..., 2].max() <= 1.0

# 4. segmentor returns a MASK [B,H,W] in 0..1
seg = PSN_Anime_Segmentor()
img2 = _make_image(1, 32, 32, 3, seed=2)
(mask_hair,) = seg.run(img2, "hair")
assert mask_hair.shape == (1, 32, 32)
assert mask_hair.min() >= 0.0 and mask_hair.max() <= 1.0

# 5. all four classes produce valid masks
for cls in ["hair", "eyes", "mouth", "body"]:
    (m,) = seg.run(img2, cls)
    assert m.shape == (1, 32, 32)
    assert m.min() >= 0.0 and m.max() <= 1.0

# 6. bad input: wrong type raises TypeError
try:
    node.run("not a tensor", 64)
    assert False, "expected TypeError"
except TypeError:
    pass

# 7. bad input: wrong shape raises ValueError
try:
    node.run(torch.rand(4, 4, 3), 64)  # 3D, not 4D
    assert False, "expected ValueError"
except ValueError:
    pass

# 8. bad input: unknown segment class raises ValueError
try:
    seg.run(img2, "fingers")
    assert False, "expected ValueError"
except ValueError:
    pass

# 9. input is not modified in place
img3 = _make_image(1, 16, 16, 3, seed=3)
before = img3.clone()
node.run(img3, 64)
seg.run(img3, "hair")
assert torch.equal(img3, before)

# 10. edge case: single-pixel image does not crash
img_tiny = torch.rand(1, 1, 1, 3)
pm, kp = node.run(img_tiny, 64)
assert pm.shape[0] == 1 and pm.shape[-1] == 3
assert kp["keypoints"].shape == (1, 17, 3)

print("ok")
