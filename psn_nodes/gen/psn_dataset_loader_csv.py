"""PSN_Dataset_Loader_CSV: pure-logic CSV parsing for batch processing.

This module implements a ComfyUI-style custom node that parses CSV *text*
into structured rows and column names. Per the project rules, it performs NO
file or OS access: the caller supplies the CSV content as a plain string
(`csv_text`), and the node validates/parses it in memory. The `file_path`
input is accepted for interface compatibility but is only used to derive a
safe, redacted label for diagnostics; it is never opened.

Only the Python standard library is used (csv, io, re). No torch, no ComfyUI
imports, no network, no subprocess, no eval/exec, no dunder tricks.
"""

import csv
import io
import re

CAT = "ParametricStudio/Data"

# Maximum number of characters we will parse, to bound memory use.
MAX_CSV_CHARS = 1_000_000
# Maximum number of rows we will keep, to bound memory use.
MAX_ROWS = 100_000
# Maximum number of columns we will keep, to bound memory use.
MAX_COLUMNS = 1_000

# Characters allowed in a delimiter (single char, or a small set).
_DELIM_ALLOWED = set(",;\t|")


def _redact_path(file_path):
    """Return a short, safe label derived from a path without exposing it.

    We keep only the final path segment's stem (no extension) and truncate it,
    so diagnostics do not leak full filesystem locations.
    """
    if not isinstance(file_path, str):
        return "unknown"
    # Take the last segment after common separators.
    segment = re.split(r"[\\/]+", file_path.strip())[-1]
    # Drop an extension if present.
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", segment)
    if not stem:
        return "unknown"
    return stem[:48]


def _validate_delimiter(delimiter):
    """Validate the delimiter string. Returns (ok, normalized, reason)."""
    if not isinstance(delimiter, str):
        return False, ",", "delimiter must be a string"
    if len(delimiter) == 0:
        return False, ",", "delimiter must not be empty"
    if len(delimiter) > 1:
        return False, ",", "delimiter must be a single character"
    if delimiter not in _DELIM_ALLOWED:
        return False, ",", "delimiter must be one of , ; tab |"
    return True, delimiter, "ok"


def parse_csv_text(csv_text, delimiter=",", header_row=True):
    """Parse CSV text into (columns, rows, reason).

    Returns:
        columns: list[str] of column names (from header row, or generated).
        rows: list[list[str]] of data rows (each row is a list of strings).
        reason: human-readable status string.
    """
    if not isinstance(csv_text, str):
        return [], [], "csv_text must be a string"

    if len(csv_text) > MAX_CSV_CHARS:
        return [], [], "csv_text exceeds maximum allowed size"

    ok, delim, why = _validate_delimiter(delimiter)
    if not ok:
        return [], [], why

    # Use a StringIO so csv module can read from the string.
    try:
        reader = csv.reader(io.StringIO(csv_text), delimiter=delim)
    except Exception as exc:  # pragma: no cover - defensive
        return [], [], "failed to initialize CSV reader: %s" % type(exc).__name__

    all_rows = []
    for row in reader:
        all_rows.append([cell if cell is not None else "" for cell in row])
        if len(all_rows) > MAX_ROWS:
            return [], [], "too many rows (exceeds limit)"

    if not all_rows:
        return [], [], "no data found in csv_text"

    # Determine column count from the widest row.
    max_cols = max(len(r) for r in all_rows)
    if max_cols > MAX_COLUMNS:
        return [], [], "too many columns (exceeds limit)"

    if header_row:
        header = all_rows[0]
        # Pad header to max_cols with generated names.
        columns = list(header)
        for i in range(len(columns), max_cols):
            columns.append("col_%d" % i)
        # Truncate header to max_cols.
        columns = columns[:max_cols]
        # Ensure unique, non-empty column names.
        seen = {}
        final_columns = []
        for i, name in enumerate(columns):
            base = name.strip() if isinstance(name, str) else ("col_%d" % i)
            if not base:
                base = "col_%d" % i
            if base in seen:
                seen[base] += 1
                base = "%s_%d" % (base, seen[base] - 1)
            else:
                seen[base] = 1
            final_columns.append(base)
        columns = final_columns
        data_rows = all_rows[1:]
    else:
        columns = ["col_%d" % i for i in range(max_cols)]
        data_rows = all_rows

    # Normalize each data row to exactly max_cols cells.
    normalized_rows = []
    for r in data_rows:
        if len(r) < max_cols:
            r = r + [""] * (max_cols - len(r))
        elif len(r) > max_cols:
            r = r[:max_cols]
        normalized_rows.append(r)

    return columns, normalized_rows, "ok"


class PSN_Dataset_Loader_CSV:
    """Parse CSV text into structured rows and column names.

    Inputs:
        file_path: STRING - a label for the source (not opened).
        csv_text: STRING - the actual CSV content to parse.
        delimiter: STRING - single character delimiter (default ",").
        header_row: BOOLEAN - whether the first row is a header.

    Outputs:
        rows: LIST[STRING] - list of rows, each row is a list of strings.
        columns: LIST[STRING] - list of column names.
        reason: STRING - status/diagnostic message.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "data.csv"}),
                "csv_text": ("STRING", {"default": "", "multiline": True}),
                "delimiter": ("STRING", {"default": ","}),
                "header_row": ("BOOLEAN", {"default": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST", "LIST", "STRING")
    RETURN_NAMES = ("rows", "columns", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, file_path, csv_text, delimiter, header_row):
        columns, rows, reason = parse_csv_text(csv_text, delimiter, header_row)
        # Prepend a short, redacted source label to the reason for context.
        label = _redact_path(file_path)
        full_reason = "[%s] %s" % (label, reason)
        return (rows, columns, full_reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Dataset_Loader_CSV": PSN_Dataset_Loader_CSV,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Dataset_Loader_CSV": "PSN Dataset Loader CSV",
}
