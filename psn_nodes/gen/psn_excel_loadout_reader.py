"""PSN_Excel_Loadout_Reader: extract a single parameter value from a loadout row.

This node is pure-logic only. It does not open files, sockets, or use torch.
It expects `row_data` as a plain Python list of strings (the selected row from
PSN_Excel_Loadout_Selector) and `param_name` as a string. It maps the parameter
name to a column index using a cached header row, retrieves the value, and
attempts a safe type cast to int, float, bool, or string.

Inputs:
    row_data (LIST): list of string cells for the selected row.
    param_name (STRING): the parameter name (matches a column header).
    header_row (LIST, optional): list of column header strings. If omitted,
        the first row of `row_data` is treated as the header (cached).

Outputs:
    value (STRING): the extracted value as a string.
    type_hint (STRING): one of "int", "float", "string", "bool".
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Excel"

_TYPE_INT = "int"
_TYPE_FLOAT = "float"
_TYPE_BOOL = "bool"
_TYPE_STRING = "string"

_BOOL_TRUE = {"true", "1", "yes", "y", "on"}
_BOOL_FALSE = {"false", "0", "no", "n", "off"}


def _normalize_header(name):
    """Normalize a header name for case-insensitive, whitespace-tolerant matching."""
    return " ".join(str(name).strip().lower().split())


def _try_cast_int(text):
    """Attempt to cast text to int. Returns (True, int_value) or (False, None)."""
    try:
        return True, int(str(text).strip())
    except (ValueError, TypeError):
        return False, None


def _try_cast_float(text):
    """Attempt to cast text to float. Returns (True, float_value) or (False, None)."""
    try:
        return True, float(str(text).strip())
    except (ValueError, TypeError):
        return False, None


def _try_cast_bool(text):
    """Attempt to cast text to bool. Returns (True, bool_value) or (False, None)."""
    t = str(text).strip().lower()
    if t in _BOOL_TRUE:
        return True, True
    if t in _BOOL_FALSE:
        return True, False
    return False, None


def _cast_value(text):
    """
    Attempt to cast a string value to int, float, bool, or string.
    Returns (type_hint, value_as_string).
    """
    s = str(text).strip()
    if not s:
        return _TYPE_STRING, ""

    # Try int, then float, then bool, then string.
    ok, v = _try_cast_int(s)
    if ok:
        return _TYPE_INT, str(v)

    ok, v = _try_cast_float(s)
    if ok:
        return _TYPE_FLOAT, str(v)

    ok, v = _try_cast_bool(s)
    if ok:
        return _TYPE_BOOL, str(v).lower()

    return _TYPE_STRING, s


def _find_column_index(header_row, param_name):
    """
    Find the column index for param_name in header_row.
    Returns (found: bool, index: int, reason: str).
    """
    if not header_row:
        return False, -1, "header_row is empty"

    target = _normalize_header(param_name)
    for i, h in enumerate(header_row):
        if _normalize_header(h) == target:
            return True, i, "matched"

    return False, -1, "param_name '{}' not found in headers".format(param_name)


class PSN_Excel_Loadout_Reader:
    """Extracts a specific parameter value from a selected loadout row."""

    _header_cache = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "row_data": ("LIST", {"default": []}),
                "param_name": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "header_row": ("LIST", {"default": []}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("value", "type_hint")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, row_data, param_name, header_row=None):
        """
        Extract the value for param_name from row_data.

        Args:
            row_data: list of strings (the selected row).
            param_name: string, the parameter name.
            header_row: optional list of strings (column headers).
                        If empty/None, uses the first row of row_data as header.

        Returns:
            (value: str, type_hint: str)
        """
        # Determine header row and data row
        headers = None
        data_row = row_data

        if header_row and len(header_row) > 0:
            headers = list(header_row)
        elif row_data and len(row_data) > 0:
            # Check if row_data is a list of lists (first row is header)
            if isinstance(row_data[0], (list, tuple)):
                headers = list(row_data[0])
                data_row = list(row_data[1]) if len(row_data) > 1 else []
            else:
                # row_data is a flat list, so we can't use first row as header
                # unless we have a separate header_row
                return ("", _TYPE_STRING)

        if headers is None:
            return ("", _TYPE_STRING)

        # Find column index
        found, col_idx, reason = _find_column_index(headers, param_name)
        if not found:
            return ("", _TYPE_STRING)

        # Get value from data_row
        if not isinstance(data_row, (list, tuple)) or col_idx >= len(data_row):
            return ("", _TYPE_STRING)

        raw_value = data_row[col_idx]
        type_hint, value_str = _cast_value(raw_value)
        return (value_str, type_hint)


NODE_CLASS_MAPPINGS = {
    "PSN_Excel_Loadout_Reader": PSN_Excel_Loadout_Reader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Excel_Loadout_Reader": "PSN Excel Loadout Reader",
}
