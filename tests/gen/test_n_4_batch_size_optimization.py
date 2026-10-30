"""Tests for PSN_Batch_Calculator (psn_nodes.gen.n_4_batch_size_optimization)."""

import math
import pytest

from psn_nodes.gen.n_4_batch_size_optimization import (
    PSN_Batch_Calculator,
    psn_batch_calculate,
    DEFAULT_SAFETY_MARGIN_PCT,
)


def test_basic_calculation_within_range():
    # vram=24, model=6, per_image=1, margin=10% -> free = 24 - 6 - 2.4 = 15.6
    # batch = floor(15.6 / 1) = 15 -> clamped to max_batch=8
    optimal, est, reason = psn_batch_calculate(24.0, 6.0, 1.0, 1, 8)
    assert optimal == 8
    assert reason == "clamped_to_max"
    assert est == pytest.approx(6.0 + 8 * 1.0)


def test_clamped_to_min():
    # vram=8, model=6, per_image=1, margin=10% -> free = 8 - 6 - 0.8 = 1.2
    # batch = floor(1.2 / 1) = 1 -> within [1, 8]
    optimal, est, reason = psn_batch_calculate(8.0, 6.0, 1.0, 1, 8)
    assert optimal == 1
    assert reason == "within_range"
    assert est == pytest.approx(6.0 + 1 * 1.0)


def test_insufficient_vram_falls_back_to_min():
    # vram=5, model=6 -> free = 5 - 6 - 0.5 = -1.5 <= 0
    optimal, est, reason = psn_batch_calculate(5.0, 6.0, 1.0, 1, 8)
    assert optimal == 1
    assert reason == "insufficient_vram_for_model"
    assert est == pytest.approx(6.0 + 1 * 1.0)


def test_exact_boundary_no_clamp():
    # Choose values so raw_batch lands exactly on max_batch.
    # vram=10, model=2, per_image=1, margin=0% -> free = 8 -> batch=8, max=8
    optimal, est, reason = psn_batch_calculate(10.0, 2.0, 1.0, 1, 8, safety_margin_pct=0.0)
    assert optimal == 8
    assert reason == "within_range"
    assert est == pytest.approx(2.0 + 8 * 1.0)


def test_zero_safety_margin():
    # vram=10, model=2, per_image=2, margin=0 -> free=8 -> batch=floor(8/2)=4
    optimal, est, reason = psn_batch_calculate(10.0, 2.0, 2.0, 1, 8, safety_margin_pct=0.0)
    assert optimal == 4
    assert reason == "within_range"
    assert est == pytest.approx(2.0 + 4 * 2.0)


def test_high_per_image_clamps_to_min():
    # vram=10, model=2, per_image=5, margin=10% -> free = 10-2-1 = 7 -> batch=floor(7/5)=1
    optimal, est, reason = psn_batch_calculate(10.0, 2.0, 5.0, 1, 8)
    assert optimal == 1
    assert reason == "within_range"
    assert est == pytest.approx(2.0 + 1 * 5.0)


def test_invalid_per_image_zero_raises():
    with pytest.raises(ValueError, match="per_image_vram_gb"):
        psn_batch_calculate(24.0, 6.0, 0.0, 1, 8)


def test_invalid_min_batch_raises():
    with pytest.raises(ValueError, match="min_batch"):
        psn_batch_calculate(24.0, 6.0, 1.0, 0, 8)


def test_invalid_max_less_than_min_raises():
    with pytest.raises(ValueError, match="max_batch"):
        psn_batch_calculate(24.0, 6.0, 1.0, 5, 3)


def test_invalid_safety_margin_pct_raises():
    with pytest.raises(ValueError, match="safety_margin_pct"):
        psn_batch_calculate(24.0, 6.0, 1.0, 1, 8, safety_margin_pct=1.5)


def test_non_numeric_input_raises():
    with pytest.raises(ValueError, match="vram_available_gb"):
        psn_batch_calculate("24", 6.0, 1.0, 1, 8)


def test_node_run_returns_tuple():
    node = PSN_Batch_Calculator()
    result = node.run(24.0, 6.0, 1.0, 1, 8)
    assert isinstance(result, tuple)
    assert len(result) == 3
    optimal, est, reason = result
    assert isinstance(optimal, int)
    assert isinstance(est, float)
    assert isinstance(reason, str)
    assert optimal == 8
    assert est == pytest.approx(14.0)


def test_node_run_with_default_safety_margin():
    node = PSN_Batch_Calculator()
    # vram=20, model=4, per_image=1, margin=10% -> free = 20-4-2 = 14 -> batch=14 -> clamp to 8
    optimal, est, reason = node.run(20.0, 4.0, 1.0, 1, 8)
    assert optimal == 8
    assert reason == "clamped_to_max"
    assert est == pytest.approx(4.0 + 8 * 1.0)


def test_float_inputs_produce_int_batch():
    optimal, est, reason = psn_batch_calculate(16.5, 3.2, 0.75, 1, 16)
    assert isinstance(optimal, int)
    # free = 16.5 - 3.2 - 1.65 = 11.65; batch = floor(11.65/0.75) = floor(15.533) = 15
    assert optimal == 15
    assert reason == "within_range"
    assert est == pytest.approx(3.2 + 15 * 0.75)
