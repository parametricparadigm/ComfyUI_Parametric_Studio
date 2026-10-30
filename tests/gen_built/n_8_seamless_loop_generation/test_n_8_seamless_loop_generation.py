import torch

import n_8_seamless_loop_generation as m


def test_mappings():
    assert "PSN_LoopPreparer" in m.NODE_CLASS_MAPPINGS
    assert "PSN_LoopAssembler" in m.NODE_CLASS_MAPPINGS
    assert m.NODE_DISPLAY_NAME_MAPPINGS["PSN_LoopPreparer"]
    assert m.PSN_LoopPreparer.FUNCTION == "run"
    assert m.PSN_LoopPreparer.CATEGORY.startswith("ParametricStudio/")
    assert m.PSN_LoopAssembler.RETURN_TYPES == ("IMAGE",)


def test_preparer_basic():
    # 8 frames, loop_length 8, blend 2 -> last 2 frames are blended.
    x = torch.arange(8 * 1 * 1 * 1, dtype=torch.float32).reshape(8, 1, 1, 1) / 8.0
    out = m.PSN_LoopPreparer().run(x, 8, 2)[0]
    assert out.shape == (8, 1, 1, 1)
    # First 6 frames unchanged.
    for i in range(6):
        assert torch.allclose(out[i], x[i])
    # Frame 6 (n-blend=6): weight a = 0/1 = 0 -> out = 0*head[0] + 1*tail[0]
    # tail[0] = x[6], head[0] = x[0]
    assert torch.allclose(out[6], x[6])
    # Frame 7: a = 1/1 = 1 -> out = 1*head[1] + 0*tail[1] = x[1]
    assert torch.allclose(out[7], x[1])


def test_preparer_no_blend():
    x = torch.rand(5, 2, 2, 3)
    out = m.PSN_LoopPreparer().run(x, 5, 0)[0]
    assert torch.allclose(out, x)


def test_preparer_short_batch_wraps():
    # 3 frames, loop_length 6 -> wraps to 6 frames.
    x = torch.arange(3, dtype=torch.float32).reshape(3, 1, 1, 1)
    out = m.PSN_LoopPreparer().run(x, 6, 0)[0]
    assert out.shape[0] == 6
    assert torch.allclose(out[0], x[0])
    assert torch.allclose(out[3], x[0])


def test_preparer_bad_input():
    # Wrong dim
    try:
        m.PSN_LoopPreparer().run(torch.zeros(4, 4), 4, 1)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Non-tensor
    try:
        m.PSN_LoopPreparer().run("nope", 4, 1)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    # Bad loop_length
    try:
        m.PSN_LoopPreparer().run(torch.zeros(4, 2, 2, 3), 1, 1)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_assembler_exact():
    x = torch.rand(10, 2, 2, 3)
    out = m.PSN_LoopAssembler().run(x, 10)[0]
    assert out.shape == (10, 2, 2, 3)
    assert torch.allclose(out, x)


def test_assembler_trims():
    x = torch.rand(10, 2, 2, 3)
    out = m.PSN_LoopAssembler().run(x, 4)[0]
    assert out.shape[0] == 4
    assert torch.allclose(out, x[:4])


def test_assembler_repeats():
    x = torch.rand(3, 2, 2, 3)
    out = m.PSN_LoopAssembler().run(x, 7)[0]
    assert out.shape[0] == 7
    assert torch.allclose(out[0], x[0])
    assert torch.allclose(out[3], x[0])
    assert torch.allclose(out[6], x[0])


def test_assembler_bad_input():
    try:
        m.PSN_LoopAssembler().run(torch.zeros(4, 4), 4)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        m.PSN_LoopAssembler().run(torch.zeros(4, 2, 2, 3), 0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_no_inplace():
    x = torch.rand(6, 2, 2, 3)
    x_copy = x.clone()
    m.PSN_LoopPreparer().run(x, 6, 2)
    m.PSN_LoopAssembler().run(x, 6)
    assert torch.allclose(x, x_copy)


def test_clamp():
    x = torch.full((4, 1, 1, 1), 5.0)
    out = m.PSN_LoopAssembler().run(x, 4)[0]
    assert out.max() <= 1.0
    x2 = torch.full((4, 1, 1, 1), -5.0)
    out2 = m.PSN_LoopAssembler().run(x2, 4)[0]
    assert out2.min() >= 0.0


if __name__ == "__main__":
    test_mappings()
    test_preparer_basic()
    test_preparer_no_blend()
    test_preparer_short_batch_wraps()
    test_preparer_bad_input()
    test_assembler_exact()
    test_assembler_trims()
    test_assembler_repeats()
    test_assembler_bad_input()
    test_no_inplace()
    test_clamp()
    print("ok")
