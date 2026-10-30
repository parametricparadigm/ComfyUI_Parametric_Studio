"""Tests for PSN_Excel_Loadout_Selector (pure-logic loadout row selection)."""

import pytest

from psn_nodes.gen.psn_excel_loadout_selector import (
    PSN_Excel_Loadout_Selector,
    _psn_parse_table,
    _psn_validate_rows,
    _psn_find_row,
)


def _make_node():
    return PSN_Excel_Loadout_Selector()


def _tsv_table(header, rows):
    lines = ["\t".join(header)]
    for r in rows:
        lines.append("\t".join(r))
    return "\n".join(lines)


class TestPSNExcelLoadoutSelector:

    def test_select_by_name_success(self):
        node = _make_node()
        table = _tsv_table(
            ["Name", "Res", "FPS", "Quality"],
            [
                ["Video High-Quality", "1920x1080", "60", "High"],
                ["Video Low-Quality", "1280x720", "30", "Low"],
            ],
        )
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="Video High-Quality",
            delimiter="\t",
        )
        assert status == "OK"
        assert row_index == 0
        assert row_data == ["Video High-Quality", "1920x1080", "60", "High"]

    def test_select_by_name_second_row(self):
        node = _make_node()
        table = _tsv_table(
            ["Name", "Res", "FPS"],
            [
                ["Alpha", "1920x1080", "60"],
                ["Beta", "1280x720", "30"],
                ["Gamma", "3840x2160", "120"],
            ],
        )
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="Beta",
            delimiter="\t",
        )
        assert status == "OK"
        assert row_index == 1
        assert row_data == ["Beta", "1280x720", "30"]

    def test_select_by_index(self):
        node = _make_node()
        table = _tsv_table(
            ["Name", "Res", "FPS"],
            [
                ["Alpha", "1920x1080", "60"],
                ["Beta", "1280x720", "30"],
            ],
        )
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="",
            delimiter="\t",
            use_index=True,
            index_value=1,
        )
        assert status == "OK"
        assert row_index == 1
        assert row_data == ["Beta", "1280x720", "30"]

    def test_name_not_found(self):
        node = _make_node()
        table = _tsv_table(
            ["Name", "Res"],
            [["Alpha", "1920x1080"]],
        )
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="NonExistent",
            delimiter="\t",
        )
        assert row_data == []
        assert row_index == -1
        assert status.startswith("ERROR")
        assert "not found" in status

    def test_index_out_of_range(self):
        node = _make_node()
        table = _tsv_table(
            ["Name", "Res"],
            [["Alpha", "1920x1080"]],
        )
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="",
            delimiter="\t",
            use_index=True,
            index_value=5,
        )
        assert row_data == []
        assert row_index == -1
        assert status.startswith("ERROR")
        assert "out of range" in status

    def test_empty_table_text(self):
        node = _make_node()
        row_data, row_index, status = node.run(
            table_text="",
            loadout_name="Alpha",
            delimiter="\t",
        )
        assert row_data == []
        assert row_index == -1
        assert status.startswith("ERROR")
        assert "empty" in status

    def test_header_only_no_data_rows(self):
        node = _make_node()
        table = "Name\tRes\tFPS"
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="Alpha",
            delimiter="\t",
        )
        assert row_data == []
        assert row_index == -1
        assert status.startswith("ERROR")
        assert "at least one data row" in status

    def test_inconsistent_column_count(self):
        node = _make_node()
        table = "Name\tRes\tFPS\nAlpha\t1920x1080\nBeta\t1280x720\t30"
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="Alpha",
            delimiter="\t",
        )
        assert row_data == []
        assert row_index == -1
        assert status.startswith("ERROR")
        assert "columns" in status

    def test_csv_delimiter(self):
        node = _make_node()
        table = "Name,Res,FPS\nAlpha,1920x1080,60\nBeta,1280x720,30"
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="Beta",
            delimiter=",",
        )
        assert status == "OK"
        assert row_index == 1
        assert row_data == ["Beta", "1280x720", "30"]

    def test_whitespace_in_name_is_stripped(self):
        node = _make_node()
        table = _tsv_table(
            ["Name", "Res"],
            [["  Alpha  ", "1920x1080"]],
        )
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="Alpha",
            delimiter="\t",
        )
        assert status == "OK"
        assert row_index == 0
        assert row_data[0] == "  Alpha  "

    def test_too_many_columns(self):
        node = _make_node()
        # 13 columns exceeds _MAX_COLS of 12
        header = ["C%d" % i for i in range(13)]
        row = ["V%d" % i for i in range(13)]
        table = _tsv_table(header, [row])
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="V0",
            delimiter="\t",
        )
        assert row_data == []
        assert row_index == -1
        assert status.startswith("ERROR")
        assert "column count" in status

    def test_parse_table_bad_delimiter(self):
        rows, err = _psn_parse_table("a\tb", "|")
        assert rows is None
        assert err is not None
        assert "delimiter" in err

    def test_validate_rows_empty(self):
        ok, err, col_count = _psn_validate_rows([])
        assert ok is False
        assert err is not None

    def test_find_row_by_index_non_int(self):
        rows = [["A", "1"], ["B", "2"]]
        row, idx, err = _psn_find_row(rows, "", True, "not_an_int")
        assert row is None
        assert err is not None
        assert "integer" in err

    def test_optional_fields_do_not_break(self):
        node = _make_node()
        table = _tsv_table(
            ["Name", "Res"],
            [["Alpha", "1920x1080"]],
        )
        row_data, row_index, status = node.run(
            table_text=table,
            loadout_name="Alpha",
            delimiter="\t",
            use_index=False,
            index_value=0,
            sheet_name="Sheet1",
            excel_path="/fake/path.xlsx",
        )
        assert status == "OK"
        assert row_index == 0
        assert row_data == ["Alpha", "1920x1080"]
