import pytest

from psn_nodes.gen.n_2_parametric_seed_generation import (
    PSN_Seed_Generator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    MODES,
    MAX_SEED,
)


def test_deterministic_mode_is_reproducible():
    node = PSN_Seed_Generator()
    s1, h1 = node.run(100, 1.5, 2.5, "Deterministic")
    s2, h2 = node.run(100, 1.5, 2.5, "Deterministic")
    assert s1 == s2
    assert h1 == h2
    # 100 + int(1.5*1000) + int(2.5*1000) = 100 + 1500 + 2500 = 4100
    assert s1 == 4100
    assert h1 == format(4100, "016x")


def test_hashed_mode_is_reproducible_and_salt_sensitive():
    node = PSN_Seed_Generator()
    s1, _ = node.run(7, 0.1, 0.2, "Hashed", salt="abc")
    s2, _ = node.run(7, 0.1, 0.2, "Hashed", salt="abc")
    s3, _ = node.run(7, 0.1, 0.2, "Hashed", salt="xyz")
    assert s1 == s2
    assert s1 != s3


def test_pseudo_random_differs_for_different_param_a():
    node = PSN_Seed_Generator()
    s1, _ = node.run(42, 1.0, 0.0, "Pseudo-Random")
    s2, _ = node.run(42, 2.0, 0.0, "Pseudo-Random")
    assert s1 != s2


def test_pseudo_random_reproducible_for_same_inputs():
    node = PSN_Seed_Generator()
    s1, _ = node.run(42, 1.0, 0.5, "Pseudo-Random")
    s2, _ = node.run(42, 1.0, 0.5, "Pseudo-Random")
    assert s1 == s2


def test_seed_hex_format_and_range():
    node = PSN_Seed_Generator()
    for mode in MODES:
        seed, hex_str = node.run(12345, 3.14, 2.71, mode, salt="s")
        assert isinstance(seed, int)
        assert 0 <= seed <= MAX_SEED
        assert len(hex_str) == 16
        assert int(hex_str, 16) == seed


def test_bad_inputs_are_coerced_safely():
    node = PSN_Seed_Generator()
    # Non-numeric base_seed and params should not raise
    seed, hex_str = node.run("not-an-int", "bad", "bad", "Deterministic")
    assert isinstance(seed, int)
    assert 0 <= seed <= MAX_SEED
    assert len(hex_str) == 16
    # Unknown mode falls back to hashed without raising
    seed2, _ = node.run(1, 1.0, 1.0, "BogusMode", salt="x")
    assert isinstance(seed2, int)


def test_node_mappings_and_input_schema():
    assert "PSN_Seed_Generator" in NODE_CLASS_MAPPINGS
    assert "PSN_Seed_Generator" in NODE_DISPLAY_NAME_MAPPINGS
    schema = PSN_Seed_Generator.INPUT_TYPES()
    assert "base_seed" in schema["required"]
    assert "mode" in schema["required"]
    assert "salt" in schema["optional"]
    assert MODES == ["Deterministic", "Pseudo-Random", "Hashed"]
