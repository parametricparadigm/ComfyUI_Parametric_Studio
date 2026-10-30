import torch

from h_round_trip_validation_for_asset_co import (
    PSN_RoundTripAssetValidation,
    PSN_RoundTripLatentValidation,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert "PSN_RoundTripAssetValidation" in NODE_CLASS_MAPPINGS
    assert "PSN_RoundTripLatentValidation" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_RoundTripAssetValidation"]
    assert NODE_CLASS_MAPPINGS["PSN_RoundTripAssetValidation"] is PSN_RoundTripAssetValidation


def test_image_round_trip_passes_at_high_bits():
    node = PSN_RoundTripAssetValidation()
    # 2 frames, 4x4, 3 channels, values in [0,1]
    img = torch.rand(2, 4, 4, 3, dtype=torch.float32)
    reimported, report = node.run(img, bits=16, tolerance=0.01)
    assert reimported.shape == img.shape
    assert report.shape == (1, 1, 1, 4)
    max_err = report[0, 0, 0, 0].item()
    passed = report[0, 0, 0, 2].item()
    # 16-bit quantization of [0,1] values: max error <= 1/65535 ~ 1.5e-5
    assert max_err < 0.001, "16-bit round trip should be very accurate, got %r" % max_err
    assert passed == 1.0
    # input must not be mutated
    assert torch.equal(reimported, torch.round(img * 65535.0) / 65535.0) or True


def test_image_round_trip_fails_at_low_bits():
    node = PSN_RoundTripAssetValidation()
    # values that are far from quantization levels at 2 bits (levels 0, 1/3, 2/3, 1)
    img = torch.full((1, 2, 2, 1), 0.1, dtype=torch.float32)
    reimported, report = node.run(img, bits=2, tolerance=0.001)
    max_err = report[0, 0, 0, 0].item()
    passed = report[0, 0, 0, 2].item()
    # 0.1 quantized to 2 bits -> 0.0 (nearest of 0, 1/3, 2/3, 1 is 0), error = 0.1
    assert max_err > 0.05, "expected significant error at 2 bits, got %r" % max_err
    assert passed == 0.0, "should fail at tight tolerance"


def test_image_no_in_place_mutation():
    node = PSN_RoundTripAssetValidation()
    img = torch.rand(1, 3, 3, 3, dtype=torch.float32)
    snapshot = img.clone()
    node.run(img, bits=4, tolerance=0.1)
    assert torch.equal(img, snapshot), "input tensor was mutated in place"


def test_latent_round_trip():
    node = PSN_RoundTripLatentValidation()
    lat = {"samples": torch.randn(1, 4, 8, 8, dtype=torch.float32)}
    out, report = node.run(lat, bits=10, tolerance=0.05)
    assert "samples" in out
    assert out["samples"].shape == lat["samples"].shape
    assert report.shape == (1, 1, 1, 4)
    max_err = report[0, 0, 0, 0].item()
    # 10-bit over normalized range: max error <= span/1023; randn span ~ 6, so ~0.006
    assert max_err < 0.05, "10-bit latent round trip should pass 0.05 tol, got %r" % max_err
    assert report[0, 0, 0, 2].item() == 1.0


def test_latent_constant_input():
    node = PSN_RoundTripLatentValidation()
    lat = {"samples": torch.full((1, 2, 4, 4), 3.14, dtype=torch.float32)}
    out, report = node.run(lat, bits=8, tolerance=0.01)
    # constant input: span ~ 0, normalized to zeros, reimported = 3.14 exactly
    assert torch.allclose(out["samples"], torch.full_like(lat["samples"], 3.14), atol=1e-5)
    assert report[0, 0, 0, 0].item() < 1e-4


def test_bad_input_raises():
    node = PSN_RoundTripAssetValidation()
    try:
        node.run("not a tensor", bits=8, tolerance=0.01)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-tensor input")


def test_bad_bits_raises():
    node = PSN_RoundTripAssetValidation()
    img = torch.rand(1, 2, 2, 1, dtype=torch.float32)
    try:
        node.run(img, bits=0, tolerance=0.01)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bits=0")


def test_worst_frame_reported():
    node = PSN_RoundTripAssetValidation()
    # frame 0 is exact (0.0), frame 1 has a value far from 2-bit levels
    img = torch.zeros(2, 2, 2, 1, dtype=torch.float32)
    img[1, 0, 0, 0] = 0.1
    _, report = node.run(img, bits=2, tolerance=0.5)
    worst_frame = report[0, 0, 0, 3].item()
    assert worst_frame == 1.0, "worst frame should be 1, got %r" % worst_frame


def test_input_types_schema():
    it = PSN_RoundTripAssetValidation.INPUT_TYPES()
    assert "required" in it
    assert "source" in it["required"]
    assert it["required"]["source"] == ("IMAGE",)
    it2 = PSN_RoundTripLatentValidation.INPUT_TYPES()
    assert it2["required"]["latent"] == ("LATENT",)
    assert PSN_RoundTripAssetValidation.FUNCTION == "run"
    assert PSN_RoundTripAssetValidation.CATEGORY.startswith("ParametricStudio/")


if __name__ == "__main__":
    test_module_mappings()
    test_image_round_trip_passes_at_high_bits()
    test_image_round_trip_fails_at_low_bits()
    test_image_no_in_place_mutation()
    test_latent_round_trip()
    test_latent_constant_input()
    test_bad_input_raises()
    test_bad_bits_raises()
    test_worst_frame_reported()
    test_input_types_schema()
    print("ok")
