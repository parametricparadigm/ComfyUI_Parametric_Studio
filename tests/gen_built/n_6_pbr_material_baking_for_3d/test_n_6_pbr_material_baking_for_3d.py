import torch

from n_6_pbr_material_baking_for_3d import (
    PSN_PBR_Bake_Albedo,
    PSN_PBR_Bake_Normal,
    PSN_PBR_Bake_Roughness,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# ---------------------------------------------------------------------------
# 1. Module-level mappings exist and are consistent
# ---------------------------------------------------------------------------
assert set(NODE_CLASS_MAPPINGS) == {
    "PSN_PBR_Bake_Albedo",
    "PSN_PBR_Bake_Normal",
    "PSN_PBR_Bake_Roughness",
}
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)
for name, cls in NODE_CLASS_MAPPINGS.items():
    assert hasattr(cls, "INPUT_TYPES")
    assert hasattr(cls, "RETURN_TYPES")
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")

# ---------------------------------------------------------------------------
# 2. Albedo: sRGB -> linear conversion is correct
# ---------------------------------------------------------------------------
# A mid-gray sRGB value of 0.5 should map to ~0.214 in linear.
img = torch.full((1, 4, 4, 3), 0.5)
albedo = PSN_PBR_Bake_Albedo().run(img, "sRGB")[0]
assert albedo.shape == (1, 4, 4, 3)
assert albedo.min() >= 0.0 and albedo.max() <= 1.0
# After the small box blur the value stays close to the linear midpoint.
expected_linear = ((0.5 + 0.055) / 1.055) ** 2.4  # ~0.214
assert abs(albedo[0, 2, 2, 0].item() - expected_linear) < 0.05, (
    f"albedo {albedo[0,2,2,0].item()} vs expected {expected_linear}"
)

# ---------------------------------------------------------------------------
# 3. Albedo: Linear input passes through (with slight blur)
# ---------------------------------------------------------------------------
img_lin = torch.full((1, 4, 4, 3), 0.5)
albedo_lin = PSN_PBR_Bake_Albedo().run(img_lin, "Linear")[0]
assert abs(albedo_lin[0, 2, 2, 0].item() - 0.5) < 0.05

# ---------------------------------------------------------------------------
# 4. Normal: flat image -> neutral normal (0.5, 0.5, 1.0)
# ---------------------------------------------------------------------------
flat = torch.full((1, 8, 8, 3), 0.5)
normal = PSN_PBR_Bake_Normal().run(flat, strength=1.0, smoothness=1.0)[0]
assert normal.shape == (1, 8, 8, 3)
# Interior pixels should be neutral: R≈0.5, G≈0.5, B≈1.0
assert abs(normal[0, 4, 4, 0].item() - 0.5) < 0.01
assert abs(normal[0, 4, 4, 1].item() - 0.5) < 0.01
assert abs(normal[0, 4, 4, 2].item() - 1.0) < 0.01

# ---------------------------------------------------------------------------
# 5. Normal: gradient image produces non-neutral normals
# ---------------------------------------------------------------------------
g = torch.linspace(0.0, 1.0, 8).view(1, 1, 8, 1).expand(1, 8, 8, 3).contiguous()
normal_g = PSN_PBR_Bake_Normal().run(g, strength=2.0, smoothness=0.0)[0]
# At least one interior pixel should deviate from neutral
interior = normal_g[0, 2:6, 2:6, :]
dev = (interior - torch.tensor([0.5, 0.5, 1.0])).abs().max().item()
assert dev > 0.01, f"expected non-neutral normal, max dev {dev}"

# ---------------------------------------------------------------------------
# 6. Roughness: flat image -> min_roughness everywhere
# ---------------------------------------------------------------------------
flat_r = torch.full((1, 8, 8, 3), 0.5)
rough = PSN_PBR_Bake_Roughness().run(flat_r, min_roughness=0.2, max_roughness=0.8)[0]
assert rough.shape == (1, 8, 8, 3)
# All channels equal and close to min_roughness
assert abs(rough[0, 4, 4, 0].item() - 0.2) < 0.05
assert abs(rough[0, 4, 4, 1].item() - 0.2) < 0.05
assert abs(rough[0, 4, 4, 2].item() - 0.2) < 0.05

# ---------------------------------------------------------------------------
# 7. Roughness: noisy image -> higher roughness than flat
# ---------------------------------------------------------------------------
torch.manual_seed(42)
noisy = torch.rand(1, 8, 8, 3)
rough_n = PSN_PBR_Bake_Roughness().run(noisy, min_roughness=0.1, max_roughness=0.9)[0]
# Some pixel should be noticeably above min_roughness
assert rough_n.max().item() > 0.3, f"max roughness {rough_n.max().item()}"

# ---------------------------------------------------------------------------
# 8. Bad input: non-tensor raises TypeError
# ---------------------------------------------------------------------------
try:
    PSN_PBR_Bake_Albedo().run("not a tensor", "sRGB")
    raise AssertionError("expected TypeError")
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 9. Bad input: wrong shape raises ValueError
# ---------------------------------------------------------------------------
try:
    PSN_PBR_Bake_Albedo().run(torch.rand(4, 4, 3), "sRGB")  # missing batch dim
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 10. Bad input: NaN in image raises ValueError
# ---------------------------------------------------------------------------
bad = torch.full((1, 4, 4, 3), 0.5)
bad[0, 0, 0, 0] = float("nan")
try:
    PSN_PBR_Bake_Albedo().run(bad, "sRGB")
    raise AssertionError("expected ValueError for NaN")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 11. Roughness: min > max raises ValueError
# ---------------------------------------------------------------------------
try:
    PSN_PBR_Bake_Roughness().run(torch.rand(1, 4, 4, 3), min_roughness=0.9, max_roughness=0.1)
    raise AssertionError("expected ValueError for min>max")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 12. No in-place modification of input
# ---------------------------------------------------------------------------
orig = torch.full((1, 4, 4, 3), 0.5)
orig_clone = orig.clone()
PSN_PBR_Bake_Albedo().run(orig, "sRGB")
PSN_PBR_Bake_Normal().run(orig, 1.0, 1.0)
PSN_PBR_Bake_Roughness().run(orig, 0.1, 0.9)
assert torch.equal(orig, orig_clone), "input was modified in place"

print("ok")
