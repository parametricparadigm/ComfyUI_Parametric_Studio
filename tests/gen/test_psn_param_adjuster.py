"""Tests for PSN_Param_Adjuster node."""

import pytest
from psn_nodes.gen.psn_param_adjuster import PSN_Param_Adjuster


@pytest.fixture
def node():
    return PSN_Param_Adjuster()


def test_blend_factor_zero_keeps_current(node):
    """blend_factor=0.0 should return current params unchanged."""
    current = {"cfg": 7.0, "steps": 30, "prompt": "a cat"}
    suggested = {"cfg": 12.0, "steps": 50, "prompt": "a dog"}
    (result,) = node.run(current, suggested, 0.0)
    assert result["cfg"] == 7.0
    assert result["steps"] == 30
    assert result["prompt"] == "a cat"


def test_blend_factor_one_uses_suggested(node):
    """blend_factor=1.0 should return suggested params."""
    current = {"cfg": 7.0, "steps": 30, "prompt": "a cat"}
    suggested = {"cfg": 12.0, "steps": 50, "prompt": "a dog"}
    (result,) = node.run(current, suggested, 1.0)
    assert result["cfg"] == 12.0
    assert result["steps"] == 50
    assert result["prompt"] == "a dog"


def test_blend_factor_half_numeric(node):
    """blend_factor=0.5 should average numeric values."""
    current = {"cfg": 7.0, "steps": 30}
    suggested = {"cfg": 13.0, "steps": 50}
    (result,) = node.run(current, suggested, 0.5)
    assert result["cfg"] == pytest.approx(10.0)
    assert result["steps"] == pytest.approx(40.0)


def test_blend_factor_half_non_numeric(node):
    """blend_factor=0.5 with non-numeric values: blend > 0.5 is false, so keep current."""
    current = {"prompt": "a cat", "model": "sd15"}
    suggested = {"prompt": "a dog", "model": "sdxl"}
    (result,) = node.run(current, suggested, 0.5)
    # blend == 0.5 is not > 0.5, so current is kept
    assert result["prompt"] == "a cat"
    assert result["model"] == "sd15"


def test_blend_factor_above_half_non_numeric(node):
    """blend_factor=0.6 with non-numeric values: use suggested."""
    current = {"prompt": "a cat"}
    suggested = {"prompt": "a dog"}
    (result,) = node.run(current, suggested, 0.6)
    assert result["prompt"] == "a dog"


def test_key_only_in_current(node):
    """Keys only in current_params are retained (scaled if numeric and blend > 0)."""
    current = {"extra": 10.0, "name": "test"}
    suggested = {"cfg": 5.0}
    (result,) = node.run(current, suggested, 0.5)
    assert result["extra"] == pytest.approx(5.0)  # 10 * (1 - 0.5)
    assert result["name"] == "test"
    assert result["cfg"] == pytest.approx(2.5)  # 5 * 0.5


def test_key_only_in_suggested(node):
    """Keys only in suggested_params are included (scaled if numeric and blend < 1)."""
    current = {"cfg": 7.0}
    suggested = {"new_key": 20.0, "label": "v2"}
    (result,) = node.run(current, suggested, 0.5)
    # cfg is only in current, so it gets scaled by (1 - blend)
    assert result["cfg"] == pytest.approx(3.5)  # 7.0 * (1 - 0.5)
    assert result["new_key"] == pytest.approx(10.0)  # 20 * 0.5
    assert result["label"] == "v2"


def test_empty_dicts(node):
    """Both dicts empty should return empty dict."""
    (result,) = node.run({}, {}, 0.5)
    assert result == {}


def test_blend_factor_clamped_above_one(node):
    """blend_factor > 1.0 should be clamped to 1.0."""
    current = {"cfg": 7.0}
    suggested = {"cfg": 12.0}
    (result,) = node.run(current, suggested, 1.5)
    assert result["cfg"] == 12.0


def test_blend_factor_clamped_below_zero(node):
    """blend_factor < 0.0 should be clamped to 0.0."""
    current = {"cfg": 7.0}
    suggested = {"cfg": 12.0}
    (result,) = node.run(current, suggested, -0.5)
    assert result["cfg"] == 7.0


def test_int_values_with_extreme_blend(node):
    """Integer values with blend 0.0 or 1.0 should remain integers."""
    current = {"steps": 30}
    suggested = {"steps": 50}
    (result_zero,) = node.run(current, suggested, 0.0)
    assert result_zero["steps"] == 30
    assert isinstance(result_zero["steps"], int)

    (result_one,) = node.run(current, suggested, 1.0)
    assert result_one["steps"] == 50
    assert isinstance(result_one["steps"], int)


def test_mixed_types_same_key(node):
    """If current is numeric and suggested is string, use non-numeric path."""
    current = {"value": 5.0}
    suggested = {"value": "high"}
    (result,) = node.run(current, suggested, 0.7)
    assert result["value"] == "high"  # blend > 0.5, use suggested
