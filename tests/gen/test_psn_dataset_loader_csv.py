"""Tests for PSN_Dataset_Loader_CSV (pure-logic CSV parsing)."""

import pytest

from psn_nodes.gen.psn_dataset_loader_csv import (
    PSN_Dataset_Loader_CSV,
    parse_csv_text,
    _redact_path,
    _validate_delimiter,
)


def test_parse_simple_csv_with_header():
    csv_text = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
    columns, rows, reason = parse_csv_text(csv_text, ",", True)
    assert reason == "ok"
    assert columns == ["name", "age", "city"]
    assert len(rows) == 2
    assert rows[0] == ["Alice", "30", "NYC"]
    assert rows[1] == ["Bob", "25", "LA"]


def test_parse_csv_without_header():
    csv_text = "1,2,3\n4,5,6\n"
    columns, rows, reason = parse_csv_text(csv_text, ",", False)
    assert reason == "ok"
    assert columns == ["col_0", "col_1", "col_2"]
    assert len(rows) == 2
    assert rows[0] == ["1", "2", "3"]


def test_parse_csv_with_semicolon_delimiter():
    csv_text = "a;b;c\n1;2;3\n"
    columns, rows, reason = parse_csv_text(csv_text, ";", True)
    assert reason == "ok"
    assert columns == ["a", "b", "c"]
    assert rows == [["1", "2", "3"]]


def test_parse_csv_with_tab_delimiter():
    csv_text = "x\ty\n1\t2\n"
    columns, rows, reason = parse_csv_text(csv_text, "\t", True)
    assert reason == "ok"
    assert columns == ["x", "y"]
    assert rows == [["1", "2"]]


def test_parse_csv_empty_text():
    columns, rows, reason = parse_csv_text("", ",", True)
    assert columns == []
    assert rows == []
    assert reason == "no data found in csv_text"


def test_parse_csv_non_string_input():
    columns, rows, reason = parse_csv_text(12345, ",", True)
    assert columns == []
    assert rows == []
    assert reason == "csv_text must be a string"


def test_parse_csv_bad_delimiter_empty():
    columns, rows, reason = parse_csv_text("a,b\n1,2\n", "", True)
    assert columns == []
    assert rows == []
    assert "delimiter" in reason.lower()


def test_parse_csv_bad_delimiter_multi_char():
    columns, rows, reason = parse_csv_text("a,b\n1,2\n", "::", True)
    assert columns == []
    assert rows == []
    assert "delimiter" in reason.lower()


def test_parse_csv_bad_delimiter_not_allowed():
    columns, rows, reason = parse_csv_text("a,b\n1,2\n", "#", True)
    assert columns == []
    assert rows == []
    assert "delimiter" in reason.lower()


def test_parse_csv_ragged_rows_padded():
    csv_text = "a,b,c\n1,2\n3,4,5,6\n"
    columns, rows, reason = parse_csv_text(csv_text, ",", True)
    assert reason == "ok"
    # Header has 3 cols, but data row 2 has 4 cols. Max cols is 4.
    # Header is padded to 4: ["a", "b", "c", "col_3"]
    assert columns == ["a", "b", "c", "col_3"]
    # Row 1 has 2 cells, padded to 4. Row 2 has 4 cells.
    assert rows[0] == ["1", "2", "", ""]
    assert rows[1] == ["3", "4", "5", "6"]


def test_parse_csv_duplicate_header_names():
    csv_text = "a,a,b\n1,2,3\n"
    columns, rows, reason = parse_csv_text(csv_text, ",", True)
    assert reason == "ok"
    assert columns == ["a", "a_1", "b"]
    assert rows == [["1", "2", "3"]]


def test_parse_csv_empty_header_cells():
    csv_text = ",,\n1,2,3\n"
    columns, rows, reason = parse_csv_text(csv_text, ",", True)
    assert reason == "ok"
    assert columns == ["col_0", "col_1", "col_2"]
    assert rows == [["1", "2", "3"]]


def test_redact_path_basic():
    assert _redact_path("/home/user/data.csv") == "data"
    assert _redact_path("C:\\Users\\me\\file.txt") == "file"
    assert _redact_path("noext") == "noext"
    assert _redact_path("") == "unknown"
    assert _redact_path(None) == "unknown"


def test_validate_delimiter_ok():
    ok, norm, why = _validate_delimiter(",")
    assert ok is True
    assert norm == ","
    assert why == "ok"


def test_validate_delimiter_bad_type():
    ok, norm, why = _validate_delimiter(123)
    assert ok is False
    assert "string" in why.lower()


def test_node_run_returns_correct_types():
    node = PSN_Dataset_Loader_CSV()
    rows, columns, reason = node.run(
        file_path="test.csv",
        csv_text="a,b\n1,2\n",
        delimiter=",",
        header_row=True,
    )
    assert isinstance(rows, list)
    assert isinstance(columns, list)
    assert isinstance(reason, str)
    assert columns == ["a", "b"]
    assert rows == [["1", "2"]]
    assert "test" in reason  # redacted label present


def test_node_run_empty_csv():
    node = PSN_Dataset_Loader_CSV()
    rows, columns, reason = node.run(
        file_path="empty.csv",
        csv_text="",
        delimiter=",",
        header_row=True,
    )
    assert rows == []
    assert columns == []
    assert "no data" in reason


def test_node_run_bad_delimiter():
    node = PSN_Dataset_Loader_CSV()
    rows, columns, reason = node.run(
        file_path="bad.csv",
        csv_text="a,b\n1,2\n",
        delimiter="::",
        header_row=True,
    )
    assert rows == []
    assert columns == []
    assert "delimiter" in reason.lower()
