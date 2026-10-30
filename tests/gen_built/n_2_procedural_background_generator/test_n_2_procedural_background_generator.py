import math

import torch

from n_2_procedural_background_generator import (
    PSN_ProcGen_Patterns,
    PSN_ProcGen_OpticalIllusion,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_mappings():
    assert "PSN_ProcGen_Patterns" in NODE_CLASS_MAPPINGS
    assert "PSN_ProcGen_OpticalIllusion" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ProcGen_Patterns"] == "ProcGen Patterns"
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ProcGen_OpticalIllusion"] == "ProcGen Optical Illusion"


def test_input_types():
    it = PSN_ProcGen_Patterns.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "pattern_type" in req
    assert "width" in req
    assert "height" in req
    assert "param_1" in req
    assert "param_2" in req
    assert "seed" in req
    assert PSN_ProcGen_Patterns.RETURN_TYPES == ("IMAGE", "STRING")
    assert PSN_ProcGen_Patterns.FUNCTION == "run"
    assert PSN_ProcGen_Patterns.CATEGORY.startswith("ParametricStudio/")

    it2 = PSN_ProcGen_OpticalIllusion.INPUT_TYPES()
    assert "illusion_type" in it2["required"]
    assert PSN_ProcGen_OpticalIllusion.RETURN_TYPES == ("IMAGE",)


def test_checker_binary_and_dims():
    node = PSN_ProcGen_Patterns()
    img, meta = node.run("checker", 64, 32, 8.0, 0.0, 42)
    assert isinstance(img, torch.Tensor)
    assert img.shape == (1, 32, 64, 3)
    assert img.dtype == torch.float32
    assert img.min() >= 0.0 and img.max() <= 1.0
    # checker should be strictly binary (0 or 1)
    flat = img[0, :, :, 0].flatten()
    vals = set(flat.tolist())
    assert vals <= {0.0, 1.0}, f"expected binary values, got {vals}"
    assert 0.0 in vals and 1.0 in vals
    assert isinstance(meta, str)
    assert "pattern=checker" in meta
    assert "seed=42" in meta


def test_deterministic_seed():
    node = PSN_ProcGen_Patterns()
    a, _ = node.run("binary", 32, 32, 0.5, 4.0, 1234)
    b, _ = node.run("binary", 32, 32, 0.5, 4.0, 1234)
    c, _ = node.run("binary", 32, 32, 0.5, 4.0, 9999)
    assert torch.equal(a, b)
    assert not torch.equal(a, c)


def test_all_patterns_run():
    node = PSN_ProcGen_Patterns()
    for p in ["checker", "gradient", "halftone", "starburst", "binary"]:
        img, _ = node.run(p, 48, 40, 16.0, 0.5, 7)
        assert img.shape == (1, 40, 48, 3), p
        assert not torch.isnan(img).any(), p
        assert img.min() >= 0.0 and img.max() <= 1.0, p


def test_bad_pattern_type():
    node = PSN_ProcGen_Patterns()
    try:
        node.run("nope", 16, 16, 1.0, 0.5, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad pattern_type")


def test_bad_size():
    node = PSN_ProcGen_Patterns()
    for w, h in [(0, 16), (16, 0), (99999, 16)]:
        try:
            node.run("checker", w, h, 4.0, 0.5, 0)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for size {w}x{h}")


def test_illusions():
    node = PSN_ProcGen_OpticalIllusion()
    for t in ["moire", "spiral", "grid_distortion"]:
        img = node.run(t, 64, 64, 1.0)[0]
        assert img.shape == (1, 64, 64, 3), t
        assert not torch.isnan(img).any(), t
        assert img.min() >= 0.0 and img.max() <= 1.0, t


def test_illusion_bad_type():
    node = PSN_ProcGen_OpticalIllusion()
    try:
        node.run("warp", 16, 16, 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad illusion_type")


def test_no_inplace_mutation():
    # inputs are scalars/strings here, but ensure the node does not crash on repeated calls
    node = PSN_ProcGen_Patterns()
    for _ in range(3):
        img, _ = node.run("gradient", 24, 24, 45.0, 0.7, 1)
        assert img.shape == (1, 24, 24, 3)


def main():
    test_mappings()
    test_input_types()
    test_checker_binary_and_dims()
    test_deterministic_seed()
    test_all_patterns_run()
    test_bad_pattern_type()
    test_bad_size()
    test_illusions()
    test_illusion_bad_type()
    test_no_inplace_mutation()
    print("ok")


if __name__ == "__main__":
    main()
