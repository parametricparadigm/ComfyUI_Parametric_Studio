"""PSN_Excel_Loadout_Selector: pure-logic loadout row selection from tabular text.

This module implements the secure, pure-logic core of an Excel loadout selector.
Because the runtime environment forbids file I/O, network access, and third-party
libraries (openpyxl/pandas), this node does NOT read .xlsx files. Instead it
accepts the tabular data as plain text (TSV or CSV) plus a header row, and
selects the row whose first column matches the requested loadout name (or by
0-based index). It validates the payload, enforces an allow-list of column
counts, and returns the selected row as a list of cell values plus its index.

Inputs are plain values (strings, numbers); no sockets, files, or subprocesses
are opened. The caller is responsible for extracting the sheet contents from
the .xlsx file (e.g., via openpyxl/pandas in a separate, sandboxed step) and
passing them here as text.
"""

import csv
import io
import json

CAT = "ParametricStudio/Excel"

# Allow-list of acceptable column counts (A-L = 12 columns, but we allow a
# small range to be tolerant of trailing empty cells or fewer columns).
_MIN_COLS = 1
_MAX_COLS = 12

# Allowed delimiters for the tabular text payload.
_ALLOWED_DELIMS = ("\t", ",")


def _psn_parse_table(text, delimiter):
    """Parse tabular text into a list of rows (list of strings).

    Returns (rows, error). rows is a list of lists of strings.
    """
    if not isinstance(text, str):
        return None, "table_text must be a string"
    if delimiter not in _ALLOWED_DELIMS:
        return None, "delimiter must be one of: %s" % (_ALLOWED_DELIMS,)
    if not text.strip():
        return None, "table_text is empty"
    try:
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [row for row in reader]
    except Exception as exc:
        return None, "failed to parse table_text: %s" % exc
    if not rows:
        return None, "table_text produced no rows"
    return rows, None


def _psn_validate_rows(rows):
    """Validate that all rows have a consistent, allowed column count.

    Returns (ok, error, col_count).
    """
    if not rows:
        return False, "no rows to validate", 0
    col_count = len(rows[0])
    if col_count < _MIN_COLS or col_count > _MAX_COLS:
        return False, "column count %d outside allowed range [%d, %d]" % (
            col_count, _MIN_COLS, _MAX_COLS), col_count
    for i, row in enumerate(rows):
        if len(row) != col_count:
            return False, "row %d has %d columns, expected %d" % (
                i, len(row), col_count), col_count
    return True, None, col_count


def _psn_find_row(rows, loadout_name, use_index, index_value):
    """Find the matching row by name (column A) or by 0-based index.

    Returns (row, row_index, error). row_index is 0-based relative to data
    rows (excluding header). If not found, row is None and error is set.
    """
    if use_index:
        if not isinstance(index_value, int):
            return None, None, "index_value must be an integer"
        if index_value < 0 or index_value >= len(rows):
            return None, None, "index_value %d out of range [0, %d]" % (
                index_value, len(rows) - 1)
        return rows[index_value], index_value, None

    if not isinstance(loadout_name, str):
        return None, None, "loadout_name must be a string"
    target = loadout_name.strip()
    for i, row in enumerate(rows):
        if row and row[0].strip() == target:
            return row, i, None
    return None, None, "loadout_name '%s' not found in column A" % loadout_name


class PSN_Excel_Loadout_Selector:
    """Select a loadout row from tabular text by name or index.

    Pure-logic node: accepts table data as text (TSV/CSV) and returns the
    matching row. No file I/O, no network, no third-party dependencies.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "table_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Tab-separated or comma-separated table data including a header row. Column A must contain loadout names.",
                }),
                "loadout_name": ("STRING", {
                    "default": "",
                    "tooltip": "Name of the loadout to select (matches column A).",
                }),
                "delimiter": (list(_ALLOWED_DELIMS), {
                    "tooltip": "Delimiter used in table_text.",
                }),
            },
            "optional": {
                "use_index": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "If True, select by 0-based row index instead of name.",
                }),
                "index_value": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 10000,
                    "tooltip": "0-based row index (data rows, excluding header).",
                }),
                "sheet_name": ("STRING", {
                    "default": "",
                    "tooltip": "Sheet tab name (informational; not used for parsing).",
                }),
                "excel_path": ("STRING", {
                    "default": "",
                    "tooltip": "Original .xlsx path (informational; not read by this node).",
                }),
            },
        }

    RETURN_TYPES = ("LIST", "INT", "STRING")
    RETURN_NAMES = ("row_data", "row_index", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, table_text, loadout_name, delimiter,
            use_index=False, index_value=0, sheet_name="", excel_path=""):
        rows, err = _psn_parse_table(table_text, delimiter)
        if err:
            return ([], -1, "ERROR: %s" % err)

        ok, verr, col_count = _psn_validate_rows(rows)
        if not ok:
            return ([], -1, "ERROR: %s" % verr)

        # Separate header from data rows.
        if len(rows) < 2:
            return ([], -1, "ERROR: table must have a header row and at least one data row")
        header = rows[0]
        data_rows = rows[1:]

        row, row_index, find_err = _psn_find_row(
            data_rows, loadout_name, use_index, index_value)
        if find_err:
            return ([], -1, "ERROR: %s" % find_err)

        # Return the row as a list of strings (cell values for columns A-L).
        return (list(row), row_index, "OK")


NODE_CLASS_MAPPINGS = {
    "PSN_Excel_Loadout_Selector": PSN_Excel_Loadout_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Excel_Loadout_Selector": "PSN Excel Loadout Selector",
}
