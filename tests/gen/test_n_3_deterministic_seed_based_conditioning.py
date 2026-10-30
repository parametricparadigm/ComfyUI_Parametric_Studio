"""Tests for psn_nodes.gen.n_3_deterministic_seed_based_conditioning."""

import json

import pytest

from psn_nodes.gen.n_3_deterministic_seed_based_conditioning import (
    PSN_ZeroCLIPConditioner,
    generate_conditioning,
    _MODEL_DIMS,
    _STRATEGIES,
    _MODEL_TYPES,
)


def test_deterministic_same_seed_same_output():
    """seed=123 must always produce identical values."""
    a = generate_conditioning(123, "B", "sd15")
    b = generate_conditioning(123, "B", "sd15")
    assert a == b
    assert a["clip"] == b["clip"]
    assert a["pooled"] == b["pooled"]


def test_shape_sd15():
    """SD1.5 clip dim = 768, pooled dim = 768."""
    payload = generate_conditioning(42, "A", "sd15")
    assert len(payload["clip"]) == 768
    assert len(payload["pooled"]) == 768
    assert payload["clip_dim"] == 768
    assert payload["pooled_dim"] == 768


def test_shape_sdxl():
    """SDXL clip dim = 2048, pooled dim = 1280."""
    payload = generate_conditioning(42, "C", "sdxl")
    assert len(payload["clip"]) == 2048
    assert len(payload["pooled"]) == 1280
    assert payload["clip_dim"] == 2048
    assert payload["pooled_dim"] == 1280


def test_different_seeds_differ():
    """Different seeds should (almost certainly) produce different vectors."""
    a = generate_conditioning(1, "B", "sd15")
    b = generate_conditioning(2, "B", "sd15")
    assert a["clip"] != b["clip"]


def test_all_strategies_produce_valid_output():
    """Every strategy must produce the correct shape and finite floats."""
    for strategy in _STRATEGIES:
        for model_type in _MODEL_TYPES:
            payload = generate_conditioning(99, strategy, model_type)
            clip_dim, pooled_dim = _MODEL_DIMS[model_type]
            assert len(payload["clip"]) == clip_dim
            assert len(payload["pooled"]) == pooled_dim
            for v in payload["clip"]:
                assert -1.0 <= v <= 1.0
            for v in payload["pooled"]:
                assert -1.0 <= v <= 1.0


def test_node_run_returns_valid_json():
    """The node's run() must return parseable JSON with expected keys."""
    node = PSN_ZeroCLIPConditioner()
    conditioning_json, summary = node.run(seed=123, strategy="D", model_type="sdxl")
    data = json.loads(conditioning_json)
    assert data["seed"] == 123
    assert data["strategy"] == "D"
    assert data["model_type"] == "sdxl"
    assert len(data["clip"]) == 2048
    assert len(data["pooled"]) == 1280
    assert "seed=123" in summary


def test_bad_strategy_raises():
    """An invalid strategy must raise ValueError."""
    with pytest.raises(ValueError, match="strategy"):
        generate_conditioning(1, "X", "sd15")


def test_bad_model_type_raises():
    """An invalid model_type must raise ValueError."""
    with pytest.raises(ValueError, match="model_type"):
        generate_conditioning(1, "A", "flux")


def test_non_integer_seed_raises():
    """A non-integer seed (e.g. float or bool) must raise ValueError."""
    with pytest.raises(ValueError, match="seed"):
        generate_conditioning(1.5, "A", "sd15")
    with pytest.raises(ValueError, match="seed"):
        generate_conditioning(True, "A", "sd15")


def test_negative_seed_works():
    """Negative seeds are valid integers and must produce deterministic output."""
    a = generate_conditioning(-42, "C", "sd15")
    b = generate_conditioning(-42, "C", "sd15")
    assert a == b
    assert len(a["clip"]) == 768
