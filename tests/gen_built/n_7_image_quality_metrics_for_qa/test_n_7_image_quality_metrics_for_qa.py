import math
import torch

from n_7_image_quality_metrics_for_qa import (
    PSN_Quality_Metrics,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

node = PSN_Quality_Metrics()

# --- 1. module-level mappings exist and are consistent ---
assert "PSN_Quality_Metrics" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Quality_Metrics"] is PSN_Quality_Metrics
assert "PSN_Quality_Metrics" in NODE_DISPLAY_NAME_MAPPINGS

# --- 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY ---
it = PSN_Quality_Metrics.INPUT_TYPES()
assert "image" in it["required"]
assert "reference" in it["required"]
assert "metrics" in it["required"]
assert PSN_Quality_Metrics.RETURN_TYPES == ("FLOAT", "IMAGE")
assert PSN_Quality_Metrics.RETURN_NAMES == ("score", "map")
assert PSN_Quality_Metrics.FUNCTION == "run"
assert PSN_Quality_Metrics.CATEGORY.startswith("ParametricStudio/")

# --- 3. SSIM of an image with itself is ~1.0 ---
torch.manual_seed(0)
img = torch.rand(1, 16, 16, 3)
score, emap = node.run(img, img.clone(), "SSIM", return_map=True)
assert isinstance(score, float)
assert abs(score - 1.0) < 1e-4, f"SSIM self should be ~1.0, got {score}"
assert emap.shape == (1, 16, 16, 3)
assert emap.max().item() < 1e-6  # identical -> zero error map

# --- 4. PSNR of an image with itself is infinity ---
score_p, _ = node.run(img, img.clone(), "PSNR", return_map=False)
assert math.isinf(score_p), f"PSNR self should be inf, got {score_p}"

# --- 5. Noisy version lowers SSIM and PSNR ---
noisy = img + 0.3 * torch.randn_like(img)
noisy = noisy.clamp(0, 1)
score_n, _ = node.run(img, noisy, "SSIM", return_map=False)
assert score_n < 1.0, f"noisy SSIM should be < 1, got {score_n}"
score_pn, _ = node.run(img, noisy, "PSNR", return_map=False)
assert not math.isinf(score_pn)
assert score_pn < 100.0, f"noisy PSNR should be finite and < 100, got {score_pn}"

# --- 6. DISTS proxy: 0 for identical, > 0 for different ---
score_d0, _ = node.run(img, img.clone(), "DISTS", return_map=False)
assert score_d0 == 0.0, f"DISTS self should be 0, got {score_d0}"
score_dn, _ = node.run(img, noisy, "DISTS", return_map=False)
assert score_dn > 0.0, f"DISTS noisy should be > 0, got {score_dn}"

# --- 7. Mismatched spatial sizes are handled (resize) ---
ref_small = torch.rand(1, 8, 8, 3)
score_m, emap_m = node.run(img, ref_small, "SSIM", return_map=True)
assert isinstance(score_m, float)
assert emap_m.shape == (1, 16, 16, 3)

# --- 8. Bad input: wrong number of dims raises ValueError ---
try:
    node.run(torch.rand(16, 16, 3), img, "SSIM")
    raise AssertionError("expected ValueError for 3-dim input")
except ValueError:
    pass

# --- 9. Bad input: non-tensor raises ValueError ---
try:
    node.run("not a tensor", img, "SSIM")
    raise AssertionError("expected ValueError for non-tensor input")
except ValueError:
    pass

# --- 10. Bad metric name raises ValueError ---
try:
    node.run(img, img, "NOT_A_METRIC")
    raise AssertionError("expected ValueError for unknown metric")
except ValueError:
    pass

# --- 11. Inputs are not modified in place ---
img_orig = img.clone()
ref_in = img.clone()
node.run(img, ref_in, "SSIM", return_map=True)
assert torch.equal(img, img_orig), "image was modified in place"
assert torch.equal(ref_in, img_orig), "reference was modified in place"

# --- 12. Batch > 1 works ---
img_b = torch.rand(2, 12, 12, 3)
score_b, emap_b = node.run(img_b, img_b.clone(), "SSIM", return_map=True)
assert abs(score_b - 1.0) < 1e-4
assert emap_b.shape == (2, 12, 12, 3)

print("ok")
