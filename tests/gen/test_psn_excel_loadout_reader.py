"""Tests for PSN_Excel_Loadout_Reader."""

import pytest
from psn_nodes.gen.psn_excel_loadout_reader import (
    PSN_Excel_Loadout_Reader,
    _cast_value,
    _find_column_index,
    _normalize_header,
)


def test_cast_value_int():
    hint, val = _cast_value("42")
    assert hint == "int"
    assert val == "42"


def test_cast_value_float():
    hint, val = _cast_value("3.14")
    assert hint == "float"
    assert val == "3.14"


def test_cast_value_bool_true():
    hint, val = _cast_value("true")
    assert hint == "bool"
    assert val == "true"


def test_cast_value_bool_false():
    hint, val = _cast_value("False")
    assert hint == "bool"
    assert val == "false"


def test_cast_value_string():
    hint, val = _cast_value("hello world")
    assert hint == "string"
    assert val == "hello world"


def test_cast_value_empty():
    hint, val = _cast_value("")
    assert hint == "string"
    assert val == ""


def test_cast_value_negative_int():
    hint, val = _cast_value("-7")
    assert hint == "int"
    assert val == "-7"


def test_cast_value_negative_float():
    hint, val = _cast_value("-2.5")
    assert hint == "float"
    assert val == "-2.5"


def test_normalize_header():
    assert _normalize_header("  My Param  ") == "my param"
    assert _normalize_header("My   Param") == "my param"
    assert _normalize_header("MY_PARAM") == "my_param"


def test_find_column_index_found():
    headers = ["Name", "Age", "Active"]
    found, idx, reason = _find_column_index(headers, "age")
    assert found is True
    assert idx == 1


def test_find_column_index_not_found():
    headers = ["Name", "Age"]
    found, idx, reason = _find_column_index(headers, "missing")
    assert found is False
    assert idx == -1


def test_find_column_index_empty_headers():
    found, idx, reason = _find_column_index([], "name")
    assert found is False
    assert idx == -1


def test_run_with_explicit_header_row():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["Alice", "30", "true"]
    header_row = ["name", "age", "active"]
    value, type_hint = node.run(row_data, "age", header_row)
    assert value == "30"
    assert type_hint == "int"


def test_run_with_header_from_first_row():
    node = PSN_Excel_Loadout_Reader()
    # First row is header, second row is data
    row_data = [["name", "age", "active"], ["Bob", "25", "false"]]
    value, type_hint = node.run(row_data, "active")
    assert value == "false"
    assert type_hint == "bool"


def test_run_param_not_found():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["Alice", "30"]
    header_row = ["name", "age"]
    value, type_hint = node.run(row_data, "missing", header_row)
    assert value == ""
    assert type_hint == "string"


def test_run_empty_row_data():
    node = PSN_Excel_Loadout_Reader()
    value, type_hint = node.run([], "name")
    assert value == ""
    assert type_hint == "string"


def test_run_column_index_out_of_range():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["Alice"]
    header_row = ["name", "age", "active"]
    value, type_hint = node.run(row_data, "active", header_row)
    assert value == ""
    assert type_hint == "string"


def test_run_case_insensitive_header_match():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["Alice", "30"]
    header_row = ["Name", "AGE"]
    value, type_hint = node.run(row_data, "age", header_row)
    assert value == "30"
    assert type_hint == "int"


def test_run_whitespace_in_header():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["Alice", "30"]
    header_row = ["  Name  ", "  Age  "]
    value, type_hint = node.run(row_data, "age", header_row)
    assert value == "30"
    assert type_hint == "int"


def test_run_float_value():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["3.14159"]
    header_row = ["pi"]
    value, type_hint = node.run(row_data, "pi", header_row)
    assert value == "3.14159"
    assert type_hint == "float"


def test_run_string_value():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["hello"]
    header_row = ["greeting"]
    value, type_hint = node.run(row_data, "greeting", header_row)
    assert value == "hello"
    assert type_hint == "string"


def test_run_bool_yes():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["yes"]
    header_row = ["flag"]
    value, type_hint = node.run(row_data, "flag", header_row)
    assert value == "true"
    assert type_hint == "bool"


def test_run_bool_no():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["no"]
    header_row = ["flag"]
    value, type_hint = node.run(row_data, "flag", header_row)
    assert value == "false"
    assert type_hint == "bool"


def test_run_malformed_numeric():
    node = PSN_Excel_Loadout_Reader()
    row_data = ["not_a_number"]
    header_row = ["num"]
    value, type_hint = node.run(row_data, "num", header_row)
    assert value == "not_a_number"
    assert type_hint == "string"
