import json

import torch

from n_6_batch_image_processing_utility import (
    PSN_Batch_Filter_Chain,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    parse_filter_chain,
    apply_filter_chain,
)


def make_batch(b=4, h=8, w=8, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(b, h, w, c, generator=g)


def test_module_mappings():
    assert "PSN_Batch_Filter_Chain" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Batch_Filter_Chain"] is PSN_Batch_Filter_Chain
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Batch_Filter_Chain"] == "Batch Filter Chain"
    node = PSN_Batch_Filter_Chain()
    assert node.FUNCTION == "run"
    assert node.RETURN_TYPES == ("IMAGE",)
    assert node.RETURN_NAMES == ("processed_batch",)
    assert node.CATEGORY.startswith("ParametricStudio/")
    it = PSN_Batch_Filter_Chain.INPUT_TYPES()
    assert "image_batch" in it["required"]
    assert "filter_chain" in it["required"]
    assert "parallel" in it["required"]


def test_parse_chain():
    chain = parse_filter_chain('[{"name": "blur", "radius": 2}, "sharpen"]')
    assert chain == [("blur", {"radius": 2}), ("sharpen", {})]
    assert parse_filter_chain("[]") == []
    # unknown filter
    try:
        parse_filter_chain('["nope"]')
        raise AssertionError("expected ValueError for unknown filter")
    except ValueError:
        pass
    # bad json
    try:
        parse_filter_chain("not json")
        raise AssertionError("expected ValueError for bad json")
    except ValueError:
        pass
    # not a list
    try:
        parse_filter_chain('{"name": "blur"}')
        raise AssertionError("expected ValueError for non-list")
    except ValueError:
        pass
    # non-string input
    try:
        parse_filter_chain(123)
        raise AssertionError("expected TypeError for non-string")
    except TypeError:
        pass


def test_blur_sharpen_differs_and_matches_sequential():
    img = make_batch()
    chain = parse_filter_chain('[{"name": "blur", "radius": 1}, {"name": "sharpen", "amount": 1.0, "radius": 1}]')
    out = apply_filter_chain(img, chain, parallel=True)
    assert out.shape == img.shape
    assert not torch.equal(out, img)
    # sequential application of the two filters equals the chain result
    from n_6_batch_image_processing_utility import _FILTERS, _clamp01
    y = img.clone()
    y = _clamp01(_FILTERS["blur"](y, {"radius": 1}))
    y = _clamp01(_FILTERS["sharpen"](y, {"amount": 1.0, "radius": 1}))
    assert torch.allclose(out, y, atol=1e-6)
    # input not modified
    assert torch.equal(img, make_batch())


def test_parallel_matches_serial():
    img = make_batch(b=4, seed=7)
    chain = parse_filter_chain('[{"name": "brightness", "value": 0.1}, {"name": "contrast", "value": 1.2}, {"name": "blur", "radius": 1}]')
    par = apply_filter_chain(img, chain, parallel=True)
    ser = apply_filter_chain(img, chain, parallel=False)
    assert torch.allclose(par, ser, atol=1e-6)


def test_batch_of_4_smoke():
    img = make_batch(b=4, h=16, w=16, seed=3)
    chain = parse_filter_chain('[{"name": "blur", "radius": 1}, {"name": "saturate", "value": 1.5}, {"name": "gamma", "gamma": 1.2}]')
    out = apply_filter_chain(img, chain, parallel=True)
    assert out.shape == (4, 16, 16, 3)
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert not torch.equal(out, img)


def test_bad_image_input():
    node = PSN_Batch_Filter_Chain()
    # wrong ndim
    try:
        node.run(torch.rand(8, 8, 3), "[]", True)
        raise AssertionError("expected ValueError for 3D image")
    except ValueError:
        pass
    # not a tensor
    try:
        node.run("hello", "[]", True)
        raise AssertionError("expected TypeError for non-tensor")
    except TypeError:
        pass
    # bad channel count
    try:
        node.run(torch.rand(1, 4, 4, 5), "[]", True)
        raise AssertionError("expected ValueError for 5 channels")
    except ValueError:
        pass


def test_empty_chain_identity():
    img = make_batch(seed=11)
    out = apply_filter_chain(img, parse_filter_chain("[]"), parallel=True)
    assert torch.allclose(out, img, atol=1e-6)


def test_invert_and_threshold():
    img = torch.full((1, 4, 4, 3), 0.3)
    out = apply_filter_chain(img, parse_filter_chain('["invert"]'), parallel=True)
    assert torch.allclose(out, torch.full((1, 4, 4, 3), 0.7), atol=1e-6)
    out2 = apply_filter_chain(img, parse_filter_chain('[{"name": "threshold", "level": 0.5}]'), parallel=True)
    assert torch.allclose(out2, torch.zeros(1, 4, 4, 3), atol=1e-6)


def test_alpha_channel_preserved():
    img = torch.rand(2, 6, 6, 4)
    chain = parse_filter_chain('["grayscale"]')
    out = apply_filter_chain(img, chain, parallel=True)
    assert out.shape == (2, 6, 6, 4)
    assert torch.allclose(out[..., 3:], img[..., 3:], atol=1e-6)


if __name__ == "__main__":
    test_module_mappings()
    test_parse_chain()
    test_blur_sharpen_differs_and_matches_sequential()
    test_parallel_matches_serial()
    test_batch_of_4_smoke()
    test_bad_image_input()
    test_empty_chain_identity()
    test_invert_and_threshold()
    test_alpha_channel_preserved()
    print("ok")
