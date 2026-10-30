import torch

from n_8_batch_resize_pad_for_datasets import (
    PSN_Batch_Resize_Pad,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_pad_color,
)


def make_node():
    return PSN_Batch_Resize_Pad()


def test_module_mappings():
    assert "PSN_Batch_Resize_Pad" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Batch_Resize_Pad"] is PSN_Batch_Resize_Pad
    assert "PSN_Batch_Resize_Pad" in NODE_DISPLAY_NAME_MAPPINGS
    assert PSN_Batch_Resize_Pad.FUNCTION == "run"
    assert PSN_Batch_Resize_Pad.RETURN_TYPES == ("IMAGE",)
    assert PSN_Batch_Resize_Pad.RETURN_NAMES == ("processed_images",)
    assert PSN_Batch_Resize_Pad.CATEGORY.startswith("ParametricStudio/")
    it = PSN_Batch_Resize_Pad.INPUT_TYPES()
    assert "images" in it["required"]
    assert "target_width" in it["required"]
    assert "target_height" in it["required"]
    assert "pad_color" in it["required"]


def test_uniform_output_size_and_centering():
    node = make_node()
    # 3 images with different aspect ratios, each as a batch of 1
    img1 = torch.rand(1, 100, 200, 3)  # wide
    img2 = torch.rand(1, 200, 100, 3)  # tall
    img3 = torch.rand(1, 150, 150, 3)  # square
    # Process each separately since they have different sizes
    out1 = node.run(img1, 64, 64, "#000000")[0]
    out2 = node.run(img2, 64, 64, "#000000")[0]
    out3 = node.run(img3, 64, 64, "#000000")[0]
    out = torch.cat([out1, out2, out3], dim=0)
    assert out.shape == (3, 64, 64, 3), f"unexpected shape {out.shape}"
    # all outputs should be in 0..1
    assert out.min() >= 0.0 and out.max() <= 1.0
    # check centering: for the square image (150x150 -> 64x64), the whole canvas is filled
    # so no padding; for wide image (100x200 -> 32x64), top/bottom rows are pad color (0)
    # img1: 100x200, scale = min(64/200, 64/100) = 0.32, new = 32x64, top pad = (64-32)//2 = 16
    assert torch.all(out[0, 0, :, :] == 0.0), "top rows of wide image should be pad color"
    assert torch.all(out[0, 15, :, :] == 0.0), "row 15 of wide image should be pad color"
    assert torch.all(out[0, 16, :, :] != 0.0), "row 16 of wide image should have content"
    # img2: 200x100, scale = min(64/100, 64/200) = 0.32, new = 64x32, left pad = (64-32)//2 = 16
    assert torch.all(out[1, :, 0, :] == 0.0), "left cols of tall image should be pad color"
    assert torch.all(out[1, :, 15, :] == 0.0), "col 15 of tall image should be pad color"
    assert torch.all(out[1, :, 16, :] != 0.0), "col 16 of tall image should have content"


def test_pad_color_white():
    node = make_node()
    img = torch.rand(1, 100, 200, 3)
    out = node.run(img, 64, 64, "#ffffff")[0]
    assert out.shape == (1, 64, 64, 3)
    # top rows should be white (1.0)
    assert torch.all(out[0, 0, :, :] == 1.0), "top rows should be white pad"


def test_pad_color_rgb_tuple():
    node = make_node()
    img = torch.rand(1, 100, 200, 3)
    out = node.run(img, 64, 64, "255,0,0")[0]
    assert out.shape == (1, 64, 64, 3)
    # top rows should be red (1,0,0)
    assert torch.all(out[0, 0, :, 0] == 1.0), "top rows R should be 1"
    assert torch.all(out[0, 0, :, 1] == 0.0), "top rows G should be 0"
    assert torch.all(out[0, 0, :, 2] == 0.0), "top rows B should be 0"


def test_no_inplace_modification():
    node = make_node()
    img = torch.rand(2, 100, 200, 3)
    original = img.clone()
    node.run(img, 64, 64, "#000000")
    assert torch.equal(img, original), "input tensor was modified in place"


def test_bad_input_not_tensor():
    node = make_node()
    try:
        node.run("not a tensor", 64, 64, "#000000")
        assert False, "should have raised TypeError"
    except TypeError:
        pass


def test_bad_input_wrong_dims():
    node = make_node()
    try:
        node.run(torch.rand(100, 200, 3), 64, 64, "#000000")  # 3D, missing batch
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_pad_color():
    node = make_node()
    img = torch.rand(1, 100, 200, 3)
    try:
        node.run(img, 64, 64, "not_a_color")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_single_pixel_image():
    node = make_node()
    img = torch.rand(1, 1, 1, 3)
    out = node.run(img, 8, 8, "#000000")[0]
    assert out.shape == (1, 8, 8, 3)
    # 1x1 image scaled to fit 8x8: scale = min(8/1, 8/1) = 8, new = 8x8, no padding
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_grayscale_image():
    node = make_node()
    img = torch.rand(1, 100, 200, 1)  # grayscale
    out = node.run(img, 64, 64, "#000000")[0]
    assert out.shape == (1, 64, 64, 1)


def test_rgba_image():
    node = make_node()
    img = torch.rand(1, 100, 200, 4)  # RGBA
    out = node.run(img, 64, 64, "#000000")[0]
    assert out.shape == (1, 64, 64, 4)


def test_parse_pad_color_hex():
    t = _parse_pad_color("#ff0000")
    assert torch.allclose(t, torch.tensor([1.0, 0.0, 0.0]))
    t = _parse_pad_color("#0f0")
    assert torch.allclose(t, torch.tensor([0.0, 1.0, 0.0]))
    t = _parse_pad_color("#808080")
    assert torch.allclose(t, torch.tensor([128/255.0, 128/255.0, 128/255.0]))


def test_parse_pad_color_grayscale():
    t = _parse_pad_color("128")
    assert t.shape == (3,)
    assert torch.allclose(t, torch.full((3,), 128/255.0))
    t = _parse_pad_color("0.5")
    assert torch.allclose(t, torch.full((3,), 0.5))


def test_already_target_size():
    node = make_node()
    img = torch.rand(1, 64, 64, 3)
    out = node.run(img, 64, 64, "#000000")[0]
    assert out.shape == (1, 64, 64, 3)
    # no padding, content should be the same (bilinear at same size is identity)
    assert torch.allclose(out[0], img[0], atol=1e-5)


def test_batch_of_100():
    node = make_node()
    img = torch.rand(100, 512, 512, 3)
    out = node.run(img, 256, 256, "#000000")[0]
    assert out.shape == (100, 256, 256, 3)
    assert out.min() >= 0.0 and out.max() <= 1.0


if __name__ == "__main__":
    test_module_mappings()
    test_uniform_output_size_and_centering()
    test_pad_color_white()
    test_pad_color_rgb_tuple()
    test_no_inplace_modification()
    test_bad_input_not_tensor()
    test_bad_input_wrong_dims()
    test_bad_pad_color()
    test_single_pixel_image()
    test_grayscale_image()
    test_rgba_image()
    test_parse_pad_color_hex()
    test_parse_pad_color_grayscale()
    test_already_target_size()
    test_batch_of_100()
    print("ok")
