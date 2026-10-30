"""PSN_Sheet_Parameter_Loop: iterate over rows of a sheet matrix and build parameter dicts.

This module implements the pure-logic part of a Google-Sheet parameter loop. It does NOT
open any network connection, read files, or touch the OS. The `matrix` input is expected
to be a plain Python list of rows (each row a list of cell values) as produced by a
loader node; the first row is treated as the header. The node slices rows from
`start_row` to `end_row` (inclusive) and converts each into a dict keyed by the header.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Sheet"


class PSN_Sheet_Parameter_Loop:
    """Iterate through rows in a sheet matrix to generate multiple parameter sets."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "matrix": ("LIST", {"default": []}),
                "start_row": ("INT", {"default": 1, "min": 0, "max": 10**9, "step": 1}),
                "end_row": ("INT", {"default": 10, "min": 0, "max": 10**9, "step": 1}),
            },
            "optional": {
                "header_row": ("INT", {"default": 0, "min": 0, "max": 10**9, "step": 1}),
            },
        }

    RETURN_TYPES = ("LIST", "INT")
    RETURN_NAMES = ("param_sets", "count")
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _coerce_row(row):
        """Normalize a row into a list of strings. Accepts list/tuple or a single scalar."""
        if row is None:
            return []
        if isinstance(row, (list, tuple)):
            return [("" if c is None else str(c)) for c in row]
        return [str(row)]

    @classmethod
    def run(cls, matrix, start_row, end_row, header_row=0):
        # Validate matrix is a list of rows
        if not isinstance(matrix, (list, tuple)):
            raise ValueError("matrix must be a list of rows")

        # Normalize rows
        rows = [cls._coerce_row(r) for r in matrix]

        # Determine header
        if header_row < 0 or header_row >= len(rows):
            raise ValueError("header_row out of range")
        header = rows[header_row]

        # Determine data row range (inclusive), clamped to available rows
        first_data = header_row + 1
        last_data = len(rows) - 1

        if start_row < first_data:
            start_row = first_data
        if end_row > last_data:
            end_row = last_data

        param_sets = []
        if start_row <= end_row:
            for i in range(start_row, end_row + 1):
                row = rows[i]
                d = {}
                for j, key in enumerate(header):
                    if j < len(row):
                        d[key] = row[j]
                    else:
                        d[key] = ""
                param_sets.append(d)

        return (param_sets, len(param_sets))


NODE_CLASS_MAPPINGS = {
    "PSN_Sheet_Parameter_Loop": PSN_Sheet_Parameter_Loop,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Sheet_Parameter_Loop": "Sheet Parameter Loop",
}
