import torch

from h_adopt_a_non_failing_verification_p import (
    PSN_NonFailingVerify,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    verify_payload,
)


def test_module_mappings():
    assert "PSN_NonFailingVerify" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_NonFailingVerify"] is PSN_NonFailingVerify
    assert "PSN_NonFailingVerify" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_NonFailingVerify"], str)


def test_input_types_shape():
    spec = PSN_NonFailingVerify.INPUT_TYPES()
    assert "required" in spec and "optional" in spec
    assert "payload" in spec["required"]
    assert "label" in spec["required"]
    assert "strict" in spec["optional"]
    assert PSN_NonFailingVerify.FUNCTION == "run"
    assert PSN_NonFailingVerify.CATEGORY.startswith("ParametricStudio/")
    assert PSN_NonFailingVerify.RETURN_TYPES == ("IMAGE,MASK,LATENT", "STRING")
    assert PSN_NonFailingVerify.RETURN_NAMES == ("payload", "report")


def test_image_pass():
    node = PSN_NonFailingVerify()
    img = torch.rand(1, 8, 8, 3)  # valid 0..1 image
    out, report = node.run(img, label="img")
    assert isinstance(report, str)
    assert "PASS" in report
    assert torch.equal(out, img)  # passthrough, not mutated
    assert out is not img  # fresh copy


def test_image_out_of_range_warns_but_does_not_raise():
    node = PSN_NonFailingVerify()
    bad = torch.full((1, 4, 4, 3), 5.0)  # outside 0..1
    out, report = node.run(bad, label="bad")
    assert "WARN" in report
    assert "outside 0..1" in report
    assert torch.equal(out, bad)


def test_image_nan_warns():
    node = PSN_NonFailingVerify()
    t = torch.zeros(1, 4, 4, 3)
    t[0, 0, 0, 0] = float("nan")
    out, report = node.run(t, label="nan")
    assert "WARN" in report
    assert "NaN" in report


def test_latent_pass():
    node = PSN_NonFailingVerify()
    latent = {"samples": torch.randn(1, 4, 8, 8)}
    out, report = node.run(latent, label="lat")
    assert "PASS" in report
    assert isinstance(out, dict)
    assert torch.equal(out["samples"], latent["samples"])
    assert out is not latent  # dict copy


def test_mask_pass():
    node = PSN_NonFailingVerify()
    mask = torch.rand(1, 8, 8)
    out, report = node.run(mask, label="mask")
    assert "PASS" in report
    assert torch.equal(out, mask)


def test_bad_input_string_does_not_raise():
    node = PSN_NonFailingVerify()
    out, report = node.run("not a tensor", label="str")
    assert isinstance(report, str)
    assert "skipped" in report
    assert out == "not a tensor"


def test_bad_input_none_does_not_raise():
    node = PSN_NonFailingVerify()
    out, report = node.run(None, label="none")
    assert "skipped" in report
    assert out is None


def test_verify_payload_helper():
    lines, ok = verify_payload(torch.rand(1, 4, 4, 3))
    assert ok is True
    assert any("image" in ln for ln in lines)
    lines, ok = verify_payload(torch.full((1, 4, 4, 3), 9.0))
    assert ok is False
    assert any("outside" in ln for ln in lines)


def test_strict_flag_still_non_failing():
    node = PSN_NonFailingVerify()
    bad = torch.full((1, 4, 4, 3), 3.0)
    out, report = node.run(bad, label="strict", strict=True)
    # strict=True must NOT raise; it only changes the report wording
    assert "WARN" in report
    assert torch.equal(out, bad)


def test_no_in_place_mutation():
    node = PSN_NonFailingVerify()
    img = torch.rand(1, 4, 4, 3)
    snapshot = img.clone()
    node.run(img, label="x")
    assert torch.equal(img, snapshot)


if __name__ == "__main__":
    test_module_mappings()
    test_input_types_shape()
    test_image_pass()
    test_image_out_of_range_warns_but_does_not_raise()
    test_image_nan_warns()
    test_latent_pass()
    test_mask_pass()
    test_bad_input_string_does_not_raise()
    test_bad_input_none_does_not_raise()
    test_verify_payload_helper()
    test_strict_flag_still_non_failing()
    test_no_in_place_mutation()
    print("ok")
