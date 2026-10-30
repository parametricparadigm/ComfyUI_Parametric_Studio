import torch

from n_5_nuke_style_compositing_for_layers import (
    PSN_Nuke_Composite,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    BLEND_MODES,
)


def _img(v, b=1, h=2, w=2, c=3):
    return torch.full((b, h, w, c), float(v))


def _mask(v, b=1, h=2, w=2):
    return torch.full((b, h, w), float(v))


def test_module_mappings():
    assert "PSN_Nuke_Composite" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Nuke_Composite"] is PSN_Nuke_Composite
    assert "PSN_Nuke_Composite" in NODE_DISPLAY_NAME_MAPPINGS
    assert PSN_Nuke_Composite.FUNCTION == "run"
    assert PSN_Nuke_Composite.RETURN_TYPES == ("IMAGE",)
    assert PSN_Nuke_Composite.RETURN_NAMES == ("composite_image",)
    assert PSN_Nuke_Composite.CATEGORY.startswith("ParametricStudio/")
    it = PSN_Nuke_Composite.INPUT_TYPES()
    assert "base_image" in it["required"]
    assert "overlay_image" in it["required"]
    assert "mask" in it["required"]
    assert "blend_mode" in it["required"]
    assert "opacity" in it["required"]
    assert set(BLEND_MODES) == {"Normal", "Screen", "Multiply", "Overlay"}


def test_screen_white_over_black():
    node = PSN_Nuke_Composite()
    base = _img(0.0)  # black
    top = _img(1.0)  # white
    m = _mask(1.0)
    out = node.run(base, top, m, "Screen", 1.0)[0]
    assert out.shape == (1, 2, 2, 3)
    assert torch.allclose(out, torch.ones_like(out), atol=1e-6)


def test_multiply_white_over_black():
    node = PSN_Nuke_Composite()
    base = _img(0.0)
    top = _img(1.0)
    m = _mask(1.0)
    out = node.run(base, top, m, "Multiply", 1.0)[0]
    assert torch.allclose(out, torch.zeros_like(out), atol=1e-6)


def test_mask_zero_keeps_base():
    node = PSN_Nuke_Composite()
    base = _img(0.25)
    top = _img(1.0)
    m = _mask(0.0)
    out = node.run(base, top, m, "Screen", 1.0)[0]
    # Screen with masked-out overlay (0) leaves base unchanged
    assert torch.allclose(out, base, atol=1e-6)


def test_opacity_zero_keeps_base():
    node = PSN_Nuke_Composite()
    base = _img(0.3)
    top = _img(1.0)
    m = _mask(1.0)
    out = node.run(base, top, m, "Normal", 0.0)[0]
    assert torch.allclose(out, base, atol=1e-6)


def test_overlay_midpoint():
    node = PSN_Nuke_Composite()
    base = _img(0.5)
    top = _img(0.5)
    m = _mask(1.0)
    out = node.run(base, top, m, "Overlay", 1.0)[0]
    # Overlay at base=0.5: condition base<0.5 is False -> 1 - 2*(0.5)*(0.5) = 0.5
    assert torch.allclose(out, _img(0.5), atol=1e-6)


def test_no_inplace_mutation():
    node = PSN_Nuke_Composite()
    base = _img(0.2)
    top = _img(0.8)
    m = _mask(1.0)
    base_before = base.clone()
    top_before = top.clone()
    m_before = m.clone()
    node.run(base, top, m, "Screen", 0.5)
    assert torch.equal(base, base_before)
    assert torch.equal(top, top_before)
    assert torch.equal(m, m_before)


def test_bad_inputs():
    node = PSN_Nuke_Composite()
    base = _img(0.5)
    top = _img(0.5)
    m = _mask(1.0)

    # shape mismatch
    try:
        node.run(base, _img(0.5, h=3), m, "Normal", 1.0)
        raise AssertionError("expected ValueError for shape mismatch")
    except ValueError:
        pass

    # mask batch mismatch
    try:
        node.run(base, top, _mask(1.0, b=2), "Normal", 1.0)
        raise AssertionError("expected ValueError for mask batch mismatch")
    except ValueError:
        pass

    # mask spatial mismatch
    try:
        node.run(base, top, _mask(1.0, w=3), "Normal", 1.0)
        raise AssertionError("expected ValueError for mask spatial mismatch")
    except ValueError:
        pass

    # bad blend mode
    try:
        node.run(base, top, m, "Dodge", 1.0)
        raise AssertionError("expected ValueError for bad blend mode")
    except ValueError:
        pass

    # bad opacity
    try:
        node.run(base, top, m, "Normal", 1.5)
        raise AssertionError("expected ValueError for bad opacity")
    except ValueError:
        pass

    # non-tensor input
    try:
        node.run("not a tensor", top, m, "Normal", 1.0)
        raise AssertionError("expected TypeError for non-tensor")
    except TypeError:
        pass

    # wrong-dim image
    try:
        node.run(torch.zeros(2, 2, 3), top, m, "Normal", 1.0)
        raise AssertionError("expected ValueError for wrong-dim image")
    except ValueError:
        pass


def test_batch_and_channels():
    node = PSN_Nuke_Composite()
    base = torch.rand(2, 3, 4, 4)
    top = torch.rand(2, 3, 4, 4)
    m = torch.rand(2, 3, 4)
    out = node.run(base, top, m, "Screen", 0.7)[0]
    assert out.shape == (2, 3, 4, 4)
    assert out.min() >= 0.0 and out.max() <= 1.0


def main():
    test_module_mappings()
    test_screen_white_over_black()
    test_multiply_white_over_black()
    test_mask_zero_keeps_base()
    test_opacity_zero_keeps_base()
    test_overlay_midpoint()
    test_no_inplace_mutation()
    test_bad_inputs()
    test_batch_and_channels()
    print("ok")


if __name__ == "__main__":
    main()
