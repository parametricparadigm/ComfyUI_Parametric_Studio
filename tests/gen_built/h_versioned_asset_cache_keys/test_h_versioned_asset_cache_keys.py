"""Tests for h_versioned_asset_cache_keys."""

import h_versioned_asset_cache_keys as m


def test_basic_key_deterministic():
    k1 = m.build_cache_key("sd_xl", "a cat", "anime", seed=42, steps=20, cfg=7.0)
    k2 = m.build_cache_key("sd_xl", "a cat", "anime", seed=42, steps=20, cfg=7.0)
    assert k1 == k2, "same inputs must give same key"
    assert m.is_valid_key(k1), "key must match expected format"


def test_different_prompt_changes_key():
    k1 = m.build_cache_key("sd_xl", "a cat", "anime")
    k2 = m.build_cache_key("sd_xl", "a dog", "anime")
    assert k1 != k2, "different prompt must change key"


def test_whitespace_normalization():
    k1 = m.build_cache_key("sd_xl", "a   cat", "anime")
    k2 = m.build_cache_key("sd_xl", "a cat", "anime")
    assert k1 == k2, "whitespace-only differences must not change key"


def test_empty_model_raises():
    try:
        m.build_cache_key("", "a cat", "anime")
        assert False, "expected ValueError for empty model"
    except ValueError:
        pass


def test_bad_type_raises():
    try:
        m.build_cache_key(123, "a cat", "anime")
        assert False, "expected TypeError for non-str model"
    except TypeError:
        pass


def test_seed_changes_key():
    k1 = m.build_cache_key("sd_xl", "a cat", "anime", seed=1)
    k2 = m.build_cache_key("sd_xl", "a cat", "anime", seed=2)
    assert k1 != k2, "different seed must change key"


def test_compare_node_hit_and_miss():
    node = m.PSN_CacheKeyCompare()
    k = m.build_cache_key("sd_xl", "a cat", "anime")
    match, status = node.run(k, k)
    assert match is True and status == "hit"
    k2 = m.build_cache_key("sd_xl", "a dog", "anime")
    match2, status2 = node.run(k, k2)
    assert match2 is False and status2 == "miss"


def test_compare_invalid_key():
    node = m.PSN_CacheKeyCompare()
    match, status = node.run("not-a-key", "v1-" + "0" * 64)
    assert match is False and status == "invalid_key"


def test_node_run_returns_string():
    node = m.PSN_VersionedAssetCacheKey()
    (key,) = node.run("sd_xl", "a cat", "anime", seed=0, steps=20, cfg=7.0)
    assert isinstance(key, str)
    assert m.is_valid_key(key)


def test_algo_version_in_key():
    k = m.build_cache_key("m", "p", "s")
    assert k.startswith("v%d-" % m.ALGO_VERSION)


if __name__ == "__main__":
    test_basic_key_deterministic()
    test_different_prompt_changes_key()
    test_whitespace_normalization()
    test_empty_model_raises()
    test_bad_type_raises()
    test_seed_changes_key()
    test_compare_node_hit_and_miss()
    test_compare_invalid_key()
    test_node_run_returns_string()
    test_algo_version_in_key()
    print("ok")
