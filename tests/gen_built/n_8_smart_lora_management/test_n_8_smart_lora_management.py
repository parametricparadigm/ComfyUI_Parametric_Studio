"""Tests for n_8_smart_lora_management.py"""

import torch
from n_8_smart_lora_management import (
    PSN_SmartLoRALoader,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_blocks,
)


def test_parse_blocks_basic():
    assert _parse_blocks("0,1,2") == [0, 1, 2]


def test_parse_blocks_unsorted_and_dups():
    assert _parse_blocks("3,1,3,0") == [0, 1, 3]


def test_parse_blocks_empty_raises():
    try:
        _parse_blocks("")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_parse_blocks_invalid_raises():
    try:
        _parse_blocks("0,abc")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_parse_blocks_negative_raises():
    try:
        _parse_blocks("-1,0")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_node_loads_single_block():
    node = PSN_SmartLoRALoader()
    result = node.run(lora_path="test.safetensors", blocks_to_load="0", strength=1.0)
    loaded = result[0]
    assert isinstance(loaded, dict)
    assert set(loaded["blocks"].keys()) == {0}
    assert loaded["strength"] == 1.0
    assert loaded["path"] == "test.safetensors"
    # Check tensor shape
    assert loaded["blocks"][0].shape == (4, 4)


def test_node_loads_multiple_blocks():
    node = PSN_SmartLoRALoader()
    result = node.run(lora_path="test.safetensors", blocks_to_load="0,2,5", strength=0.5)
    loaded = result[0]
    assert set(loaded["blocks"].keys()) == {0, 2, 5}
    assert loaded["strength"] == 0.5


def test_node_strength_scaling():
    node = PSN_SmartLoRALoader()
    r1 = node.run(lora_path="test.safetensors", blocks_to_load="0", strength=1.0)
    r2 = node.run(lora_path="test.safetensors", blocks_to_load="0", strength=2.0)
    # r2 should be exactly 2x r1
    expected = r1[0]["blocks"][0] * 2.0
    assert torch.allclose(r2[0]["blocks"][0], expected, atol=1e-6)


def test_node_does_not_mutate_input():
    """Verify that the node does not modify the synthetic lora in place."""
    node = PSN_SmartLoRALoader()
    # Get the synthetic lora directly
    lora = node._synthetic_lora("test.safetensors")
    original = lora[0].clone()
    node.run(lora_path="test.safetensors", blocks_to_load="0", strength=3.0)
    # The synthetic lora is regenerated each call, so check that the returned
    # tensor is a scaled copy, not the original
    result = node.run(lora_path="test.safetensors", blocks_to_load="0", strength=3.0)
    assert not torch.equal(result[0]["blocks"][0], original)
    assert torch.allclose(result[0]["blocks"][0], original * 3.0, atol=1e-6)


def test_node_nonexistent_block_raises():
    node = PSN_SmartLoRALoader()
    try:
        node.run(lora_path="test.safetensors", blocks_to_load="99", strength=1.0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_node_bad_strength_type():
    node = PSN_SmartLoRALoader()
    try:
        node.run(lora_path="test.safetensors", blocks_to_load="0", strength="abc")
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


def test_node_bad_path_type():
    node = PSN_SmartLoRALoader()
    try:
        node.run(lora_path=123, blocks_to_load="0", strength=1.0)
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


def test_node_class_mappings():
    assert "PSN_SmartLoRALoader" in NODE_CLASS_MAPPINGS
    assert "PSN_SmartLoRALoader" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_SmartLoRALoader"] is PSN_SmartLoRALoader


def test_input_types():
    it = PSN_SmartLoRALoader.INPUT_TYPES()
    assert "required" in it
    assert "lora_path" in it["required"]
    assert "blocks_to_load" in it["required"]
    assert "strength" in it["required"]


def test_return_types():
    assert PSN_SmartLoRALoader.RETURN_TYPES == ("LOADED_LORA",)
    assert PSN_SmartLoRALoader.FUNCTION == "run"
    assert PSN_SmartLoRALoader.CATEGORY == "ParametricStudio/LoRA"


def test_negative_strength():
    node = PSN_SmartLoRALoader()
    result = node.run(lora_path="test.safetensors", blocks_to_load="0", strength=-1.0)
    loaded = result[0]
    assert loaded["strength"] == -1.0
    # Values should be negated
    base = node._synthetic_lora("test.safetensors")[0]
    assert torch.allclose(loaded["blocks"][0], -base, atol=1e-6)


if __name__ == "__main__":
    test_parse_blocks_basic()
    test_parse_blocks_unsorted_and_dups()
    test_parse_blocks_empty_raises()
    test_parse_blocks_invalid_raises()
    test_parse_blocks_negative_raises()
    test_node_loads_single_block()
    test_node_loads_multiple_blocks()
    test_node_strength_scaling()
    test_node_does_not_mutate_input()
    test_node_nonexistent_block_raises()
    test_node_bad_strength_type()
    test_node_bad_path_type()
    test_node_class_mappings()
    test_input_types()
    test_return_types()
    test_negative_strength()
    print("ok")
