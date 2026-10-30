"""Tests for the pure-logic LTX2 identity preservation nodes."""

import math

import pytest

from psn_nodes.gen.n_9_ltx2_identity_preservation import (
    PSN_LTX2_Identity_Lock,
    PSN_LTX2_Stabilize,
    identity_lock,
    stabilize,
    _similarity,
    _high_freq_energy,
)


def test_identity_lock_increases_similarity_to_reference():
    current = [1.0, 0.0, 1.0, 0.0]
    reference = [0.0, 1.0, 0.0, 1.0]
    locked = identity_lock(current, reference, 0.8)
    sim_before = _similarity(current, reference)
    sim_after = _similarity(locked, reference)
    assert sim_after > sim_before
    # With strength 0.8 the locked latent should be much closer to reference.
    assert sim_after > 0.9


def test_identity_lock_strength_zero_returns_current():
    current = [1.0, 2.0, 3.0]
    reference = [9.0, 8.0, 7.0]
    locked = identity_lock(current, reference, 0.0)
    assert locked == current


def test_identity_lock_strength_one_returns_reference():
    current = [1.0, 2.0, 3.0]
    reference = [9.0, 8.0, 7.0]
    locked = identity_lock(current, reference, 1.0)
    assert locked == reference


def test_identity_lock_clamps_strength():
    current = [1.0, 2.0]
    reference = [3.0, 4.0]
    # Strength above 1 should be clamped to 1 -> returns reference.
    locked = identity_lock(current, reference, 5.0)
    assert locked == reference
    # Strength below 0 should be clamped to 0 -> returns current.
    locked = identity_lock(current, reference, -3.0)
    assert locked == current


def test_identity_lock_length_mismatch_raises():
    with pytest.raises(ValueError):
        identity_lock([1.0, 2.0], [1.0, 2.0, 3.0], 0.5)


def test_identity_lock_bad_input_raises():
    with pytest.raises(ValueError):
        identity_lock("not a list", [1.0], 0.5)
    with pytest.raises(ValueError):
        identity_lock([1.0, "x"], [1.0, 1.0], 0.5)
    with pytest.raises(ValueError):
        identity_lock([float("nan")], [1.0], 0.5)


def test_stabilize_reduces_high_frequency_content():
    # Alternating signal has high high-frequency energy.
    noisy = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    stabilized = stabilize(noisy, 1.0)
    hf_before = _high_freq_energy(noisy)
    hf_after = _high_freq_energy(stabilized)
    assert hf_after < hf_before


def test_stabilize_factor_zero_returns_original():
    latent = [0.0, 1.0, 0.0, 1.0]
    out = stabilize(latent, 0.0)
    assert out == latent


def test_stabilize_smooths_constant_signal():
    # A constant signal is unchanged by a low-pass filter.
    latent = [2.0, 2.0, 2.0, 2.0]
    out = stabilize(latent, 1.0)
    assert all(abs(v - 2.0) < 1e-9 for v in out)


def test_stabilize_empty_list():
    assert stabilize([], 0.5) == []


def test_stabilize_bad_input_raises():
    with pytest.raises(ValueError):
        stabilize("nope", 0.5)
    with pytest.raises(ValueError):
        stabilize([1.0, float("inf")], 0.5)


def test_node_identity_lock_run():
    node = PSN_LTX2_Identity_Lock()
    (locked,) = node.run([1.0, 0.0], [0.0, 1.0], 0.5)
    assert locked == [0.5, 0.5]


def test_node_stabilize_run():
    node = PSN_LTX2_Stabilize()
    (out,) = node.run([0.0, 1.0, 0.0], 1.0)
    # Moving average of [0,1,0] with window 3:
    # i=0: avg(0,1)=0.5 ; i=1: avg(0,1,0)=1/3 ; i=2: avg(1,0)=0.5
    assert len(out) == 3
    assert abs(out[0] - 0.5) < 1e-9
    assert abs(out[1] - 1.0 / 3.0) < 1e-9
    assert abs(out[2] - 0.5) < 1e-9


def test_node_input_types_shape():
    it = PSN_LTX2_Identity_Lock.INPUT_TYPES()
    assert "current_latent" in it["required"]
    assert "reference_latent" in it["required"]
    assert "lock_strength" in it["required"]
    it2 = PSN_LTX2_Stabilize.INPUT_TYPES()
    assert "latent" in it2["required"]
    assert "stability_factor" in it2["required"]
