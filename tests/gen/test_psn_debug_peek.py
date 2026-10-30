"""Tests for psn_nodes.gen.psn_debug_peek (pure-logic peek planning + grid layout)."""

import pytest

from psn_nodes.gen.psn_debug_peek import (
    PSN_Peek_Plan,
    PSN_Peek_Grid,
    build_peek_plan,
    grid_layout,
    _parse_peek_steps,
)


def test_parse_peek_steps_basic():
    steps, err = _parse_peek_steps("1,5,10", 20)
    assert err == ""
    assert steps == [1, 5, 10]


def test_parse_peek_steps_dedup_and_sort():
    steps, err = _parse_peek_steps("10,1,5,5,1", 20)
    assert err == ""
    assert steps == [1, 5, 10]


def test_parse_peek_steps_out_of_range():
    steps, err = _parse_peek_steps("1,25", 20)
    assert steps == []
    assert "out of range" in err


def test_parse_peek_steps_non_integer_token():
    steps, err = _parse_peek_steps("1,abc,10", 20)
    assert steps == []
    assert "non-integer" in err


def test_parse_peek_steps_empty_string():
    steps, err = _parse_peek_steps("", 20)
    assert err == ""
    assert steps == []


def test_parse_peek_steps_bad_total():
    steps, err = _parse_peek_steps("1,5", 0)
    assert steps == []
    assert "positive integer" in err


def test_build_peek_plan_disabled():
    steps, indices, enabled, err = build_peek_plan("1,5,10", 20, enabled=False)
    assert err == ""
    assert steps == [1, 5, 10]
    assert indices == [0, 1, 2]
    assert enabled is False


def test_build_peek_plan_error_propagates():
    steps, indices, enabled, err = build_peek_plan("1,99", 20, enabled=True)
    assert steps == []
    assert indices == []
    assert enabled is False
    assert "out of range" in err


def test_grid_layout_single():
    assert grid_layout(1) == (1, 1)


def test_grid_layout_three():
    # 3 images -> cols=2 (ceil(sqrt(3))=2), rows=ceil(3/2)=2
    assert grid_layout(3) == (2, 2)


def test_grid_layout_four():
    assert grid_layout(4) == (2, 2)


def test_grid_layout_zero():
    assert grid_layout(0) == (1, 0)


def test_grid_layout_negative():
    assert grid_layout(-5) == (1, 0)


def test_plan_node_run_valid():
    node = PSN_Peek_Plan()
    count, total, enabled, summary = node.run(steps=20, peek_steps="1,5,10", enabled=True)
    assert count == 3
    assert total == 20
    assert enabled is True
    assert "peeks=1,5,10" in summary


def test_plan_node_run_error():
    node = PSN_Peek_Plan()
    count, total, enabled, summary = node.run(steps=20, peek_steps="1,99", enabled=True)
    assert count == 0
    assert enabled is False
    assert summary.startswith("ERROR:")


def test_grid_node_run_basic():
    node = PSN_Peek_Grid()
    rows, cols, summary = node.run(peek_count=3)
    assert rows == 2
    assert cols == 2
    assert "count=3" in summary


def test_grid_node_run_max_cols():
    node = PSN_Peek_Grid()
    rows, cols, summary = node.run(peek_count=6, max_cols=2)
    assert cols == 2
    assert rows == 3  # ceil(6/2)
