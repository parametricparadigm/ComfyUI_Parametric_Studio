import torch

from n_6_pbr_texture_generation_from_images import (
    PSN_PBR_Delight,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_image(b=1, h=32, w=32, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(b, h, w, c, generator=g)


def test_module_mappings():
    assert "PSN_PBR_Delight" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_PBR_Delight"] is PSN_PBR_Delight
    assert "PSN_PBR_Delight" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_PBR_Delight"], str)


def test_input_types_schema():
    spec = PSN_PBR_Delight.INPUT_TYPES()
    assert "required" in spec
    req = spec["required"]
    assert req["albedo_image"] == ("IMAGE",)
    assert req["model_path"][0] == "STRING"
    assert req["tiled"][0] == "BOOLEAN"
    assert PSN_PBR_Delight.RETURN_TYPES == ("IMAGE", "IMAGE", "IMAGE")
    assert PSN_PBR_Delight.RETURN_NAMES == ("albedo", "roughness", "normal")
    assert PSN_PBR_Delight.FUNCTION == "run"
    assert PSN_PBR_Delight.CATEGORY.startswith("ParametricStudio/")


def test_basic_run_shapes_and_range():
    node = PSN_PBR_Delight()
    img = make_image(2, 32, 32, 3, seed=1)
    albedo, rough, normal = node.run(img, model_path="", tiled=False)
    assert albedo.shape == (2, 32, 32, 3)
    assert rough.shape == (2, 32, 32, 3)
    assert normal.shape == (2, 32, 32, 3)
    for t in (albedo, rough, normal):
        assert t.dtype == torch.float32
        assert t.min() >= 0.0 and t.max() <= 1.0


def test_input_not_modified():
    node = PSN_PBR_Delight()
    img = make_image(1, 16, 16, 3, seed=2)
    snapshot = img.clone()
    node.run(img, model_path="", tiled=True)
    assert torch.equal(img, snapshot), "input must not be modified in place"


def test_roughness_correlates_with_local_contrast():
    """A flat region should give low roughness, a noisy region high."""
    node = PSN_PBR_Delight()
    b, h, w = 1, 64, 64
    flat = torch.full((b, h, w, 3), 0.5)
    noisy = torch.rand(b, h, w, 3, generator=torch.Generator().manual_seed(3))
    img = torch.cat([flat, noisy], dim=1)  # [1, 128, 64, 3]
    _, rough, _ = node.run(img, model_path="", tiled=False)
    flat_rough = rough[:, :h, :, 0].mean()
    noisy_rough = rough[:, h:, :, 0].mean()
    assert noisy_rough > flat_rough, (
        f"noisy roughness {noisy_rough.item():.3f} should exceed flat {flat_rough.item():.3f}"
    )


def test_normal_flat_is_neutral():
    """A perfectly flat image should give a neutral normal (0.5,0.5,1)."""
    node = PSN_PBR_Delight()
    flat = torch.full((1, 32, 32, 3), 0.4)
    _, _, normal = node.run(flat, model_path="", tiled=False)
    # neutral tangent-space normal: R=0.5, G=0.5, B=1.0
    assert abs(normal[0, 16, 16, 0].item() - 0.5) < 1e-4
    assert abs(normal[0, 16, 16, 1].item() - 0.5) < 1e-4
    assert abs(normal[0, 16, 16, 2].item() - 1.0) < 1e-4


def test_tiled_changes_edges():
    node = PSN_PBR_Delight()
    img = make_image(1, 64, 64, 3, seed=4)
    a0, r0, n0 = node.run(img, model_path="", tiled=False)
    a1, r1, n1 = node.run(img, model_path="", tiled=True)
    # interior should be identical
    assert torch.allclose(a0[:, 16:-16, 16:-16, :], a1[:, 16:-16, 16:-16, :])
    # edges should differ
    assert not torch.allclose(a0[:, :8, :, :], a1[:, :8, :, :])


def test_bad_input_type_raises():
    node = PSN_PBR_Delight()
    try:
        node.run("not a tensor", model_path="", tiled=False)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-tensor input")


def test_bad_input_dim_raises():
    node = PSN_PBR_Delight()
    bad = torch.rand(32, 32, 3)  # 3D, missing batch
    try:
        node.run(bad, model_path="", tiled=False)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for 3D input")


def test_single_channel_input():
    node = PSN_PBR_Delight()
    img = make_image(1, 16, 16, 1, seed=5)
    albedo, rough, normal = node.run(img, model_path="", tiled=False)
    assert albedo.shape == (1, 16, 16, 3)
    assert rough.shape == (1, 16, 16, 3)
    assert normal.shape == (1, 16, 16, 3)


def test_small_image_edge():
    node = PSN_PBR_Delight()
    img = make_image(1, 4, 4, 3, seed=6)
    albedo, rough, normal = node.run(img, model_path="", tiled=True)
    assert albedo.shape == (1, 4, 4, 3)
    assert rough.shape == (1, 4, 4, 3)
    assert normal.shape == (1, 4, 4, 3)


def main():
    test_module_mappings()
    test_input_types_schema()
    test_basic_run_shapes_and_range()
    test_input_not_modified()
    test_roughness_correlates_with_local_contrast()
    test_normal_flat_is_neutral()
    test_tiled_changes_edges()
    test_bad_input_type_raises()
    test_bad_input_dim_raises()
    test_single_channel_input()
    test_small_image_edge()
    print("ok")


if __name__ == "__main__":
    main()
