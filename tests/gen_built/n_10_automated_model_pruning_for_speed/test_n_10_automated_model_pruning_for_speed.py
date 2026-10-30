import os
import tempfile

import torch

from n_10_automated_model_pruning_for_speed import (
    PSN_ModelPruner,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_keys,
    _load_safetensors,
    _save_safetensors,
    _file_size,
)


def _make_fixture(path, tensors):
    """Write a small safetensors fixture file."""
    from safetensors.torch import save_file
    save_file(tensors, path)


def test_parse_keys_basic():
    s = _parse_keys("a, b ,c")
    assert s == {"a", "b", "c"}, f"expected {{'a','b','c'}}, got {s}"


def test_parse_keys_empty():
    s = _parse_keys("")
    assert s == set(), f"expected empty set, got {s}"


def test_parse_keys_bad_type():
    try:
        _parse_keys(123)
        assert False, "should have raised TypeError"
    except TypeError:
        pass


def test_prune_reduces_size():
    """Prune a key from a fixture model; assert key is missing and size reduced."""
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src.safetensors")
        dst = os.path.join(d, "dst.safetensors")
        tensors = {
            "keep": torch.randn(4, 4),
            "prune_me": torch.randn(64, 64),
        }
        _make_fixture(src, tensors)

        node = PSN_ModelPruner()
        out_path, reduction = node.run(src, "prune_me", dst)

        assert out_path == dst, f"expected {dst}, got {out_path}"
        assert reduction > 0, f"expected positive reduction, got {reduction}"

        # Verify pruned key is missing
        loaded, _ = _load_safetensors(dst)
        assert "prune_me" not in loaded, "prune_me should be missing"
        assert "keep" in loaded, "keep should still be present"
        assert torch.allclose(loaded["keep"], tensors["keep"]), "keep tensor should be unchanged"


def test_prune_no_keys():
    """Prune with empty key list: file should be identical in content."""
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src.safetensors")
        dst = os.path.join(d, "dst.safetensors")
        tensors = {"a": torch.randn(2, 2)}
        _make_fixture(src, tensors)

        node = PSN_ModelPruner()
        out_path, reduction = node.run(src, "", dst)

        assert out_path == dst
        assert abs(reduction) < 1.0, f"reduction should be ~0, got {reduction}"
        loaded, _ = _load_safetensors(dst)
        assert "a" in loaded


def test_prune_bad_model_path():
    """Bad model path should raise ValueError."""
    node = PSN_ModelPruner()
    try:
        node.run("", "key", "/tmp/out.safetensors")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_prune_bad_output_path():
    """Bad output path should raise ValueError."""
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src.safetensors")
        tensors = {"a": torch.randn(2, 2)}
        _make_fixture(src, tensors)

        node = PSN_ModelPruner()
        try:
            node.run(src, "a", "")
            assert False, "should have raised ValueError"
        except ValueError:
            pass


def test_node_mappings():
    """Verify module-level mappings are correct."""
    assert "PSN_ModelPruner" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_ModelPruner"] is PSN_ModelPruner
    assert "PSN_ModelPruner" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ModelPruner"] == "Model Pruner (Speed)"


def test_input_types():
    """Verify INPUT_TYPES has the expected fields."""
    it = PSN_ModelPruner.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "model_path" in req
    assert "keys_to_prune" in req
    assert "output_path" in req


def test_return_types():
    """Verify RETURN_TYPES and RETURN_NAMES."""
    assert PSN_ModelPruner.RETURN_TYPES == ("STRING", "FLOAT")
    assert PSN_ModelPruner.RETURN_NAMES == ("PRUNED_MODEL_PATH", "SIZE_REDUCTION")
    assert PSN_ModelPruner.FUNCTION == "run"
    assert PSN_ModelPruner.CATEGORY == "ParametricStudio/Model"


if __name__ == "__main__":
    test_parse_keys_basic()
    test_parse_keys_empty()
    test_parse_keys_bad_type()
    test_prune_reduces_size()
    test_prune_no_keys()
    test_prune_bad_model_path()
    test_prune_bad_output_path()
    test_node_mappings()
    test_input_types()
    test_return_types()
    print("ok")
