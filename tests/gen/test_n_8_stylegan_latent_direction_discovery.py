"""Tests for PSN_StyleGAN_Direction_Discover and PSN_StyleGAN_Direction_Apply."""

import math
import pytest
from psn_nodes.gen.n_8_stylegan_latent_direction_discovery import (
    PSN_StyleGAN_Direction_Discover,
    PSN_StyleGAN_Direction_Apply,
    _pca_discover,
    _apply_direction,
    _validate_latent,
    _validate_latent_batch,
)


def _make_batch(n_samples, dim, seed=0):
    """Create a deterministic batch of latents with known structure."""
    import random
    rng = random.Random(seed)
    batch = []
    for _ in range(n_samples):
        lat = [rng.gauss(0, 1) for _ in range(dim)]
        batch.append(lat)
    return batch


def test_discover_returns_correct_number_of_directions():
    """PCA should return exactly num_directions vectors."""
    batch = _make_batch(50, 8, seed=42)
    directions, eigenvalues = _pca_discover(batch, 3, seed=42)
    assert len(directions) == 3
    assert len(eigenvalues) == 3


def test_discover_directions_are_orthogonal():
    """PCA directions should be mutually orthogonal (dot product ~ 0)."""
    batch = _make_batch(100, 6, seed=123)
    directions, _ = _pca_discover(batch, 3, seed=123)
    for i in range(len(directions)):
        for j in range(i + 1, len(directions)):
            dot = sum(directions[i][k] * directions[j][k] for k in range(len(directions[i])))
            assert abs(dot) < 1e-6, f"Directions {i} and {j} not orthogonal: dot={dot}"


def test_discover_directions_are_unit_vectors():
    """Each PCA direction should be a unit vector."""
    batch = _make_batch(50, 5, seed=7)
    directions, _ = _pca_discover(batch, 2, seed=7)
    for d in directions:
        norm = math.sqrt(sum(x * x for x in d))
        assert abs(norm - 1.0) < 1e-6, f"Direction not unit: norm={norm}"


def test_apply_direction_changes_latent():
    """Applying a non-zero direction with non-zero strength should change the latent."""
    latent = [1.0, 2.0, 3.0, 4.0]
    direction = [1.0, 0.0, 0.0, 0.0]
    modified = _apply_direction(latent, direction, 1.0)
    assert modified != latent
    # Projection onto [1,0,0,0] is 1.0, so modified[0] = 1.0 + 1.0*1.0*1.0 = 2.0
    assert abs(modified[0] - 2.0) < 1e-9
    # Other components unchanged
    for i in range(1, 4):
        assert abs(modified[i] - latent[i]) < 1e-9


def test_apply_direction_zero_strength_no_change():
    """Strength=0 should leave the latent unchanged."""
    latent = [1.0, 2.0, 3.0]
    direction = [0.5, 0.5, 0.5]
    modified = _apply_direction(latent, direction, 0.0)
    for i in range(len(latent)):
        assert abs(modified[i] - latent[i]) < 1e-12


def test_apply_direction_dimension_mismatch_raises():
    """Mismatched dimensions should raise ValueError."""
    latent = [1.0, 2.0, 3.0]
    direction = [1.0, 0.0]
    with pytest.raises(ValueError, match="same dimension"):
        _apply_direction(latent, direction, 1.0)


def test_discover_empty_batch_raises():
    """Empty batch should raise ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        _pca_discover([], 3, seed=42)


def test_discover_inconsistent_dimensions_raises():
    """Batch with inconsistent latent dimensions should raise ValueError."""
    batch = [[1.0, 2.0], [1.0, 2.0, 3.0]]
    with pytest.raises(ValueError, match="dimension"):
        _pca_discover(batch, 2, seed=42)


def test_discover_num_directions_exceeds_dim_clamps():
    """num_directions > dim should be clamped to dim."""
    batch = _make_batch(20, 3, seed=5)
    directions, eigenvalues = _pca_discover(batch, 10, seed=5)
    assert len(directions) == 3
    assert len(eigenvalues) == 3


def test_discover_non_finite_latent_raises():
    """Latent with NaN or Inf should raise ValueError."""
    batch = [[1.0, float('nan'), 3.0], [1.0, 2.0, 3.0]]
    with pytest.raises(ValueError, match="finite"):
        _pca_discover(batch, 2, seed=42)


def test_apply_direction_non_finite_strength_raises():
    """Non-finite strength should raise ValueError."""
    latent = [1.0, 2.0]
    direction = [1.0, 0.0]
    with pytest.raises(ValueError, match="finite"):
        _apply_direction(latent, direction, float('inf'))


def test_node_discover_run():
    """Test the node's run method end-to-end."""
    node = PSN_StyleGAN_Direction_Discover()
    batch = _make_batch(30, 4, seed=99)
    directions, eigenvalues = node.run(batch, 2, seed=99)
    assert len(directions) == 2
    assert len(eigenvalues) == 2
    # Eigenvalues should be non-negative for covariance matrix
    for ev in eigenvalues:
        assert ev >= -1e-9


def test_node_apply_run():
    """Test the apply node's run method end-to-end."""
    node = PSN_StyleGAN_Direction_Apply()
    latent = [1.0, 2.0, 3.0]
    direction = [1.0, 0.0, 0.0]
    (modified,) = node.run(latent, direction, 2.0)
    # dot = 1.0, modified[0] = 1.0 + 2.0*1.0*1.0 = 3.0
    assert abs(modified[0] - 3.0) < 1e-9
    assert abs(modified[1] - 2.0) < 1e-9
    assert abs(modified[2] - 3.0) < 1e-9


def test_pca_finds_dominant_direction():
    """PCA should find the direction of maximum variance first."""
    # Create data with strong variance along x-axis
    import random
    rng = random.Random(42)
    batch = []
    for _ in range(200):
        x = rng.gauss(0, 10.0)  # high variance
        y = rng.gauss(0, 0.1)   # low variance
        batch.append([x, y])
    directions, eigenvalues = _pca_discover(batch, 2, seed=42)
    # First direction should be close to [1, 0] or [-1, 0]
    d0 = directions[0]
    assert abs(abs(d0[0]) - 1.0) < 0.1, f"First direction not along x: {d0}"
    # First eigenvalue should be much larger than second
    assert eigenvalues[0] > eigenvalues[1] * 10
