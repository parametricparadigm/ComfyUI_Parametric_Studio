"""Tests for n_3_civitai_compatible_image_saver_for_com.

Run:  python3 -B test_n_3_civitai_compatible_image_saver_for_com.py
Must print 'ok' and exit 0.
"""

import json
import os
import tempfile

import torch

from PIL import Image

from n_3_civitai_compatible_image_saver_for_com import (
    PSN_Civitai_Compat_Save,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _build_civitai_metadata,
    _tensor_to_pil,
)


def _make_image(b=1, h=8, w=8, c=3):
    """Create a small random IMAGE tensor in [0,1]."""
    return torch.rand(b, h, w, c)


def _save_and_read(node, image, prompt="a cat", neg="blurry", model="test.ckpt", prefix="test"):
    """Run the node, read the PNG back, return (path, meta_dict, pil_img)."""
    (path,) = node.run(image, prompt, neg, model, prefix)
    assert os.path.isfile(path), f"saved file missing: {path}"
    img = Image.open(path)
    assert img.format == "PNG", f"expected PNG, got {img.format}"
    # read metadata
    params = img.text.get("parameters")
    assert params is not None, "missing 'parameters' text chunk"
    meta = json.loads(params)
    return path, meta, img


def test_1_module_mappings():
    """NODE_CLASS_MAPPINGS and display names exist and are correct."""
    assert "PSN_Civitai_Compat_Save" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Civitai_Compat_Save"] is PSN_Civitai_Compat_Save
    assert "PSN_Civitai_Compat_Save" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Civitai_Compat_Save"] == "Civitai-Compatible Image Saver"


def test_2_input_types():
    """INPUT_TYPES classmethod returns the expected schema."""
    it = PSN_Civitai_Compat_Save.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "image" in req and req["image"] == ("IMAGE",)
    assert "prompt" in req
    assert "negative_prompt" in req
    assert "model_name" in req
    assert "filename_prefix" in req
    assert PSN_Civitai_Compat_Save.RETURN_TYPES == ("STRING",)
    assert PSN_Civitai_Compat_Save.RETURN_NAMES == ("saved_path",)
    assert PSN_Civitai_Compat_Save.FUNCTION == "run"
    assert PSN_Civitai_Compat_Save.CATEGORY.startswith("ParametricStudio/")


def test_3_metadata_structure():
    """_build_civitai_metadata returns the expected keys."""
    meta = _build_civitai_metadata("a dog", "ugly", "dog.ckpt")
    assert meta["prompt"] == "a dog"
    assert meta["negative_prompt"] == "ugly"
    assert meta["model"] == "dog.ckpt"
    assert meta["source"] == "ComfyUI"


def test_4_save_and_read_metadata():
    """End-to-end: save image, read PNG, verify JSON in parameters chunk."""
    node = PSN_Civitai_Compat_Save()
    img = _make_image(1, 16, 16, 3)
    path, meta, pil = _save_and_read(node, img, "a cat", "blurry", "test.ckpt", "test")
    assert meta["prompt"] == "a cat"
    assert meta["negative_prompt"] == "blurry"
    assert meta["model"] == "test.ckpt"
    # also check the 'prompt' chunk
    prompt_chunk = pil.text.get("prompt")
    assert prompt_chunk is not None, "missing 'prompt' text chunk"
    meta2 = json.loads(prompt_chunk)
    assert meta2["prompt"] == "a cat"
    # image dimensions preserved
    assert pil.size == (16, 16)
    os.remove(path)


def test_5_batch_and_channels():
    """Batch > 1 uses first element; single-channel and RGBA work."""
    node = PSN_Civitai_Compat_Save()
    # batch of 3, 8x8, 3 channels
    img3 = _make_image(3, 8, 8, 3)
    path, meta, pil = _save_and_read(node, img3, "batch", "", "m", "batch_test")
    assert pil.size == (8, 8)
    assert pil.mode == "RGB"
    os.remove(path)

    # single channel
    img1 = _make_image(1, 4, 4, 1)
    path, meta, pil = _save_and_read(node, img1, "mono", "", "m", "mono_test")
    assert pil.mode == "L"
    os.remove(path)

    # RGBA
    img4 = _make_image(1, 4, 4, 4)
    path, meta, pil = _save_and_read(node, img4, "rgba", "", "m", "rgba_test")
    assert pil.mode == "RGBA"
    os.remove(path)


def test_6_bad_input():
    """Non-tensor and wrong-dim inputs raise errors."""
    node = PSN_Civitai_Compat_Save()
    # non-tensor
    try:
        node.run("not a tensor", "p", "n", "m", "x")
        assert False, "expected TypeError for non-tensor"
    except TypeError:
        pass
    # wrong dims (3D instead of 4D)
    try:
        node.run(torch.rand(8, 8, 3), "p", "n", "m", "x")
        assert False, "expected ValueError for 3D tensor"
    except ValueError:
        pass
    # bad channel count
    try:
        node.run(torch.rand(1, 8, 8, 5), "p", "n", "m", "x")
        assert False, "expected ValueError for C=5"
    except ValueError:
        pass


def test_7_empty_and_special_strings():
    """Empty prompt/negative/model and special chars in filename_prefix."""
    node = PSN_Civitai_Compat_Save()
    img = _make_image(1, 4, 4, 3)
    path, meta, pil = _save_and_read(node, img, "", "", "", "")
    assert meta["prompt"] == ""
    assert meta["negative_prompt"] == ""
    assert meta["model"] == ""
    os.remove(path)

    # filename_prefix with special chars gets sanitised
    path, meta, pil = _save_and_read(node, img, "p", "n", "m", "my/file:with*specials")
    assert "/" not in path
    assert ":" not in path
    assert "*" not in path
    assert os.path.isfile(path)
    os.remove(path)


def test_8_long_prompt():
    """A very long prompt still round-trips through PNG metadata."""
    node = PSN_Civitai_Compat_Save()
    img = _make_image(1, 4, 4, 3)
    long_prompt = "a " * 500  # ~2000 chars
    path, meta, pil = _save_and_read(node, img, long_prompt, "neg", "m", "long")
    assert meta["prompt"] == long_prompt
    os.remove(path)


def test_9_no_inplace_modification():
    """The input tensor must not be modified by the node."""
    node = PSN_Civitai_Compat_Save()
    img = _make_image(1, 4, 4, 3)
    original = img.clone()
    path, meta, pil = _save_and_read(node, img, "p", "n", "m", "inplace")
    assert torch.equal(img, original), "input tensor was modified in place"
    os.remove(path)


if __name__ == "__main__":
    test_1_module_mappings()
    test_2_input_types()
    test_3_metadata_structure()
    test_4_save_and_read_metadata()
    test_5_batch_and_channels()
    test_6_bad_input()
    test_7_empty_and_special_strings()
    test_8_long_prompt()
    test_9_no_inplace_modification()
    print("ok")
