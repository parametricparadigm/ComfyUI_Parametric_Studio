"""Tests for psn_nodes.gen.psn_seed_lab (pure-logic seed lab)."""

import pytest

from psn_nodes.gen.psn_seed_lab import (
    MODES,
    PSN_Seed_Manipulator,
    PSN_Seed_Visualizer,
    psn_derive_seed,
    psn_noise_descriptor,
    psn_noise_to_grid,
    psn_fnv1a64,
    psn_lcg_step,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_same_seed_same_mode_is_identical():
    """Unit: same base seed + mode + offset must yield an identical descriptor."""
    s1 = psn_derive_seed(12345, "ancestral", 0)
    s2 = psn_derive_seed(12345, "ancestral", 0)
    assert s1 == s2
    d1 = psn_noise_descriptor(s1, "ancestral", (4, 4))
    d2 = psn_noise_descriptor(s2, "ancestral", (4, 4))
    assert d1 == d2
    assert d1["checksum"] == d2["checksum"]


def test_different_modes_diverge():
    """Same base seed but different sampler modes must produce different seeds."""
    a = psn_derive_seed(999, "ancestral", 0)
    s = psn_derive_seed(999, "sde", 0)
    f = psn_derive_seed(999, "fixed", 0)
    assert len({a, s, f}) == 3


def test_offset_shifts_seed_deterministically():
    """Offset must shift the derived seed, and be reproducible."""
    base = psn_derive_seed(42, "sde", 0)
    shifted = psn_derive_seed(42, "sde", 7)
    assert base != shifted
    # Reproducibility of the shifted value.
    assert shifted == psn_derive_seed(42, "sde", 7)
    # Negative offset is also deterministic and distinct.
    neg = psn_derive_seed(42, "sde", -7)
    assert neg == psn_derive_seed(42, "sde", -7)
    assert neg != base


def test_seed_is_nonnegative_64bit():
    """Derived seeds must be non-negative and fit in 64 bits."""
    for seed in (-1, 0, 1, 10**12, -10**12):
        for mode in MODES:
            for off in (-5, 0, 5):
                d = psn_derive_seed(seed, mode, off)
                assert 0 <= d < (1 << 64)


def test_bad_mode_raises():
    """An invalid mode must raise ValueError."""
    with pytest.raises(ValueError):
        psn_derive_seed(1, "bogus", 0)
    with pytest.raises(ValueError):
        psn_noise_descriptor(1, "bogus")


def test_bad_seed_type_raises():
    """Non-int (and bool) seeds must raise TypeError."""
    with pytest.raises(TypeError):
        psn_derive_seed("123", "fixed", 0)
    with pytest.raises(TypeError):
        psn_derive_seed(True, "fixed", 0)
    with pytest.raises(TypeError):
        psn_derive_seed(1.0, "fixed", 0)


def test_bad_offset_type_raises():
    """Non-int offsets must raise TypeError."""
    with pytest.raises(TypeError):
        psn_derive_seed(1, "fixed", "0")
    with pytest.raises(TypeError):
        psn_derive_seed(1, "fixed", True)


def test_descriptor_shape_validation():
    """Invalid shapes must raise ValueError."""
    with pytest.raises(ValueError):
        psn_noise_descriptor(1, "fixed", (0, 4))
    with pytest.raises(ValueError):
        psn_noise_descriptor(1, "fixed", (4,))
    with pytest.raises(ValueError):
        psn_noise_descriptor(1, "fixed", "4,4")


def test_visualizer_grid_deterministic_and_bounded():
    """Smoke: descriptor -> grid is deterministic, correctly shaped, values in [0,255]."""
    seed = psn_derive_seed(7, "sde", 3)
    desc = psn_noise_descriptor(seed, "sde", (4, 4))
    g1 = psn_noise_to_grid(desc, width=4, height=4)
    g2 = psn_noise_to_grid(desc, width=4, height=4)
    assert g1 == g2
    assert len(g1) == 4
    assert all(len(row) == 4 for row in g1)
    for row in g1:
        for v in row:
            assert 0 <= v <= 255


def test_visualizer_rejects_bad_descriptor():
    """Visualizer must reject a non-dict or incomplete descriptor."""
    with pytest.raises(TypeError):
        psn_noise_to_grid("not a dict")
    with pytest.raises(ValueError):
        psn_noise_to_grid({"seed": 1, "mode": "fixed"})  # missing keys


def test_node_manipulator_run_and_visualizer_pipeline():
    """End-to-end: manipulator -> descriptor -> visualizer grid, no errors."""
    manip = PSN_Seed_Manipulator()
    seed, noise = manip.run(base_seed=2024, mode="ancestral", offset=1, shape="3,5")
    assert isinstance(seed, int)
    assert isinstance(noise, dict)
    assert noise["mode"] == "ancestral"
    assert noise["shape"] == (3, 5)

    viz = PSN_Seed_Visualizer()
    (grid,) = viz.run(noise=noise, width=3, height=5)
    assert len(grid) == 5
    assert all(len(row) == 3 for row in grid)


def test_node_manipulator_bad_mode_raises():
    """Node wrapper must propagate the invalid-mode error."""
    manip = PSN_Seed_Manipulator()
    with pytest.raises(ValueError):
        manip.run(base_seed=1, mode="nope", offset=0)


def test_node_manipulator_bad_seed_type_raises():
    """Node wrapper must propagate the bad-seed-type error."""
    manip = PSN_Seed_Manipulator()
    with pytest.raises(TypeError):
        manip.run(base_seed="x", mode="fixed", offset=0)


def test_node_mappings_present():
    """Both nodes must be registered in the class/display mappings."""
    assert "PSN_Seed_Manipulator" in NODE_CLASS_MAPPINGS
    assert "PSN_Seed_Visualizer" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Seed_Manipulator"] is PSN_Seed_Manipulator
    assert NODE_CLASS_MAPPINGS["PSN_Seed_Visualizer"] is PSN_Seed_Visualizer
    assert "PSN_Seed_Manipulator" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_Seed_Visualizer" in NODE_DISPLAY_NAME_MAPPINGS


def test_helpers_are_pure_and_deterministic():
    """FNV and LCG helpers must be deterministic and type-checked."""
    assert psn_fnv1a64("abc") == psn_fnv1a64("abc")
    assert psn_fnv1a64("abc") != psn_fnv1a64("abd")
    with pytest.raises(TypeError):
        psn_fnv1a64(123)
    assert psn_lcg_step(0) == psn_lcg_step(0)
    assert psn_lcg_step(1) != psn_lcg_step(0)
    with pytest.raises(TypeError):
        psn_lcg_step("x")
