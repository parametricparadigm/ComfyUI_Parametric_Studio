import torch

from n_4_realistic_camera_simulation import (
    PSN_Camera_Degradation,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _as_image,
    _gaussian_blur,
    _chromatic_aberration,
    _vignette,
    _poisson_noise,
    _gaussian_sensor_noise,
)


def make_image(b=1, h=16, w=16, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(b, h, w, c, generator=g)


def test_module_mappings():
    assert "PSN_Camera_Degradation" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Camera_Degradation"] is PSN_Camera_Degradation
    assert "PSN_Camera_Degradation" in NODE_DISPLAY_NAME_MAPPINGS
    cls = PSN_Camera_Degradation
    assert cls.FUNCTION == "run"
    assert cls.RETURN_TYPES == ("IMAGE",)
    assert cls.RETURN_NAMES == ("simulated_image",)
    assert cls.CATEGORY.startswith("ParametricStudio/")
    it = cls.INPUT_TYPES()
    assert "image" in it["required"]
    assert "lens_type" in it["required"]
    assert "iso" in it["required"]
    assert "shutter_speed" in it["required"]
    assert "chromatic_aberration" in it["required"]


def test_bad_inputs():
    node = PSN_Camera_Degradation()
    # non-tensor image
    try:
        node.run("not a tensor", "50mm f/1.4", 400, 0.01, 0.3)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    # wrong shape
    try:
        node.run(torch.rand(4, 4), "50mm f/1.4", 400, 0.01, 0.3)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # unknown lens
    try:
        node.run(make_image(), "9000mm f/0.1", 400, 0.01, 0.3)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # out-of-range chromatic aberration
    try:
        node.run(make_image(), "50mm f/1.4", 400, 0.01, 1.5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # negative iso
    try:
        node.run(make_image(), "50mm f/1.4", -5, 0.01, 0.3)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_no_in_place_mutation():
    img = make_image(seed=1)
    snapshot = img.clone()
    node = PSN_Camera_Degradation()
    node.run(img, "50mm f/1.4", 3200, 0.01, 0.5)
    assert torch.equal(img, snapshot), "input image was modified in place"


def test_iso_increases_noise_std():
    node = PSN_Camera_Degradation()
    img = make_image(b=1, h=32, w=32, seed=2)
    out_low, = node.run(img, "24mm f/2.8", 100, 0.01, 0.0)
    out_high, = node.run(img, "24mm f/2.8", 12800, 0.01, 0.0)
    # compare against the deterministic (noise-free) pipeline
    base = _vignette(_gaussian_blur(img, 0.6), 0.20)
    std_low = (out_low - base).std().item()
    std_high = (out_high - base).std().item()
    assert std_high > std_low, f"high ISO should be noisier: {std_high} vs {std_low}"


def test_chromatic_aberration_shifts_channels():
    # red stripe in the middle of a black image
    img = torch.zeros(1, 16, 16, 3)
    img[:, 7:9, :, 0] = 1.0
    out = _chromatic_aberration(img, 2.0)
    # red shifted up-left: its stripe should now sit at rows 5:7
    assert out[0, 5, 8, 0].item() == 1.0, "red channel should be shifted up-left"
    assert out[0, 7, 8, 0].item() == 0.0, "red stripe should have moved"
    # blue (was 0) stays 0
    assert out[..., 2].sum().item() == 0.0
    # green (reference) unchanged
    assert torch.equal(out[..., 1], img[..., 1])
    # now a blue stripe: should shift down-right to rows 9:11
    img_b = torch.zeros(1, 16, 16, 3)
    img_b[:, 7:9, :, 2] = 1.0
    out_b = _chromatic_aberration(img_b, 2.0)
    assert out_b[0, 9, 8, 2].item() == 1.0, "blue channel should be shifted down-right"
    assert out_b[0, 7, 8, 2].item() == 0.0, "blue stripe should have moved"
    # zero amount -> unchanged
    out0 = _chromatic_aberration(img, 0.0)
    assert torch.equal(out0, img)


def test_vignette_darkens_edges():
    img = torch.ones(1, 16, 16, 3)
    out = _vignette(img, 0.5)
    centre = out[0, 8, 8, 0].item()
    corner = out[0, 0, 0, 0].item()
    assert centre > corner, f"centre {centre} should be brighter than corner {corner}"
    assert corner < 1.0
    # zero strength -> unchanged
    assert torch.equal(_vignette(img, 0.0), img)


def test_full_pipeline_smoke():
    node = PSN_Camera_Degradation()
    img = make_image(b=2, h=24, w=24, seed=3)
    out, = node.run(img, "50mm f/1.4", 3200, 0.01, 0.5)
    assert out.shape == img.shape
    assert out.dtype == torch.float32
    assert out.min().item() >= 0.0 and out.max().item() <= 1.0
    # vignette: mean of border pixels should be darker than centre mean
    border = torch.cat([out[:, 0, :, :], out[:, -1, :, :], out[:, :, 0, :], out[:, :, -1, :]])
    centre = out[:, 6:18, 6:18, :]
    assert border.mean().item() < centre.mean().item(), "edges should be darker (vignette)"


def test_gaussian_blur_preserves_mean_and_shape():
    img = make_image(b=1, h=16, w=16, seed=4)
    out = _gaussian_blur(img, 1.5)
    assert out.shape == img.shape
    # blur of a constant image is the same constant in the interior
    # (zero-padding at the border darkens the edges slightly)
    const = torch.full((1, 16, 16, 3), 0.7)
    outc = _gaussian_blur(const, 1.0)
    assert torch.allclose(outc[:, 3:-3, 3:-3, :], const[:, 3:-3, 3:-3, :], atol=1e-4)
    # zero sigma -> identity
    assert torch.equal(_gaussian_blur(img, 0.0), img)


def test_poisson_noise_zero_iso_is_identity():
    img = make_image(seed=5)
    assert torch.equal(_poisson_noise(img, 0), img)
    assert torch.equal(_gaussian_sensor_noise(img, 0), img)


def test_as_image_validation():
    try:
        _as_image([1, 2, 3])
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    try:
        _as_image(torch.rand(4, 4, 4))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        _as_image(torch.empty(0, 4, 4, 3))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


if __name__ == "__main__":
    test_module_mappings()
    test_bad_inputs()
    test_no_in_place_mutation()
    test_iso_increases_noise_std()
    test_chromatic_aberration_shifts_channels()
    test_vignette_darkens_edges()
    test_full_pipeline_smoke()
    test_gaussian_blur_preserves_mean_and_shape()
    test_poisson_noise_zero_iso_is_identity()
    test_as_image_validation()
    print("ok")
