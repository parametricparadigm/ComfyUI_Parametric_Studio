"""Tests for n_10_in_memory_media_management_for_fast_i."""

import torch

import n_10_in_memory_media_management_for_fast_i as mod


def _img(b=1, h=4, w=4, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(b, h, w, c, generator=g)


def test_basic_miss_then_hit():
    node = mod.PSN_Memory_Media_Manager()
    img = _img(seed=1)
    out1, hit1 = node.run(img, "a.png", 8, "")
    assert hit1 is False, "first access must be a miss"
    assert out1.shape == img.shape
    assert torch.allclose(out1, img)

    out2, hit2 = node.run(img, "a.png", 8, "")
    assert hit2 is True, "second access must be a hit"
    assert torch.allclose(out2, img)


def test_cache_key_override():
    node = mod.PSN_Memory_Media_Manager()
    img = _img(seed=2)
    # Use explicit cache_key; different path but same key -> hit.
    _, h1 = node.run(img, "path1.png", 8, "mykey")
    assert h1 is False
    _, h2 = node.run(img, "path2.png", 8, "mykey")
    assert h2 is True


def test_lru_eviction():
    node = mod.PSN_Memory_Media_Manager()
    # capacity 2
    for i in range(3):
        node.run(_img(seed=10 + i), f"k{i}.png", 2, "")
    # After inserting k0, k1, k2 with capacity 2: k0 evicted, k1 & k2 remain.
    # Access k1 (hit) -> order becomes [k2, k1].
    _, h1 = node.run(_img(seed=11), "k1.png", 2, "")
    assert h1 is True, "k1 must still be cached"
    # Now insert k3 -> evicts LRU which is k2.
    node.run(_img(seed=13), "k3.png", 2, "")
    _, h2 = node.run(_img(seed=12), "k2.png", 2, "")
    assert h2 is False, "k2 must have been evicted (LRU)"
    _, h3 = node.run(_img(seed=13), "k3.png", 2, "")
    assert h3 is True, "k3 must still be cached"


def test_no_in_place_mutation():
    node = mod.PSN_Memory_Media_Manager()
    img = _img(seed=3)
    snapshot = img.clone()
    out, _ = node.run(img, "mut.png", 8, "")
    # Mutate the output; input must be unchanged.
    out.add_(1.0)
    assert torch.allclose(img, snapshot), "input must not be mutated"


def test_bad_input_empty_key():
    node = mod.PSN_Memory_Media_Manager()
    img = _img(seed=4)
    try:
        node.run(img, "", 8, "")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty key")


def test_clear_node():
    node = mod.PSN_Memory_Media_Manager()
    img = _img(seed=5)
    node.run(img, "clearme.png", 8, "")
    clear = mod.PSN_Memory_Media_Clear()
    (cleared,) = clear.run()
    assert cleared is True
    _, hit = node.run(img, "clearme.png", 8, "")
    assert hit is False, "cache must be empty after clear"


def test_module_mappings():
    assert "PSN_Memory_Media_Manager" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_Memory_Media_Clear" in mod.NODE_CLASS_MAPPINGS
    assert mod.PSN_Memory_Media_Manager.FUNCTION == "run"
    assert mod.PSN_Memory_Media_Manager.CATEGORY == "ParametricStudio/Media"
    it = mod.PSN_Memory_Media_Manager.INPUT_TYPES()
    assert "media" in it["required"]
    assert "media_path" in it["required"]
    assert "max_cache_size" in it["required"]
    assert "cache_key" in it["optional"]


if __name__ == "__main__":
    test_basic_miss_then_hit()
    test_cache_key_override()
    test_lru_eviction()
    test_no_in_place_mutation()
    test_bad_input_empty_key()
    test_clear_node()
    test_module_mappings()
    print("ok")
