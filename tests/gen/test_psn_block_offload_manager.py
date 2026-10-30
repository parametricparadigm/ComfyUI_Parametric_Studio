"""
Tests for psn_nodes.gen.psn_block_offload_manager
"""

import pytest
from psn_nodes.gen.psn_block_offload_manager import (
    PSN_BlockOffloadManager,
    build_offload_plan,
    simulate_offload_state,
    validate_plan,
    _parse_block_indices,
)


def test_parse_single_indices():
    result = _parse_block_indices("0,2,5", 10)
    assert result == [0, 2, 5]


def test_parse_range_and_single():
    result = _parse_block_indices("0-3,7", 10)
    assert result == [0, 1, 2, 3, 7]


def test_parse_negative_indices():
    result = _parse_block_indices("-1,-2", 10)
    assert result == [8, 9]


def test_parse_empty_string():
    result = _parse_block_indices("", 10)
    assert result == []


def test_parse_invalid_index():
    with pytest.raises(ValueError):
        _parse_block_indices("abc", 10)


def test_parse_out_of_range():
    with pytest.raises(ValueError):
        _parse_block_indices("10", 10)


def test_build_plan_explicit():
    plan = build_offload_plan(10, "0-3", "explicit")
    assert plan["offload"] == [0, 1, 2, 3]
    assert plan["keep"] == [4, 5, 6, 7, 8, 9]
    assert plan["offload_count"] == 4
    assert plan["keep_count"] == 6


def test_build_plan_all():
    plan = build_offload_plan(5, "", "all")
    assert plan["offload"] == [0, 1, 2, 3, 4]
    assert plan["keep"] == []


def test_build_plan_invalid_mode():
    with pytest.raises(ValueError):
        build_offload_plan(10, "0", "invalid_mode")


def test_build_plan_zero_blocks():
    with pytest.raises(ValueError):
        build_offload_plan(0, "0", "explicit")


def test_simulate_state():
    plan = build_offload_plan(4, "0,2", "explicit")
    state = simulate_offload_state(plan)
    assert state[0] == "cpu"
    assert state[1] == "vram"
    assert state[2] == "cpu"
    assert state[3] == "vram"


def test_validate_plan_ok():
    plan = build_offload_plan(4, "0,2", "explicit")
    ok, reason = validate_plan(plan)
    assert ok is True
    assert reason == "OK"


def test_validate_plan_bad():
    ok, reason = validate_plan({"offload": [0], "keep": [0], "total_blocks": 1, "mode": "explicit"})
    assert ok is False
    assert "both" in reason


def test_node_run_valid():
    node = PSN_BlockOffloadManager()
    plan, summary, valid = node.run(total_blocks=8, offload_blocks="0-3", mode="explicit")
    assert valid is True
    assert plan["offload"] == [0, 1, 2, 3]
    assert "Offloaded" in summary


def test_node_run_invalid_input():
    node = PSN_BlockOffloadManager()
    plan, summary, valid = node.run(total_blocks=8, offload_blocks="abc", mode="explicit")
    assert valid is False
    assert "Error" in summary


def test_node_run_all_mode():
    node = PSN_BlockOffloadManager()
    plan, summary, valid = node.run(total_blocks=4, offload_blocks="", mode="all")
    assert valid is True
    assert plan["offload"] == [0, 1, 2, 3]
    assert plan["keep"] == []
