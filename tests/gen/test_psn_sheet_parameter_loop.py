"""Tests for PSN_Sheet_Parameter_Loop."""

import pytest

from psn_nodes.gen.psn_sheet_parameter_loop import PSN_Sheet_Parameter_Loop


def test_basic_iteration():
    matrix = [
        ["name", "value"],
        ["a", "1"],
        ["b", "2"],
        ["c", "3"],
    ]
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 1, 3)
    assert count == 3
    assert sets == [
        {"name": "a", "value": "1"},
        {"name": "b", "value": "2"},
        {"name": "c", "value": "3"},
    ]


def test_partial_range():
    matrix = [
        ["x", "y"],
        ["1", "2"],
        ["3", "4"],
        ["5", "6"],
        ["7", "8"],
    ]
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 2, 3)
    assert count == 2
    assert sets == [{"x": "3", "y": "4"}, {"x": "5", "y": "6"}]


def test_clamps_to_available_rows():
    matrix = [
        ["k"],
        ["v1"],
        ["v2"],
    ]
    # end_row beyond available rows should clamp
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 1, 100)
    assert count == 2
    assert sets == [{"k": "v1"}, {"k": "v2"}]


def test_start_after_end_returns_empty():
    matrix = [
        ["k"],
        ["v1"],
    ]
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 5, 2)
    assert count == 0
    assert sets == []


def test_short_row_pads_with_empty_string():
    matrix = [
        ["a", "b", "c"],
        ["1"],
        ["1", "2"],
    ]
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 1, 2)
    assert count == 2
    assert sets[0] == {"a": "1", "b": "", "c": ""}
    assert sets[1] == {"a": "1", "b": "2", "c": ""}


def test_none_cells_become_empty_string():
    matrix = [
        ["a", "b"],
        [None, "x"],
    ]
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 1, 1)
    assert count == 1
    assert sets[0] == {"a": "", "b": "x"}


def test_bad_matrix_type_raises():
    with pytest.raises(ValueError):
        PSN_Sheet_Parameter_Loop.run("not a list", 1, 2)


def test_header_row_out_of_range_raises():
    matrix = [["a"], ["1"]]
    with pytest.raises(ValueError):
        PSN_Sheet_Parameter_Loop.run(matrix, 1, 1, header_row=5)


def test_custom_header_row():
    matrix = [
        ["ignore1", "ignore2"],
        ["name", "value"],
        ["a", "1"],
        ["b", "2"],
    ]
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 2, 3, header_row=1)
    assert count == 2
    assert sets == [
        {"name": "a", "value": "1"},
        {"name": "b", "value": "2"},
    ]


def test_scalar_row_normalized():
    matrix = [
        ["v"],
        "solo",
    ]
    sets, count = PSN_Sheet_Parameter_Loop.run(matrix, 1, 1)
    assert count == 1
    assert sets[0] == {"v": "solo"}
