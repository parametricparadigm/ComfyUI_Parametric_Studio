"""PSN_GSheet_Cell_Selector: Extracts a specific value from a loaded sheet matrix.

This node indexes a 2D list (matrix) using 0-based row and column indices.
It returns the cell content as a string, or an empty string if the indices
are out of bounds or the cell is empty/None.

Pure logic only: no file I/O, no network, no GPU.
"""

import json

CAT = "ParametricStudio/GSheet"


class PSN_GSheet_Cell_Selector:
    """Extracts a specific value from the loaded sheet matrix."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "matrix": ("LIST", {"default": []}),
                "row": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "col": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("value",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, matrix, row, col):
        """
        Indexes the matrix at [row][col] and returns the value as a string.
        Returns empty string if out of bounds or cell is None/empty.
        """
        # Validate matrix is a list
        if not isinstance(matrix, list):
            return ("",)

        # Validate row and col are non-negative integers
        if not isinstance(row, int) or not isinstance(col, int):
            return ("",)
        if row < 0 or col < 0:
            return ("",)

        # Check row bounds
        if row >= len(matrix):
            return ("",)

        row_data = matrix[row]

        # Validate row_data is a list
        if not isinstance(row_data, list):
            return ("",)

        # Check col bounds
        if col >= len(row_data):
            return ("",)

        cell = row_data[col]

        # Handle None or empty
        if cell is None:
            return ("",)

        # Convert to string
        if isinstance(cell, str):
            return (cell,)

        # For other types, convert to string representation
        # If it's a dict or list, use JSON for consistency
        if isinstance(cell, (dict, list)):
            try:
                return (json.dumps(cell, ensure_ascii=False),)
            except (TypeError, ValueError):
                return (str(cell),)

        return (str(cell),)


NODE_CLASS_MAPPINGS = {
    "PSN_GSheet_Cell_Selector": PSN_GSheet_Cell_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_GSheet_Cell_Selector": "GSheet Cell Selector",
}
