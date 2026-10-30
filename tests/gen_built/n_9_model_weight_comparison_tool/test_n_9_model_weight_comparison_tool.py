"""Tests for PSN_WeightComparator."""
import torch
import torch.nn as nn

from n_9_model_weight_comparison_tool import (
    PSN_WeightComparator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _state_dict,
    _block_key,
    _l2_sq,
)


def _make_linear(seed, in_f=4, out_f=4):
    g = torch.Generator().manual_seed(seed)
    m = nn.Linear(in_f, out_f, bias=False)
    with torch.no_grad():
        m.weight.copy_(torch.randn(out_f, in_f, generator=g))
    return m


class _FakeComfyModel:
    """Mimics a ComfyUI MODEL wrapper with a .model attribute."""
    def __init__(self, module):
        self.model = module


def test_identical_models_zero_distance():
    """Two identical models should have L2 distance 0."""
    m = _make_linear(42)
    node = PSN_WeightComparator()
    dist, blocks = node.run(_FakeComfyModel(m), _FakeComfyModel(m), block_level=False)
    assert abs(dist) < 1e-6, "Expected 0 distance for identical models, got %f" % dist
    assert blocks == {"__overall__": 0.0}, "Expected single overall block, got %r" % blocks


def test_different_models_positive_distance():
    """Two different models should have L2 distance > 0."""
    ma = _make_linear(1)
    mb = _make_linear(2)
    node = PSN_WeightComparator()
    dist, blocks = node.run(_FakeComfyModel(ma), _FakeComfyModel(mb), block_level=False)
    assert dist > 0.0, "Expected positive distance, got %f" % dist
    assert "__overall__" in blocks
    assert abs(blocks["__overall__"] - dist) < 1e-6


def test_block_level_aggregation():
    """block_level=True should aggregate by block prefix."""
    class TinyNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.blocks = nn.ModuleList([nn.Linear(4, 4, bias=False) for _ in range(2)])
        def forward(self, x):
            for b in self.blocks:
                x = b(x)
            return x

    g1 = torch.Generator().manual_seed(10)
    g2 = torch.Generator().manual_seed(20)
    net_a = TinyNet()
    net_b = TinyNet()
    with torch.no_grad():
        for i in range(2):
            net_a.blocks[i].weight.copy_(torch.randn(4, 4, generator=g1))
            net_b.blocks[i].weight.copy_(torch.randn(4, 4, generator=g2))

    node = PSN_WeightComparator()
    dist, blocks = node.run(_FakeComfyModel(net_a), _FakeComfyModel(net_b), block_level=True)
    assert "blocks.0" in blocks, "Expected blocks.0 in %r" % blocks
    assert "blocks.1" in blocks, "Expected blocks.1 in %r" % blocks
    expected_overall = (blocks["blocks.0"] ** 2 + blocks["blocks.1"] ** 2) ** 0.5
    assert abs(dist - expected_overall) < 1e-5, \
        "Overall %f != expected %f" % (dist, expected_overall)


def test_dict_input():
    """Plain dict state dicts should work."""
    sd_a = {"w": torch.ones(3, 3)}
    sd_b = {"w": torch.ones(3, 3) * 2.0}
    node = PSN_WeightComparator()
    dist, blocks = node.run(sd_a, sd_b, block_level=False)
    assert abs(dist - 3.0) < 1e-5, "Expected 3.0, got %f" % dist


def test_no_common_keys_raises():
    """Models with no overlapping keys should raise ValueError."""
    sd_a = {"a": torch.ones(2)}
    sd_b = {"b": torch.ones(2)}
    node = PSN_WeightComparator()
    try:
        node.run(sd_a, sd_b, block_level=False)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_shape_mismatch_skipped():
    """Parameters with different shapes are skipped, not compared."""
    sd_a = {"w": torch.ones(3, 3), "v": torch.ones(2)}
    sd_b = {"w": torch.ones(3, 3) * 2.0, "v": torch.ones(4)}
    node = PSN_WeightComparator()
    dist, blocks = node.run(sd_a, sd_b, block_level=False)
    assert abs(dist - 3.0) < 1e-5, "Expected 3.0 (only w compared), got %f" % dist


def test_node_mappings():
    """Module-level mappings must be present and consistent."""
    assert "PSN_WeightComparator" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_WeightComparator"] is PSN_WeightComparator
    assert "PSN_WeightComparator" in NODE_DISPLAY_NAME_MAPPINGS
    assert PSN_WeightComparator.FUNCTION == "run"
    assert PSN_WeightComparator.CATEGORY == "ParametricStudio/Model"
    assert PSN_WeightComparator.RETURN_TYPES == ("FLOAT", "CUSTOM")
    assert PSN_WeightComparator.RETURN_NAMES == ("L2_DISTANCE", "BLOCK_DISTANCES")


def test_input_types():
    """INPUT_TYPES must declare the expected fields."""
    it = PSN_WeightComparator.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "model_a" in req
    assert "model_b" in req
    assert "block_level" in req
    assert req["model_a"] == ("MODEL",)
    assert req["model_b"] == ("MODEL",)
    assert req["block_level"][0] == "BOOLEAN"


def test_block_key_fallback():
    """_block_key should fall back to first segment for non-block names."""
    assert _block_key("conv.weight", True) == "conv"
    assert _block_key("blocks.3.attn.q.weight", True) == "blocks.3"
    assert _block_key("anything", False) == "__overall__"


def test_l2_sq_basic():
    """_l2_sq should return the squared L2 distance."""
    a = torch.tensor([1.0, 2.0, 3.0])
    b = torch.tensor([4.0, 6.0, 3.0])
    assert abs(_l2_sq(a, b) - 25.0) < 1e-6


def test_does_not_modify_inputs():
    """The node must not modify input tensors in place."""
    w_a = torch.ones(3, 3)
    w_b = torch.ones(3, 3) * 2.0
    snapshot_a = w_a.clone()
    snapshot_b = w_b.clone()
    node = PSN_WeightComparator()
    node.run({"w": w_a}, {"w": w_b}, block_level=False)
    assert torch.equal(w_a, snapshot_a), "model_a was modified in place"
    assert torch.equal(w_b, snapshot_b), "model_b was modified in place"


if __name__ == "__main__":
    test_identical_models_zero_distance()
    test_different_models_positive_distance()
    test_block_level_aggregation()
    test_dict_input()
    test_no_common_keys_raises()
    test_shape_mismatch_skipped()
    test_node_mappings()
    test_input_types()
    test_block_key_fallback()
    test_l2_sq_basic()
    test_does_not_modify_inputs()
    print("ok")
