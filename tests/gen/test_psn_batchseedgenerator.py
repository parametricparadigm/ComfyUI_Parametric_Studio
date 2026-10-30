"""Tests for PSN_BatchSeedGenerator."""

import pytest
from psn_nodes.gen.psn_batchseedgenerator import PSN_BatchSeedGenerator


@pytest.fixture
def node():
    return PSN_BatchSeedGenerator()


def test_basic_generation(node):
    """Test basic seed generation with count=5, base=100, offset=10."""
    (seeds,) = node.run(count=5, base_seed=100, offset=10)
    assert len(seeds) == 5
    assert seeds == [100, 110, 120, 130, 140]


def test_single_seed(node):
    """Test generation of a single seed."""
    (seeds,) = node.run(count=1, base_seed=42, offset=7)
    assert len(seeds) == 1
    assert seeds == [42]


def test_zero_count(node):
    """Test that count=0 returns an empty list."""
    (seeds,) = node.run(count=0, base_seed=100, offset=10)
    assert seeds == []
    assert len(seeds) == 0


def test_negative_count_clamped(node):
    """Test that negative count is clamped to 0, returning empty list."""
    (seeds,) = node.run(count=-5, base_seed=100, offset=10)
    assert seeds == []
    assert len(seeds) == 0


def test_zero_offset(node):
    """Test that offset=0 produces all identical seeds."""
    (seeds,) = node.run(count=4, base_seed=99, offset=0)
    assert len(seeds) == 4
    assert all(s == 99 for s in seeds)


def test_negative_offset(node):
    """Test generation with a negative offset."""
    (seeds,) = node.run(count=4, base_seed=100, offset=-10)
    assert seeds == [100, 90, 80, 70]


def test_negative_base_seed(node):
    """Test generation with a negative base seed."""
    (seeds,) = node.run(count=3, base_seed=-50, offset=10)
    assert seeds == [-50, -40, -30]


def test_large_count_uniqueness(node):
    """GPU smoke equivalent: generate 10 seeds and assert all are unique (offset != 0)."""
    (seeds,) = node.run(count=10, base_seed=12345, offset=1)
    assert len(seeds) == 10
    assert len(set(seeds)) == 10, "All seeds should be unique when offset != 0"


def test_large_offset(node):
    """Test with a large offset value."""
    (seeds,) = node.run(count=3, base_seed=0, offset=1000000)
    assert seeds == [0, 1000000, 2000000]


def test_input_types_structure(node):
    """Verify INPUT_TYPES returns the expected structure."""
    it = PSN_BatchSeedGenerator.INPUT_TYPES()
    assert "required" in it
    assert "count" in it["required"]
    assert "base_seed" in it["required"]
    assert "offset" in it["required"]
    assert it["required"]["count"][0] == "INT"
    assert it["required"]["base_seed"][0] == "INT"
    assert it["required"]["offset"][0] == "INT"


def test_return_types(node):
    """Verify RETURN_TYPES and RETURN_NAMES are correct."""
    assert PSN_BatchSeedGenerator.RETURN_TYPES == ("INT_LIST",)
    assert PSN_BatchSeedGenerator.RETURN_NAMES == ("seeds",)
    assert PSN_BatchSeedGenerator.FUNCTION == "run"
