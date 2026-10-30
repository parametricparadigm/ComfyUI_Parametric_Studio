"""Tests for PSN_GSheet_Cell_Selector node."""

import pytest
from psn_nodes.gen.psn_gsheet_cell_selector import PSN_GSheet_Cell_Selector


@pytest.fixture
def node():
    return PSN_GSheet_Cell_Selector()


def test_valid_indices_string_cell(node):
    """Test extracting a string cell with valid indices."""
    matrix = [["hello", "world"], ["foo", "bar"]]
    result = node.run(matrix, 0, 1)
    assert result == ("world",)


def test_valid_indices_numeric_cell(node):
    """Test extracting a numeric cell, should return string representation."""
    matrix = [[1, 2], [3, 4]]
    result = node.run(matrix, 1, 0)
    assert result == ("3",)


def test_out_of_bounds_row(node):
    """Test row index out of bounds returns empty string."""
    matrix = [["a", "b"], ["c", "d"]]
    result = node.run(matrix, 5, 0)
    assert result == ("",)


def test_out_of_bounds_col(node):
    """Test column index out of bounds returns empty string."""
    matrix = [["a", "b"], ["c", "d"]]
    result = node.run(matrix, 0, 5)
    assert result == ("",)


def test_empty_matrix(node):
    """Test empty matrix returns empty string."""
    result = node.run([], 0, 0)
    assert result == ("",)


def test_none_cell(node):
    """Test None cell returns empty string."""
    matrix = [["a", None], [None, "d"]]
    result = node.run(matrix, 0, 1)
    assert result == ("",)


def test_negative_indices(node):
    """Test negative indices return empty string."""
    matrix = [["a", "b"], ["c", "d"]]
    result = node.run(matrix, -1, 0)
    assert result == ("",)
    result = node.run(matrix, 0, -1)
    assert result == ("",)


def test_non_list_matrix(node):
    """Test non-list matrix input returns empty string."""
    result = node.run("not a list", 0, 0)
    assert result == ("",)


def test_non_list_row(node):
    """Test row that is not a list returns empty string."""
    matrix = ["not a list", ["a", "b"]]
    result = node.run(matrix, 0, 0)
    assert result == ("",)


def test_float_indices(node):
    """Test float indices return empty string (must be int)."""
    matrix = [["a", "b"], ["c", "d"]]
    result = node.run(matrix, 0.0, 0)
    assert result == ("",)


def test_dict_cell_json_serialization(node):
    """Test dict cell is JSON serialized."""
    matrix = [[{"key": "value"}]]
    result = node.run(matrix, 0, 0)
    assert result == ('{"key": "value"}',)


def test_list_cell_json_serialization(node):
    """Test list cell is JSON serialized."""
    matrix = [[[1, 2, 3]]]
    result = node.run(matrix, 0, 0)
    assert result == ('[1, 2, 3]',)


def test_empty_string_cell(node):
    """Test empty string cell returns empty string."""
    matrix = [["", "b"]]
    result = node.run(matrix, 0, 0)
    assert result == ("",)


def test_boolean_cell(node):
    """Test boolean cell returns string representation."""
    matrix = [[True, False]]
    result = node.run(matrix, 0, 0)
    assert result == ("True",)


def test_large_valid_indices(node):
    """Test large but valid indices."""
    matrix = [["x"]]
    result = node.run(matrix, 0, 0)
    assert result == ("x",)
