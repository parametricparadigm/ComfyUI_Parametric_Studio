import torch

from n_2_hdr_grading_for_image_outputs import (
    PSN_HDR_Tone_Map,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _srgb_to_linear,
    _linear_to_srgb,
    _reinhard,
    _aces_approx,
    _filmic,
    _apply_tone_map,
    _apply_saturation,
    _as_tensor,
)


def make_hdr_image(b=1, h=4, w=4, c=3, lo=0.0, hi=2.0):
    """Create a synthetic HDR image tensor in [lo, hi]."""
    t = torch.linspace(lo, hi, b * h * w * c).reshape(b, h, w, c)
    return t


def test_module_mappings():
    assert "PSN_HDR_Tone_Map" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_HDR_Tone_Map"] is PSN_HDR_Tone_Map
    assert "PSN_HDR_Tone_Map" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types():
    it = PSN_HDR_Tone_Map.INPUT_TYPES()
    assert "image" in it["required"]
    assert "tone_map_mode" in it["required"]
    assert "exposure" in it["required"]
    assert "saturation" in it["required"]
    assert PSN_HDR_Tone_Map.RETURN_TYPES == ("IMAGE",)
    assert PSN_HDR_Tone_Map.RETURN_NAMES == ("graded_image",)
    assert PSN_HDR_Tone_Map.FUNCTION == "run"
    assert PSN_HDR_Tone_Map.CATEGORY.startswith("ParametricStudio/")


def test_output_range_reinhard():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(hi=3.0)
    out = node.run(img, "Reinhard", 1.0, 1.0)[0]
    assert out.shape == img.shape
    assert out.dtype == torch.float32
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_output_range_aces():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(hi=5.0)
    out = node.run(img, "ACES", 1.0, 1.0)[0]
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_output_range_filmic():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(hi=4.0)
    out = node.run(img, "Filmic", 1.0, 1.0)[0]
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_exposure_brightens():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(hi=1.5)
    out_low = node.run(img, "Reinhard", 0.5, 1.0)[0]
    out_high = node.run(img, "Reinhard", 2.0, 1.0)[0]
    # Higher exposure should produce a brighter (higher mean) image.
    assert out_high.mean() > out_low.mean()


def test_saturation_zero_gives_grayscale():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(hi=1.0)
    out = node.run(img, "Reinhard", 1.0, 0.0)[0]
    # With saturation 0, all channels should be equal (luma).
    assert torch.allclose(out[..., 0], out[..., 1], atol=1e-5)
    assert torch.allclose(out[..., 1], out[..., 2], atol=1e-5)


def test_no_inplace_modification():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(hi=2.0)
    img_copy = img.clone()
    node.run(img, "ACES", 1.0, 1.0)
    assert torch.equal(img, img_copy), "input was modified in place"


def test_bad_input_not_tensor():
    node = PSN_HDR_Tone_Map()
    try:
        node.run("not a tensor", "Reinhard", 1.0, 1.0)
        assert False, "expected TypeError"
    except TypeError:
        pass


def test_bad_input_wrong_dims():
    node = PSN_HDR_Tone_Map()
    bad = torch.randn(4, 4, 3)  # missing batch dim
    try:
        node.run(bad, "Reinhard", 1.0, 1.0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bad_tone_map_mode():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(hi=1.0)
    try:
        node.run(img, "Bogus", 1.0, 1.0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_srgb_linear_roundtrip():
    x = torch.rand(1, 2, 2, 3) * 0.99
    lin = _srgb_to_linear(x)
    back = _linear_to_srgb(lin)
    assert torch.allclose(x, back, atol=1e-4)


def test_reinhard_known_value():
    x = torch.tensor([[[[1.0]]]])
    out = _reinhard(x)
    assert torch.allclose(out, torch.tensor([[[[0.5]]]]), atol=1e-6)


def test_aces_monotonic():
    x = torch.linspace(0.0, 2.0, 100).reshape(1, 1, 100, 1)
    out = _aces_approx(x)
    diffs = out[:, :, 1:, :] - out[:, :, :-1, :]
    assert (diffs >= -1e-7).all(), "ACES approx not monotonic"


def test_filmic_monotonic():
    x = torch.linspace(0.0, 2.0, 100).reshape(1, 1, 100, 1)
    out = _filmic(x)
    diffs = out[:, :, 1:, :] - out[:, :, :-1, :]
    assert (diffs >= -1e-7).all(), "Filmic not monotonic"


def test_grayscale_input():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(c=1, hi=2.0)
    out = node.run(img, "Reinhard", 1.0, 1.0)[0]
    assert out.shape == img.shape
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_rgba_input():
    node = PSN_HDR_Tone_Map()
    img = make_hdr_image(c=4, hi=1.5)
    out = node.run(img, "ACES", 1.0, 1.0)[0]
    assert out.shape == img.shape
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def main():
    test_module_mappings()
    test_input_types()
    test_output_range_reinhard()
    test_output_range_aces()
    test_output_range_filmic()
    test_exposure_brightens()
    test_saturation_zero_gives_grayscale()
    test_no_inplace_modification()
    test_bad_input_not_tensor()
    test_bad_input_wrong_dims()
    test_bad_tone_map_mode()
    test_srgb_linear_roundtrip()
    test_reinhard_known_value()
    test_aces_monotonic()
    test_filmic_monotonic()
    test_grayscale_input()
    test_rgba_input()
    print("ok")


if __name__ == "__main__":
    main()
