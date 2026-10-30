import torch

from n_7_nuke_style_compositing_suite import (
    PSN_Composite_Merge,
    PSN_Composite_Grading,
    PSN_Composite_Mask_Generator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert "PSN_Composite_Merge" in NODE_CLASS_MAPPINGS
    assert "PSN_Composite_Grading" in NODE_CLASS_MAPPINGS
    assert "PSN_Composite_Mask_Generator" in NODE_CLASS_MAPPINGS
    for k in NODE_CLASS_MAPPINGS:
        assert k in NODE_DISPLAY_NAME_MAPPINGS


def test_merge_50_percent():
    node = PSN_Composite_Merge()
    a = torch.full((1, 4, 4, 3), 0.0)
    b = torch.full((1, 4, 4, 3), 1.0)
    m = torch.full((1, 4, 4), 0.5)
    (out,) = node.run(a, b, m, "normal")
    assert out.shape == (1, 4, 4, 3)
    assert torch.allclose(out, torch.full_like(out, 0.5), atol=1e-6)


def test_merge_multiply_and_screen():
    node = PSN_Composite_Merge()
    a = torch.full((1, 2, 2, 3), 0.5)
    b = torch.full((1, 2, 2, 3), 0.5)
    m = torch.ones((1, 2, 2))
    (mul,) = node.run(a, b, m, "multiply")
    assert torch.allclose(mul, torch.full_like(mul, 0.25), atol=1e-6)
    (scr,) = node.run(a, b, m, "screen")
    assert torch.allclose(scr, torch.full_like(scr, 0.75), atol=1e-6)


def test_merge_bad_blend_mode():
    node = PSN_Composite_Merge()
    a = torch.zeros((1, 2, 2, 3))
    b = torch.zeros((1, 2, 2, 3))
    m = torch.zeros((1, 2, 2))
    try:
        node.run(a, b, m, "bogus_mode")
        raise AssertionError("expected ValueError for bad blend mode")
    except ValueError as e:
        assert "blend mode" in str(e).lower()


def test_merge_bad_input_shape():
    node = PSN_Composite_Merge()
    a = torch.zeros((1, 2, 2, 3))
    b = torch.zeros((1, 2, 2, 3))
    m = torch.zeros((1, 2, 2))
    try:
        node.run(a, b, m, "normal")
        # now pass a bad image
        node.run(torch.zeros((2, 2, 3)), b, m, "normal")
        raise AssertionError("expected ValueError for bad image shape")
    except ValueError:
        pass


def test_grading_identity():
    node = PSN_Composite_Grading()
    img = torch.rand((1, 3, 3, 3))
    (out,) = node.run(img, [0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
    assert torch.allclose(out, img, atol=1e-5)


def test_grading_gain_lift():
    node = PSN_Composite_Grading()
    img = torch.full((1, 2, 2, 3), 0.5)
    (out,) = node.run(img, [0.1, 0.0, 0.0], [1.0, 1.0, 1.0], [2.0, 1.0, 1.0])
    # R: 0.5*2 + 0.1 = 1.1 -> clamp 1.0 ; G,B: 0.5
    assert abs(out[0, 0, 0, 0].item() - 1.0) < 1e-5
    assert abs(out[0, 0, 0, 1].item() - 0.5) < 1e-5
    assert abs(out[0, 0, 0, 2].item() - 0.5) < 1e-5


def test_grading_bad_vec3():
    node = PSN_Composite_Grading()
    img = torch.rand((1, 2, 2, 3))
    try:
        node.run(img, [0.0, 0.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
        raise AssertionError("expected ValueError for 2-element lift")
    except ValueError:
        pass


def test_mask_generator_hard_threshold():
    node = PSN_Composite_Mask_Generator()
    # Luminance: 0.2126*R + 0.7152*G + 0.0722*B
    img = torch.zeros((1, 2, 2, 3))
    img[0, 0, 0] = torch.tensor([1.0, 0.0, 0.0])  # lum ~0.2126
    img[0, 0, 1] = torch.tensor([0.0, 1.0, 0.0])  # lum ~0.7152
    img[0, 1, 0] = torch.tensor([0.0, 0.0, 1.0])  # lum ~0.0722
    img[0, 1, 1] = torch.tensor([1.0, 1.0, 1.0])  # lum 1.0
    (mask,) = node.run(img, 0.5, 0.0)
    assert mask.shape == (1, 2, 2)
    assert mask[0, 0, 0].item() == 0.0
    assert mask[0, 0, 1].item() == 1.0
    assert mask[0, 1, 0].item() == 0.0
    assert mask[0, 1, 1].item() == 1.0


def test_mask_generator_feather():
    node = PSN_Composite_Mask_Generator()
    img = torch.full((1, 2, 2, 3), 0.5)  # lum 0.5
    (mask,) = node.run(img, 0.5, 0.2)
    # lum == threshold -> 0.5
    assert torch.allclose(mask, torch.full_like(mask, 0.5), atol=1e-5)


def test_mask_generator_bad_threshold():
    node = PSN_Composite_Mask_Generator()
    img = torch.rand((1, 2, 2, 3))
    try:
        node.run(img, 1.5, 0.1)
        raise AssertionError("expected ValueError for threshold > 1")
    except ValueError:
        pass


def test_no_inplace_mutation():
    node = PSN_Composite_Merge()
    a = torch.full((1, 2, 2, 3), 0.2)
    b = torch.full((1, 2, 2, 3), 0.8)
    m = torch.full((1, 2, 2), 0.5)
    a_copy = a.clone()
    b_copy = b.clone()
    m_copy = m.clone()
    node.run(a, b, m, "normal")
    assert torch.equal(a, a_copy)
    assert torch.equal(b, b_copy)
    assert torch.equal(m, m_copy)


def main():
    test_module_mappings()
    test_merge_50_percent()
    test_merge_multiply_and_screen()
    test_merge_bad_blend_mode()
    test_merge_bad_input_shape()
    test_grading_identity()
    test_grading_gain_lift()
    test_grading_bad_vec3()
    test_mask_generator_hard_threshold()
    test_mask_generator_feather()
    test_mask_generator_bad_threshold()
    test_no_inplace_mutation()
    print("ok")


if __name__ == "__main__":
    main()
