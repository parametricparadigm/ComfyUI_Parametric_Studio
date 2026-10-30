"""Tests for n_4_procedural_pattern_masking_for_texture (plain asserts, no pytest)."""

import torch

from n_4_procedural_pattern_masking_for_texture import (
    PSN_ProceduralPatternGenerator,
    PSN_BooleanMaskOperation,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert "PSN_ProceduralPatternGenerator" in NODE_CLASS_MAPPINGS
    assert "PSN_BooleanMaskOperation" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ProceduralPatternGenerator"]
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_BooleanMaskOperation"]
    # INPUT_TYPES classmethods exist and are well-formed
    it = PSN_ProceduralPatternGenerator.INPUT_TYPES()
    assert "required" in it
    assert "pattern_type" in it["required"]
    assert PSN_ProceduralPatternGenerator.FUNCTION == "run"
    assert PSN_ProceduralPatternGenerator.RETURN_TYPES == ("MASK",)
    assert PSN_BooleanMaskOperation.RETURN_NAMES == ("result_mask",)


def test_perlin_deterministic_and_nonuniform():
    gen = PSN_ProceduralPatternGenerator()
    m1 = gen.run(64, 64, "perlin", 4.0, 1234)[0]
    m2 = gen.run(64, 64, "perlin", 4.0, 1234)[0]
    assert m1.shape == (1, 64, 64)
    assert m1.dtype == torch.float32
    assert torch.equal(m1, m2), "same seed must be deterministic"
    assert m1.min() >= 0.0 and m1.max() <= 1.0
    assert m1.std() > 0.01, "perlin mask must not be uniform"
    # different seed -> different pattern
    m3 = gen.run(64, 64, "perlin", 4.0, 9999)[0]
    assert not torch.equal(m1, m3)


def test_all_pattern_types():
    gen = PSN_ProceduralPatternGenerator()
    for pt in ("perlin", "voronoi", "sine", "fractal"):
        m = gen.run(32, 48, pt, 3.0, 7)[0]
        assert m.shape == (1, 48, 32), pt
        assert m.min() >= 0.0 and m.max() <= 1.0, pt
        assert m.std() > 0.0, pt
    # voronoi determinism at larger size (CPU smoke)
    v1 = gen.run(128, 128, "voronoi", 6.0, 42)[0]
    v2 = gen.run(128, 128, "voronoi", 6.0, 42)[0]
    assert torch.equal(v1, v2)


def test_generator_bad_input():
    gen = PSN_ProceduralPatternGenerator()
    try:
        gen.run(0, 64, "perlin", 4.0, 1)
        raise AssertionError("expected ValueError for width=0")
    except ValueError:
        pass
    try:
        gen.run(64, 64, "bogus", 4.0, 1)
        raise AssertionError("expected ValueError for bad pattern_type")
    except ValueError:
        pass
    try:
        gen.run(64, 64, "perlin", -1.0, 1)
        raise AssertionError("expected ValueError for negative scale")
    except ValueError:
        pass


def test_boolean_ops():
    op = PSN_BooleanMaskOperation()
    a = torch.zeros(1, 4, 4)
    a[0, 0, 0] = 1.0
    a[0, 1, 1] = 0.5
    b = torch.zeros(1, 4, 4)
    b[0, 0, 0] = 1.0
    b[0, 1, 1] = 0.0
    b[0, 2, 2] = 1.0

    r_and = op.run(a, b, "and")[0]
    assert r_and[0, 0, 0] == 1.0
    assert r_and[0, 1, 1] == 0.0, "AND: 0.5 & 0.0 must be 0"
    assert r_and[0, 2, 2] == 0.0

    r_or = op.run(a, b, "or")[0]
    assert r_or[0, 0, 0] == 1.0
    assert r_or[0, 1, 1] == 0.5
    assert r_or[0, 2, 2] == 1.0

    r_xor = op.run(a, b, "xor")[0]
    assert r_xor[0, 0, 0] == 0.0, "XOR of equal values is 0"
    assert abs(r_xor[0, 1, 1] - 0.5) < 1e-6
    assert r_xor[0, 2, 2] == 1.0

    r_diff = op.run(a, b, "difference")[0]
    assert r_diff[0, 0, 0] == 0.0
    # difference = a - b clamped: a[1,1]=0.5, b[1,1]=0 -> 0.5
    assert abs(r_diff[0, 1, 1] - 0.5) < 1e-6
    # reversed difference: b - a at (1,1) = 0 - 0.5 -> 0
    r_diff2 = op.run(b, a, "difference")[0]
    assert r_diff2[0, 1, 1] == 0.0


def test_boolean_bad_input():
    op = PSN_BooleanMaskOperation()
    a = torch.zeros(1, 4, 4)
    b = torch.zeros(1, 4, 4)
    # shape mismatch
    try:
        op.run(a, torch.zeros(1, 5, 4), "and")
        raise AssertionError("expected ValueError for shape mismatch")
    except ValueError:
        pass
    # non-tensor input
    try:
        op.run(a, "not a tensor", "and")
        raise AssertionError("expected ValueError for non-tensor mask")
    except ValueError:
        pass
    # wrong rank
    try:
        op.run(a, torch.zeros(4, 4), "and")
        raise AssertionError("expected ValueError for 2D mask")
    except ValueError:
        pass
    # unknown operation
    try:
        op.run(a, b, "nand")
        raise AssertionError("expected ValueError for unknown op")
    except ValueError:
        pass


def test_no_inplace_mutation():
    op = PSN_BooleanMaskOperation()
    a = torch.zeros(1, 4, 4)
    a[0, 0, 0] = 1.0
    b = torch.ones(1, 4, 4)
    a_snap = a.clone()
    b_snap = b.clone()
    op.run(a, b, "and")
    op.run(a, b, "xor")
    assert torch.equal(a, a_snap), "mask_a must not be modified in place"
    assert torch.equal(b, b_snap), "mask_b must not be modified in place"


def test_end_to_end_pipeline():
    gen = PSN_ProceduralPatternGenerator()
    op = PSN_BooleanMaskOperation()
    m1 = gen.run(64, 64, "perlin", 4.0, 5)[0]
    m2 = gen.run(64, 64, "voronoi", 4.0, 5)[0]
    combined = op.run(m1, m2, "and")[0]
    assert combined.shape == (1, 64, 64)
    # AND can only be <= each input
    assert (combined <= m1 + 1e-6).all()
    assert (combined <= m2 + 1e-6).all()


if __name__ == "__main__":
    test_module_mappings()
    test_perlin_deterministic_and_nonuniform()
    test_all_pattern_types()
    test_generator_bad_input()
    test_boolean_ops()
    test_boolean_bad_input()
    test_no_inplace_mutation()
    test_end_to_end_pipeline()
    print("ok")
