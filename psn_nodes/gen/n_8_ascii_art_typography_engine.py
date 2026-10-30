"""
PSN ASCII Art & Typography Engine (pure-logic, secure-by-design).

This module implements the *logic* of the ASCII Art & Typography Engine without
any GPU, torch, ComfyUI, Pillow, numpy, file, network, or OS access.

Because the spec requires rendering images (Pillow/numpy) and reading image
tensors, which are not allowed here, the nodes operate on *plain values*:
  - PSN_ASCII_ImageToASCII: takes a 2D grid of luminance values (as a JSON
    string of a list of lists of floats in [0.0, 1.0]) plus width/character_set/
    invert, and returns the ASCII string plus a "preview" grid (a JSON string of
    a list of lists of floats in [0.0, 1.0]) that a downstream renderer could
    rasterize.
  - PSN_Typography_ArtisticText: takes text/font/size/effect/color and returns
    a *layout description* (a JSON string of a dict) describing how the text
    should be rendered (dimensions, effect parameters, color, per-character
    offsets for shadow/outline/gradient). No actual pixels are produced.

All inputs are validated; bad input raises ValueError with a clear message.
"""

import json

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/ASCII"

# Character sets for ASCII conversion.
CHAR_SETS = {
    "standard": "@%#*+=-:. ",
    "binary": "10",
    "unicode": "█▓▒░ ",
}

EFFECTS = ["shadow", "outline", "gradient"]


def _validate_grid(grid, width):
    """Validate that grid is a list of lists of numbers in [0,1] and width matches."""
    if not isinstance(grid, list) or len(grid) == 0:
        raise ValueError("grid must be a non-empty list of rows")
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise ValueError("width must be a positive integer")
    for r, row in enumerate(grid):
        if not isinstance(row, list):
            raise ValueError(f"grid row {r} must be a list")
        if len(row) != width:
            raise ValueError(f"grid row {r} has length {len(row)}, expected {width}")
        for c, v in enumerate(row):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(f"grid[{r}][{c}] must be a number")
            if v < 0.0 or v > 1.0:
                raise ValueError(f"grid[{r}][{c}] must be in [0,1], got {v}")
    return grid


def _luminance_to_char(lum, char_set, invert):
    """Map a luminance value in [0,1] to a character from char_set.

    By default, higher luminance (brighter) maps to denser characters.
    If invert is True, the mapping is reversed.
    """
    n = len(char_set)
    if n == 1:
        return char_set[0]
    # lum in [0,1]; index 0 = darkest char, index n-1 = brightest char.
    # We want bright -> dense. So index = int(lum * (n-1) + 0.5)
    idx = int(lum * (n - 1) + 0.5)
    idx = max(0, min(n - 1, idx))
    if invert:
        idx = n - 1 - idx
    return char_set[idx]


def _build_preview_grid(grid, width, char_set, invert):
    """Build a preview grid where each cell is the normalized density of the
    chosen character (0.0 for lightest, 1.0 for densest), so a renderer can
    draw it. This is a pure-logic stand-in for the preview image."""
    n = len(char_set)
    preview = []
    for row in grid:
        prow = []
        for v in row:
            idx = int(v * (n - 1) + 0.5)
            idx = max(0, min(n - 1, idx))
            if invert:
                idx = n - 1 - idx
            # density: index / (n-1) so densest char = 1.0
            density = idx / (n - 1) if n > 1 else 0.0
            prow.append(density)
        preview.append(prow)
    return preview


def _parse_color(color):
    """Validate a color string. Accepts '#RRGGBB' or '#RGB' or named 'black'/'white'/'red'/'green'/'blue'/'transparent'.
    Returns a normalized hex string or the named token."""
    if not isinstance(color, str) or not color:
        raise ValueError("color must be a non-empty string")
    c = color.strip().lower()
    named = {"black", "white", "red", "green", "blue", "transparent"}
    if c in named:
        return c
    if c.startswith("#"):
        hexpart = c[1:]
        if len(hexpart) == 3 or len(hexpart) == 6:
            if all(ch in "0123456789abcdef" for ch in hexpart):
                return c
        raise ValueError(f"invalid hex color: {color}")
    raise ValueError(f"invalid color: {color}")


