"""Tests for psn_nodes.gen.psn_auto_cfg_rescale."""

import math
import pytest

from psn_nodes.gen.psn_auto_cfg_rescale import (
    PSN_Auto_CFG_Rescale,
    rescale_cfg,
)


def test_rescale_none_mode_clamps_to_max_cfg():
    """In 'none' mode the value is simply clamped to max_cfg."""
    assert rescale_cfg(7.0, 0.5, 10.0, "none") == pytest.approx(7.0)
    assert rescale_cfg(15.0, 0.5, 10.0, "none") == pytest.approx(10.0)
    assert rescale_cfg(3.0, 0.5, 10.0, "none") == pytest.approx(3.0)


def test_rescale_linear_reduces_with_high_diff():
    """Linear mode should reduce CFG when diff is high."""
    low = rescale_cfg(7.0, 0.0, 10.0, "linear")
    high = rescale_cfg(7.0, 1.0, 10.0, "linear")
    mid = rescale_cfg(7.0, 0.5, 10.0, "linear")
    assert low == pytest.approx(7.0)
    assert high == pytest.approx(3.5)
    assert mid == pytest.approx(5.25)
    assert high < mid < low


def test_rescale_sigmoid_reduces_with_high_diff():
    """Sigmoid mode should reduce CFG, with a steeper middle."""
    low = rescale_cfg(7.0, 0.0, 10.0, "sigmoid")
    high = rescale_cfg(7.0, 1.0, 10.0, "sigmoid")
    mid = rescale_cfg(7.0, 0.5, 10.0, "sigmoid")
    
    # At risk=0: x = 2*(0 - 0.5) = -1. sigmoid(-1) = 1/(1+e^1) ≈ 0.2689.
    # scale = 0.5 + 0.5*(1 - 0.2689) = 0.5 + 0.3655 = 0.8655.
    expected_low_scale = 0.5 + 0.5 * (1.0 - (1.0 / (1.0 + math.exp(1.0))))
    assert low == pytest.approx(7.0 * expected_low_scale)
    
    # At risk=1: x = 2*(1 - 0.5) = 1. sigmoid(1) = 1/(1+e^-1) ≈ 0.7311.
    # scale = 0.5 + 0.5*(1 - 0.7311) = 0.5 + 0.1345 = 0.6345.
    expected_high_scale = 0.5 + 0.5 * (1.0 - (1.0 / (1.0 + math.exp(-1.0))))
    assert high == pytest.approx(7.0 * expected_high_scale)
    
    # At risk=0.5: x = 0. sigmoid(0) = 0.5.
    # scale = 0.5 + 0.5*(1 - 0.5) = 0.75.
    assert mid == pytest.approx(7.0 * 0.75)
    
    assert high < mid < low


def test_rescale_respects_max_cfg_ceiling():
    """The result must never exceed max_cfg regardless of mode."""
    for mode in ("linear", "sigmoid", "none"):
        result = rescale_cfg(100.0, 0.0, 5.0, mode)
        assert result <= 5.0 + 1e-9


def test_rescale_bad_mode_raises():
    """An unknown mode should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown rescale mode"):
        rescale_cfg(7.0, 0.5, 10.0, "quadratic")


def test_rescale_negative_inputs_raise():
    """Negative cfg, diff, or non-positive max_cfg should raise."""
    with pytest.raises(ValueError, match="cfg must be non-negative"):
        rescale_cfg(-1.0, 0.5, 10.0, "linear")
    with pytest.raises(ValueError, match="diff must be non-negative"):
        rescale_cfg(7.0, -0.5, 10.0, "linear")
    with pytest.raises(ValueError, match="max_cfg must be positive"):
        rescale_cfg(7.0, 0.5, 0.0, "linear")


def test_rescale_non_finite_inputs_raise():
    """NaN or inf inputs should raise ValueError."""
    with pytest.raises(ValueError, match="must be finite"):
        rescale_cfg(float("inf"), 0.5, 10.0, "linear")
    with pytest.raises(ValueError, match="must be finite"):
        rescale_cfg(7.0, float("nan"), 10.0, "linear")


def test_rescale_non_numeric_inputs_raise():
    """Non-numeric inputs should raise TypeError."""
    with pytest.raises(TypeError):
        rescale_cfg("7.0", 0.5, 10.0, "linear")
    with pytest.raises(TypeError):
        rescale_cfg(7.0, None, 10.0, "linear")


def test_node_run_returns_rescaled_value():
    """The node wrapper should return the rescaled CFG and a reason."""
    node = PSN_Auto_CFG_Rescale()
    model, rescaled, reason = node.run(
        model="test_model",
        cfg=7.0,
        diff=1.0,
        max_cfg=10.0,
        rescale_mode="linear",
    )
    assert model == "test_model"
    assert rescaled == pytest.approx(3.5)
    assert "rescaled" in reason


def test_node_run_no_change_when_diff_zero():
    """With diff=0 and mode='none', the CFG should be unchanged."""
    node = PSN_Auto_CFG_Rescale()
    model, rescaled, reason = node.run(
        model="test_model",
        cfg=7.0,
        diff=0.0,
        max_cfg=10.0,
        rescale_mode="none",
    )
    assert rescaled == pytest.approx(7.0)
    assert "no change" in reason


def test_node_run_error_on_bad_mode():
    """The node should gracefully handle an invalid mode by returning an error reason."""
    node = PSN_Auto_CFG_Rescale()
    model, rescaled, reason = node.run(
        model="test_model",
        cfg=7.0,
        diff=0.5,
        max_cfg=10.0,
        rescale_mode="invalid_mode",
    )
    assert model == "test_model"
    assert rescaled == 7.0  # original cfg returned on error
    assert "error" in reason


def test_rescale_zero_cfg_returns_tiny_positive():
    """If cfg is 0, the result should be a tiny positive floor, not zero."""
    result = rescale_cfg(0.0, 0.5, 10.0, "linear")
    assert result > 0
    assert result < 1e-3
