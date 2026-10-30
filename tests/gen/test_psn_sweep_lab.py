"""Tests for psn_nodes.gen.psn_sweep_lab (pure-logic sweep planning/analysis)."""

import json

from psn_nodes.gen.psn_sweep_lab import (
    PSN_Sweep_Config,
    PSN_Sweep_Analyzer,
    parse_values,
    grid_layout,
    build_labels,
    format_score_table,
    select_best,
    MAX_VALUES,
)


def test_parse_values_steps_valid():
    values, err = parse_values("10,20,30", "steps")
    assert err is None
    assert values == [10, 20, 30]


def test_parse_values_cfg_floats():
    values, err = parse_values("1.5, 2.0, 7", "cfg")
    assert err is None
    assert values == [1.5, 2.0, 7.0]


def test_parse_values_samplers_strings():
    values, err = parse_values("euler, dpmpp_2m, lcm", "sampler")
    assert err is None
    assert values == ["euler", "dpmpp_2m", "lcm"]


def test_parse_values_bad_param_name():
    values, err = parse_values("10,20", "bogus")
    assert values is None
    assert "param_name" in err


def test_parse_values_too_many():
    raw = ",".join(str(i) for i in range(1, MAX_VALUES + 2))
    values, err = parse_values(raw, "steps")
    assert values is None
    assert "too many" in err


def test_parse_values_duplicate():
    values, err = parse_values("10,10,20", "steps")
    assert values is None
    assert "duplicate" in err


def test_parse_values_negative_steps():
    values, err = parse_values("0,10", "steps")
    assert values is None
    assert ">= 1" in err


def test_parse_values_empty_string():
    values, err = parse_values("   ", "steps")
    assert values is None
    assert "non-empty" in err


def test_grid_layout_4_is_2x2():
    rows, cols = grid_layout(4)
    assert (rows, cols) == (2, 2)


def test_grid_layout_3_is_2x2():
    rows, cols = grid_layout(3)
    assert (rows, cols) == (2, 2)


def test_grid_layout_zero():
    assert grid_layout(0) == (0, 0)


def test_build_labels():
    assert build_labels([10, 20, 30]) == ["10", "20", "30"]


def test_config_node_smoke_3_steps():
    node = PSN_Sweep_Config()
    plan, labels, rows, cols, valid = node.run("steps", "10,20,30")
    assert valid is True
    assert (rows, cols) == (2, 2)
    parsed = json.loads(plan)
    assert parsed["ok"] is True
    assert parsed["values"] == [10, 20, 30]
    assert labels == "10, 20, 30"


def test_config_node_grid_2x2_for_4_values():
    node = PSN_Sweep_Config()
    plan, labels, rows, cols, valid = node.run("steps", "10,20,30,40")
    assert valid is True
    assert (rows, cols) == (2, 2)


def test_config_node_invalid_param():
    node = PSN_Sweep_Config()
    plan, labels, rows, cols, valid = node.run("bogus", "10,20")
    assert valid is False
    parsed = json.loads(plan)
    assert parsed["ok"] is False
    assert "param_name" in parsed["error"]


def test_config_node_too_many_values():
    node = PSN_Sweep_Config()
    raw = ",".join(str(i) for i in range(1, MAX_VALUES + 2))
    plan, labels, rows, cols, valid = node.run("steps", raw)
    assert valid is False
    parsed = json.loads(plan)
    assert "too many" in parsed["error"]


def test_analyzer_ssim_picks_max():
    node = PSN_Sweep_Analyzer()
    best, table, score, valid = node.run("10,20,30", "[0.5, 0.9, 0.7]", "ssim")
    assert valid is True
    assert best == "20"
    assert score == 0.9
    assert "ssim score table" in table


def test_analyzer_lpips_picks_min():
    node = PSN_Sweep_Analyzer()
    best, table, score, valid = node.run("10,20,30", "[0.5, 0.1, 0.7]", "lpips")
    assert valid is True
    assert best == "20"
    assert score == 0.1


def test_analyzer_bad_metric():
    node = PSN_Sweep_Analyzer()
    best, table, score, valid = node.run("10,20", "[0.5, 0.7]", "bogus")
    assert valid is False
    assert "metric" in table


def test_analyzer_length_mismatch():
    node = PSN_Sweep_Analyzer()
    best, table, score, valid = node.run("10,20,30", "[0.5, 0.7]", "ssim")
    assert valid is False
    assert "mismatch" in table


def test_analyzer_bad_scores_json():
    node = PSN_Sweep_Analyzer()
    best, table, score, valid = node.run("10,20", "not-json", "ssim")
    assert valid is False
    assert "JSON" in table


def test_select_best_empty():
    best, score, err = select_best([], [], "ssim")
    assert best is None
    assert "no values" in err


def test_select_best_non_numeric_score():
    best, score, err = select_best(["10", "20"], [0.5, "x"], "ssim")
    assert best is None
    assert "numeric" in err


def test_format_score_table_mismatch():
    out = format_score_table([1, 2], [0.5], "ssim")
    assert "mismatch" in out