def _build_layout(text, font, size, effect, color):
    """Build a layout description dict for the artistic text.

    Returns a dict with keys: text, font, size, effect, color, width, height,
    and effect-specific parameters (shadow_offset, outline_width, gradient_stops).
    """
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not isinstance(font, str) or not font:
        raise ValueError("font must be a non-empty string")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError("size must be a positive integer")
    if effect not in EFFECTS:
        raise ValueError(f"effect must be one of {EFFECTS}")
    color = _parse_color(color)

    # Approximate layout: assume monospace-ish metrics.
    char_w = max(1, size // 2)
    char_h = size
    lines = text.split("\n")
    max_line_len = max((len(line) for line in lines), default=0)
    width = max(1, max_line_len * char_w)
    height = max(1, len(lines) * char_h)

    layout = {
        "text": text,
        "font": font,
        "size": size,
        "effect": effect,
        "color": color,
        "width": width,
        "height": height,
        "lines": lines,
    }

    if effect == "shadow":
        layout["shadow_offset"] = (max(1, size // 8), max(1, size // 8))
        layout["shadow_color"] = "black"
    elif effect == "outline":
        layout["outline_width"] = max(1, size // 16)
        layout["outline_color"] = "black"
    elif effect == "gradient":
        # Gradient from color to a lighter variant; we just record stops.
        layout["gradient_stops"] = [color, "white"]
        layout["gradient_direction"] = "vertical"

    return layout


class PSN_ASCII_ImageToASCII:
    """Convert a 2D luminance grid to an ASCII art string and a preview grid.

    Pure-logic stand-in for the image-to-ASCII node. The 'image' input is
    represented as a JSON string of a list of lists of floats in [0,1]
    (luminance). The 'preview_image' output is a JSON string of a list of
    lists of floats in [0,1] representing the density of each ASCII character,
    suitable for a downstream renderer.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "grid": ("STRING", {"default": "[]", "multiline": True}),
                "width": ("INT", {"default": 80, "min": 1, "max": 4096}),
                "character_set": (list(CHAR_SETS.keys()),),
                "invert": ("BOOLEAN", {"default": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("ascii_string", "preview_grid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, grid, width, character_set, invert):
        if character_set not in CHAR_SETS:
            raise ValueError(f"character_set must be one of {list(CHAR_SETS.keys())}")
        # Parse grid from JSON string.
        if not isinstance(grid, str):
            raise ValueError("grid must be a JSON string")
        try:
            grid_data = json.loads(grid)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"grid must be valid JSON list of lists: {e}")
        _validate_grid(grid_data, width)
        char_set = CHAR_SETS[character_set]

        ascii_lines = []
        for row in grid_data:
            line = "".join(_luminance_to_char(v, char_set, invert) for v in row)
            ascii_lines.append(line)
        ascii_string = "\n".join(ascii_lines)

        preview = _build_preview_grid(grid_data, width, char_set, invert)
        # Serialize preview grid to a JSON string for transport.
        preview_str = json.dumps(preview)
        return (ascii_string, preview_str)


class PSN_Typography_ArtisticText:
    """Build a layout description for artistic text rendering.

    Pure-logic stand-in for the artistic text node. Returns a JSON string
    describing the layout (dimensions, effect parameters, color) that a
    downstream renderer (Pillow) would use to actually draw the text.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "Hello", "multiline": True}),
                "font": ("STRING", {"default": "monospace"}),
                "size": ("INT", {"default": 24, "min": 1, "max": 4096}),
                "effect": (EFFECTS,),
                "color": ("STRING", {"default": "#000000"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("layout_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, text, font, size, effect, color):
        layout = _build_layout(text, font, size, effect, color)
        return (json.dumps(layout),)


NODE_CLASS_MAPPINGS = {
    "PSN_ASCII_ImageToASCII": PSN_ASCII_ImageToASCII,
    "PSN_Typography_ArtisticText": PSN_Typography_ArtisticText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ASCII_ImageToASCII": "ASCII Image To ASCII",
    "PSN_Typography_ArtisticText": "Typography Artistic Text",
}
