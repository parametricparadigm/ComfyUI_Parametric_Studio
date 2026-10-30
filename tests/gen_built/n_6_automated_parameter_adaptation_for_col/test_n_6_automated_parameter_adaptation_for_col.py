import json
import math

import torch

from n_6_automated_parameter_adaptation_for_col import (
    PSN_AutoColorAdapt,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _as_image,
    _analyze,
    _compute_params,
    _apply_params,
    _rgb,
)


def _img(val, h=8, w=8, c=3):
    return torch.full((1, h, w, c), val, dtype=torch.float32)


def test_module_mappings():
    assert "PSN_AutoColorAdapt" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_AutoColorAdapt"] is PSN_AutoColorAdapt
    assert "PSN_AutoColorAdapt" in NODE_DISPLAY_NAME_MAPPINGS
    assert PSN_AutoColorAdapt.FUNCTION == "run"
    assert PSN_AutoColorAdapt.CATEGORY.startswith("ParametricStudio/")
    assert PSN_AutoColorAdapt.RETURN_TYPES == ("IMAGE", "STRING")
    assert PSN_AutoColorAdapt.RETURN_NAMES == ("image", "params_json")


def test_input_types():
    it = PSN_AutoColorAdapt.INPUT_TYPES()
    assert "image" in it["required"]
    assert it["required"]["image"] == ("IMAGE",)
    assert "model_family" in it["required"]
    assert "target_style" in it["required"]
    mf = it["required"]["model_family"]
    assert "SDXL" in mf[0] and "Flux.1" in mf[0] and "SD1.5" in mf[0] and "Custom" in mf[0]
    ts = it["required"]["target_style"]
    assert "Neutral" in ts[0] and "Vibrant" in ts[0] and "Moody" in ts[0] and "Cinematic" in ts[0]


def test_dark_image_exposure_increased():
    node = PSN_AutoColorAdapt()
    dark = _img(0.1)
    out_img, out_json = node.run(dark, "SDXL", "Neutral")
    params = json.loads(out_json)
    assert params["exposure"] > 0.0, "expected positive exposure for dark image, got %s" % params["exposure"]
    assert out_img.mean() > dark.mean()
    assert out_img.shape == dark.shape
    assert out_img.min() >= 0.0 and out_img.max() <= 1.0


def test_bright_image_exposure_decreased():
    node = PSN_AutoColorAdapt()
    bright = _img(0.9)
    out_img, out_json = node.run(bright, "SDXL", "Neutral")
    params = json.loads(out_json)
    assert params["exposure"] < 0.0, "expected negative exposure for bright image, got %s" % params["exposure"]
    assert out_img.mean() < bright.mean()


def test_vibrant_style_increases_saturation():
    node = PSN_AutoColorAdapt()
    gray = _img(0.5)
    _, json_v = node.run(gray, "SDXL", "Vibrant")
    _, json_n = node.run(gray, "SDXL", "Neutral")
    p_v = json.loads(json_v)
    p_n = json.loads(json_n)
    assert p_v["saturation"] > p_n["saturation"], "Vibrant should boost saturation vs Neutral"


def test_moody_style_lowers_exposure():
    node = PSN_AutoColorAdapt()
    mid = _img(0.5)
    _, json_m = node.run(mid, "SDXL", "Moody")
    _, json_n = node.run(mid, "SDXL", "Neutral")
    p_m = json.loads(json_m)
    p_n = json.loads(json_n)
    assert p_m["exposure"] < p_n["exposure"], "Moody should lower exposure vs Neutral"


def test_no_inplace_mutation():
    node = PSN_AutoColorAdapt()
    img = _img(0.3)
    snapshot = img.clone()
    node.run(img, "SDXL", "Vibrant")
    assert torch.equal(img, snapshot), "input image was mutated in place"


def test_bad_input_not_tensor():
    node = PSN_AutoColorAdapt()
    try:
        node.run("not a tensor", "SDXL", "Neutral")
        assert False, "expected TypeError"
    except TypeError:
        pass


def test_bad_input_wrong_dims():
    node = PSN_AutoColorAdapt()
    bad = torch.zeros(4, 4, 3)
    try:
        node.run(bad, "SDXL", "Neutral")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bad_input_bad_channels():
    node = PSN_AutoColorAdapt()
    bad = torch.zeros(1, 4, 4, 5)
    try:
        node.run(bad, "SDXL", "Neutral")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_single_channel_image():
    node = PSN_AutoColorAdapt()
    gray = _img(0.2, c=1)
    out_img, out_json = node.run(gray, "SD1.5", "Neutral")
    assert out_img.shape == (1, 8, 8, 1)
    params = json.loads(out_json)
    assert params["exposure"] > 0.0


def test_rgba_image_preserves_alpha():
    node = PSN_AutoColorAdapt()
    rgba = torch.zeros(1, 4, 4, 4, dtype=torch.float32)
    rgba[..., 0] = 0.3
    rgba[..., 1] = 0.4
    rgba[..., 2] = 0.5
    rgba[..., 3] = 0.7
    out_img, _ = node.run(rgba, "Flux.1", "Cinematic")
    assert out_img.shape == (1, 4, 4, 4)
    assert torch.allclose(out_img[..., 3], rgba[..., 3])


def test_params_bounded():
    node = PSN_AutoColorAdapt()
    very_dark = _img(0.0)
    _, j = node.run(very_dark, "SD1.5", "Vibrant")
    p = json.loads(j)
    assert -0.6 <= p["exposure"] <= 0.6
    assert -0.6 <= p["contrast"] <= 0.6
    assert -0.6 <= p["saturation"] <= 0.6
    assert -0.3 <= p["tint"] <= 0.3


def test_json_structure():
    node = PSN_AutoColorAdapt()
    img = _img(0.4)
    _, j = node.run(img, "Custom", "Cinematic")
    p = json.loads(j)
    assert "exposure" in p
    assert "contrast" in p
    assert "saturation" in p
    assert "tint" in p
    assert p["model_family"] == "Custom"
    assert p["target_style"] == "Cinematic"
    assert "stats" in p
    assert "mean_lum" in p["stats"]


def test_batch_of_images():
    node = PSN_AutoColorAdapt()
    batch = torch.rand(3, 8, 8, 3, dtype=torch.float32)
    out_img, _ = node.run(batch, "SDXL", "Neutral")
    assert out_img.shape == (3, 8, 8, 3)
    assert out_img.min() >= 0.0 and out_img.max() <= 1.0


def main():
    test_module_mappings()
    test_input_types()
    test_dark_image_exposure_increased()
    test_bright_image_exposure_decreased()
    test_vibrant_style_increases_saturation()
    test_moody_style_lowers_exposure()
    test_no_inplace_mutation()
    test_bad_input_not_tensor()
    test_bad_input_wrong_dims()
    test_bad_input_bad_channels()
    test_single_channel_image()
    test_rgba_image_preserves_alpha()
    test_params_bounded()
    test_json_structure()
    test_batch_of_images()
    print("ok")


if __name__ == "__main__":
    main()
