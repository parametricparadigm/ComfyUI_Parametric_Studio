import torch

from n_5_photoshop_style_compositing_layers import (
    PSN_LayerComposite,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    BLEND_MODES,
)


def _img(v, b=1, h=2, w=2, c=3):
    return torch.full((b, h, w, c), float(v))


def test_module_mappings():
    assert "PSN_LayerComposite" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_LayerComposite"] is PSN_LayerComposite
    assert "PSN_LayerComposite" in NODE_DISPLAY_NAME_MAPPINGS
    it = PSN_LayerComposite.INPUT_TYPES()
    assert "required" in it and "optional" in it
    assert "base_image" in it["required"]
    assert "top_image" in it["required"]
    assert "blend_mode" in it["required"]
    assert "opacity" in it["required"]
    assert "mask" in it["optional"]
    assert PSN_LayerComposite.RETURN_TYPES == ("IMAGE",)
    assert PSN_LayerComposite.FUNCTION == "run"
    assert PSN_LayerComposite.CATEGORY.startswith("ParametricStudio/")


def test_multiply_white_over_black_is_black():
    node = PSN_LayerComposite()
    base = _img(0.0)  # black
    top = _img(1.0)   # white
    out, = node.run(base, top, "Multiply", 1.0)
    assert out.shape == base.shape
    assert torch.allclose(out, torch.zeros_like(out), atol=1e-6)


def test_screen_black_over_white_is_white():
    node = PSN_LayerComposite()
    base = _img(1.0)  # white
    top = _img(0.0)   # black
    out, = node.run(base, top, "Screen", 1.0)
    assert torch.allclose(out, torch.ones_like(out), atol=1e-6)


def test_normal_full_opacity_replaces_base():
    node = PSN_LayerComposite()
    base = _img(0.2)
    top = _img(0.8)
    out, = node.run(base, top, "Normal", 1.0)
    assert torch.allclose(out, top, atol=1e-6)


def test_opacity_zero_keeps_base():
    node = PSN_LayerComposite()
    base = _img(0.3)
    top = _img(0.9)
    out, = node.run(base, top, "Normal", 0.0)
    assert torch.allclose(out, base, atol=1e-6)


def test_mask_full_and_zero():
    node = PSN_LayerComposite()
    base = _img(0.0)
    top = _img(1.0)
    # full mask -> top shows
    m_full = torch.ones(1, 2, 2)
    out_full, = node.run(base, top, "Normal", 1.0, mask=m_full)
    assert torch.allclose(out_full, top, atol=1e-6)
    # zero mask -> base shows
    m_zero = torch.zeros(1, 2, 2)
    out_zero, = node.run(base, top, "Normal", 1.0, mask=m_zero)
    assert torch.allclose(out_zero, base, atol=1e-6)


def test_overlay_midpoint():
    node = PSN_LayerComposite()
    # base = 0.5, top = 0.5 -> overlay(0.5,0.5): base<0.5? no (equal) -> 1 - 2*0.5*0.5 = 0.5
    base = _img(0.5)
    top = _img(0.5)
    out, = node.run(base, top, "Overlay", 1.0)
    assert torch.allclose(out, _img(0.5), atol=1e-6)


def test_hard_light_low_top():
    node = PSN_LayerComposite()
    base = _img(0.5)
    top = _img(0.25)  # < 0.5 -> 2*b*t = 2*0.5*0.25 = 0.25
    out, = node.run(base, top, "Hard_Light", 1.0)
    assert torch.allclose(out, _img(0.25), atol=1e-6)


def test_soft_light_midpoint():
    node = PSN_LayerComposite()
    base = _img(0.5)
    top = _img(0.5)
    out, = node.run(base, top, "Soft_Light", 1.0)
    # t=0.5 -> high branch: b + 0*(b2-b) = b = 0.5
    assert torch.allclose(out, _img(0.5), atol=1e-6)


def test_bad_blend_mode_raises():
    node = PSN_LayerComposite()
    try:
        node.run(_img(0.0), _img(1.0), "Bogus", 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad blend mode")


def test_shape_mismatch_raises():
    node = PSN_LayerComposite()
    base = _img(0.0, h=2, w=2)
    top = _img(1.0, h=3, w=3)
    try:
        node.run(base, top, "Normal", 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for shape mismatch")


def test_bad_opacity_raises():
    node = PSN_LayerComposite()
    try:
        node.run(_img(0.0), _img(1.0), "Normal", 1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for opacity > 1")


def test_mask_shape_mismatch_raises():
    node = PSN_LayerComposite()
    base = _img(0.0, h=2, w=2)
    top = _img(1.0, h=2, w=2)
    bad_mask = torch.ones(1, 4, 4)
    try:
        node.run(base, top, "Normal", 1.0, mask=bad_mask)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad mask shape")


def test_no_inplace_modification():
    node = PSN_LayerComposite()
    base = _img(0.3)
    top = _img(0.7)
    base_before = base.clone()
    top_before = top.clone()
    node.run(base, top, "Multiply", 1.0)
    assert torch.equal(base, base_before)
    assert torch.equal(top, top_before)


def test_output_clamped():
    node = PSN_LayerComposite()
    # values outside [0,1] should be clamped
    base = torch.full((1, 2, 2, 3), 1.5)
    top = torch.full((1, 2, 2, 3), -0.5)
    out, = node.run(base, top, "Normal", 1.0)
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_all_blend_modes_run():
    node = PSN_LayerComposite()
    base = torch.rand(1, 4, 4, 3)
    top = torch.rand(1, 4, 4, 3)
    for mode in BLEND_MODES:
        out, = node.run(base, top, mode, 0.7)
        assert out.shape == base.shape
        assert out.min() >= 0.0 and out.max() <= 1.0


def main():
    test_module_mappings()
    test_multiply_white_over_black_is_black()
    test_screen_black_over_white_is_white()
    test_normal_full_opacity_replaces_base()
    test_opacity_zero_keeps_base()
    test_mask_full_and_zero()
    test_overlay_midpoint()
    test_hard_light_low_top()
    test_soft_light_midpoint()
    test_bad_blend_mode_raises()
    test_shape_mismatch_raises()
    test_bad_opacity_raises()
    test_mask_shape_mismatch_raises()
    test_no_inplace_modification()
    test_output_clamped()
    test_all_blend_modes_run()
    print("ok")


if __name__ == "__main__":
    main()
