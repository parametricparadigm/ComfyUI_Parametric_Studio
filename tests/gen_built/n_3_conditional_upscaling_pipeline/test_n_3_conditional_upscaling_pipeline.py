import torch
from n_3_conditional_upscaling_pipeline import (
    PSN_Quality_Gate,
    PSN_Upscale_Switch,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _img(b=1, h=4, w=4, c=3):
    return torch.rand(b, h, w, c)


def test_gate_below_threshold():
    g = PSN_Quality_Gate()
    img = _img()
    needs, out = g.run(img, quality_score=0.3, threshold=0.5)
    assert needs is True, "score 0.3 < 0.5 should give needs_upscale=True"
    assert out.shape == img.shape


def test_gate_above_threshold():
    g = PSN_Quality_Gate()
    img = _img()
    needs, out = g.run(img, quality_score=0.8, threshold=0.5)
    assert needs is False, "score 0.8 >= 0.5 should give needs_upscale=False"


def test_gate_equal_threshold():
    g = PSN_Quality_Gate()
    img = _img()
    needs, _ = g.run(img, quality_score=0.5, threshold=0.5)
    assert needs is False, "score == threshold should give needs_upscale=False"


def test_switch_flag_false_passthrough():
    s = PSN_Upscale_Switch()
    img = _img()
    out = s.run(img, flag=False, upscaler_model=None)[0]
    assert out.shape == img.shape, "flag=False should pass through unchanged"
    assert torch.allclose(out, img), "flag=False output should equal input"


def test_switch_flag_true_upscales():
    s = PSN_Upscale_Switch()
    img = _img(b=1, h=4, w=4, c=3)
    out = s.run(img, flag=True, upscaler_model=None)[0]
    assert out.shape == (1, 8, 8, 3), "flag=True should 2x upscale: (1,4,4,3)->(1,8,8,3)"
    assert out.min() >= 0.0 and out.max() <= 1.0, "output must stay in [0,1]"


def test_switch_batch():
    s = PSN_Upscale_Switch()
    img = _img(b=2, h=3, w=5, c=3)
    out = s.run(img, flag=True, upscaler_model=None)[0]
    assert out.shape == (2, 6, 10, 3), "batch of 2 should upscale each frame"


def test_bad_input_non_tensor():
    g = PSN_Quality_Gate()
    try:
        g.run("not a tensor", quality_score=0.3, threshold=0.5)
        assert False, "should have raised TypeError"
    except TypeError:
        pass


def test_node_mappings():
    assert "PSN_Quality_Gate" in NODE_CLASS_MAPPINGS
    assert "PSN_Upscale_Switch" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Quality_Gate"] == "Quality Gate"
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Upscale_Switch"] == "Upscale Switch"


def test_input_types():
    it = PSN_Quality_Gate.INPUT_TYPES()
    assert "image" in it["required"]
    assert "quality_score" in it["required"]
    assert "threshold" in it["required"]
    it2 = PSN_Upscale_Switch.INPUT_TYPES()
    assert "image" in it2["required"]
    assert "flag" in it2["required"]
    assert "upscaler_model" in it2["required"]


if __name__ == "__main__":
    test_gate_below_threshold()
    test_gate_above_threshold()
    test_gate_equal_threshold()
    test_switch_flag_false_passthrough()
    test_switch_flag_true_upscales()
    test_switch_batch()
    test_bad_input_non_tensor()
    test_node_mappings()
    test_input_types()
    print("ok")
