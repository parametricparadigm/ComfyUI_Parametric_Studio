"""
PSN_CSV_Batch_Reader: A pure-logic node for parsing CSV text into batch items.

This node does NOT read files from disk. Instead, it accepts CSV content as a
STRING input (which can be provided by a file-reading node in ComfyUI, or
pasted directly). It parses the CSV using Python's standard `csv` module and
outputs the current row's data.

Inputs:
    csv_text (STRING): The full CSV content as a string.
    row_index (INT): The 0-based index of the row to retrieve.

Outputs:
    prompt (STRING): The value from the 'prompt' column (or first column if no 'prompt' header).
    params (DICT): A dictionary of all other columns in the row, with values as strings.
    has_next (BOOLEAN): True if there is a row after the current one.
    row_count (INT): Total number of data rows in the CSV.
    error (STRING): Empty string if successful, otherwise an error message.

Security: No file I/O, no network, no eval/exec. Pure string parsing.
"""

import csv
import io
import json

CAT = "ParametricStudio/CSV"


class PSN_CSV_Batch_Reader:
    """Reads a CSV string and returns the current row's prompt and parameters."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "csv_text": ("STRING", {"multiline": True, "default": "prompt,seed\nHello,42\nWorld,43"}),
                "row_index": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "DICT", "BOOLEAN", "INT", "STRING")
    RETURN_NAMES = ("prompt", "params", "has_next", "row_count", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, csv_text, row_index):
        # Validate input
        if not isinstance(csv_text, str):
            return ("", {}, False, 0, "csv_text must be a string")
        if not isinstance(row_index, int):
            return ("", {}, False, 0, "row_index must be an integer")
        if row_index < 0:
            return ("", {}, False, 0, "row_index must be non-negative")

        # Parse CSV
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            rows = list(reader)
        except csv.Error as e:
            return ("", {}, False, 0, f"CSV parse error: {e}")
        except Exception as e:
            return ("", {}, False, 0, f"Unexpected error: {e}")

        row_count = len(rows)

        if row_count == 0:
            return ("", {}, False, 0, "CSV has no data rows")

        if row_index >= row_count:
            return ("", {}, False, row_count, f"row_index {row_index} out of range (0-{row_count - 1})")

        current_row = rows[row_index]

        # Extract prompt: prefer 'prompt' column, else first column
        prompt = ""
        params = {}

        if "prompt" in current_row:
            prompt = current_row["prompt"] or ""
            for key, value in current_row.items():
                if key != "prompt":
                    params[key] = value if value is not None else ""
        else:
            # Use first column as prompt
            if current_row:
                first_key = next(iter(current_row))
                prompt = current_row[first_key] or ""
                for key, value in current_row.items():
                    if key != first_key:
                        params[key] = value if value is not None else ""

        has_next = row_index < row_count - 1

        return (prompt, params, has_next, row_count, "")


NODE_CLASS_MAPPINGS = {
    "PSN_CSV_Batch_Reader": PSN_CSV_Batch_Reader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CSV_Batch_Reader": "CSV Batch Reader",
}
