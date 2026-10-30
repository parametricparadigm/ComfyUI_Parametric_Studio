import torch

from n_8_batch_color_correction_and_masking import (
    PSN_BatchColorMod,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_image(batch=2, h=4, w=4, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(batch, h, w, c, generator=g)


def test_module_mappings():
    assert "PSN_BatchColorMod" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_BatchColorMod"] is PSN_BatchColorMod
    assert "PSN_BatchColorMod" in NODE_DISPLAY_NAME_MAPPINGS
    it = PSN_BatchColorMod.INPUT_TYPES()
    assert "images" in it["required"]
    assert PSN_BatchColorMod.FUNCTION == "run"
    assert PSN_BatchColorMod.RETURN_TYPES == ("IMAGE",)


def test_white_balance_shifts_towards_neutral():
    # Warm image: red channel much brighter than blue.
    img = torch.zeros(1, 4, 4, 3)
    img[..., 0] = 0.8
    img[..., 1] = 0.5
    img[..., 2] = 0.2
    node = PSN_BatchColorMod()
    out = node.run(img, "Auto_White_Balance", "{}", None)[0]
    before = img[0, :, :, :3].mean(dim=(0, 1))
    after = out[0, :, :, :3].mean(dim=(0, 1))
    # Blue should increase, red should decrease.
    assert after[2] > before[2]
    assert after[0] < before[0]
    # Channel means should be closer to the overall mean after correction.
    spread_before = before.max() - before.min()
    spread_after = after.max() - after.min()
    assert spread_after < spread_before


def test_mask_zero_keeps_original():
    img = make_image(2, 4, 4, 3, seed=1)
    mask = torch.zeros(2, 4, 4)
    node = PSN_BatchColorMod()
    out = node.run(img, "Auto_Contrast", "{}", mask)[0]
    assert torch.allclose(out, img, atol=1e-6)


def test_mask_full_applies_correction():
    img = make_image(2, 4, 4, 3, seed=2)
    mask = torch.ones(2, 4, 4)
    node = PSN_BatchColorMod()
    out = node.run(img, "Auto_Contrast", "{}", mask)[0]
    assert not torch.allclose(out, img, atol=1e-6)
    assert out.shape == img.shape
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_custom_multipliers_and_offsets():
    img = torch.full((1, 2, 2, 3), 0.5)
    node = PSN_BatchColorMod()
    out = node.run(img, "Custom", '{"multipliers": [2.0, 1.0, 1.0], "offsets": [0.1, 0.0, 0.0]}', None)[0]
    assert abs(out[0, 0, 0, 0].item() - 1.1) < 1e-5
    assert abs(out[0, 0, 0, 1].item() - 0.5) < 1e-5


def test_bad_inputs_raise():
    node = PSN_BatchColorMod()
    # Non-tensor images.
    try:
        node.run("not a tensor", "Auto_Contrast", "{}", None)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    # Wrong rank.
    try:
        node.run(torch.rand(4, 4, 3), "Auto_Contrast", "{}", None)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Mask batch mismatch.
    img = make_image(2, 4, 4, 3, seed=3)
    try:
        node.run(img, "Auto_Contrast", "{}", torch.ones(3, 4, 4))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Unknown correction type.
    try:
        node.run(img, "Bogus", "{}", None)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_no_in_place_mutation_and_bad_json():
    img = make_image(2, 4, 4, 3, seed=4)
    snapshot = img.clone()
    node = PSN_BatchColorMod()
    # Bad JSON should be treated as empty params, not crash.
    out = node.run(img, "Custom", "not json at all", None)[0]
    assert torch.allclose(img, snapshot)
    assert out.shape == img.shape
    # 4-channel image should pass through untouched by white balance.
    img4 = make_image(1, 3, 3, 4, seed=5)
    snap4 = img4.clone()
    out4 = node.run(img4, "Auto_White_Balance", "{}", None)[0]
    assert torch.allclose(img4, snap4)
    assert out4.shape == img4.shape


def test_mask_4d_single_channel():
    img = make_image(2, 4, 4, 3, seed=6)
    mask = torch.ones(2, 4, 4, 1)
    node = PSN_BatchColorMod()
    out = node.run(img, "Auto_Contrast", "{}", mask)[0]
    assert out.shape == img.shape


if __name__ == "__main__":
    test_module_mappings()
    test_white_balance_shifts_towards_neutral()
    test_mask_zero_keeps_original()
    test_mask_full_applies_correction()
    test_custom_multipliers_and_offsets()
    test_bad_inputs_raise()
    test_no_in_place_mutation_and_bad_json()
    test_mask_4d_single_channel()
    print("ok")
