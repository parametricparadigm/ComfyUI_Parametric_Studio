"""Tests for psn_nodes.gen.n_8_ascii_art_typography_engine."""

import json
import pytest

from psn_nodes.gen.n_8_ascii_art_typography_engine import (
    PSN_ASCII_ImageToASCII,
    PSN_Typography_ArtisticText,
    _validate_grid,
    _luminance_to_char,
    _parse_color,
    _build_layout,
    CHAR_SETS,
    EFFECTS,
)


def _grid_json(rows):
    """Helper to serialize a grid to the JSON string the node expects."""
    return json.dumps(rows)


class TestASCIIImageToASCII:
    def test_basic_black_white(self):
        """A 2x2 grid of pure black (0.0) and white (1.0) should produce expected chars."""
        # standard set: "@%#*+=-:. " (10 chars). 0.0 -> index 0 = '@', 1.0 -> index 9 = ' '
        grid = [[0.0, 1.0], [1.0, 0.0]]
        node = PSN_ASCII_ImageToASCII()
        ascii_str, preview_str = node.run(_grid_json(grid), 2, "standard", False)
        lines = ascii_str.split("\n")
        assert len(lines) == 2
        # 0.0 -> '@', 1.0 -> ' '
        assert lines[0] == "@ "
        assert lines[1] == " @"

    def test_invert(self):
        """Inverting should swap the mapping."""
        grid = [[0.0, 1.0]]
        node = PSN_ASCII_ImageToASCII()
        ascii_str, _ = node.run(_grid_json(grid), 2, "standard", True)
        # With invert: 0.0 -> index 9 = ' ', 1.0 -> index 0 = '@'
        assert ascii_str == " @"

    def test_binary_charset(self):
        """Binary set '10': 0.0 -> '1', 1.0 -> '0' (index 0='1', index 1='0')."""
        grid = [[0.0, 1.0]]
        node = PSN_ASCII_ImageToASCII()
        ascii_str, _ = node.run(_grid_json(grid), 2, "binary", False)
        assert ascii_str == "10"

    def test_unicode_charset(self):
        """Unicode set '█▓▒░ ': 0.0 -> '█', 1.0 -> ' '."""
        grid = [[0.0, 1.0]]
        node = PSN_ASCII_ImageToASCII()
        ascii_str, _ = node.run(_grid_json(grid), 2, "unicode", False)
        assert ascii_str == "█ "

    def test_invalid_grid_width_mismatch(self):
        """Grid row length must match width."""
        grid = [[0.0, 1.0, 0.5]]  # length 3
        node = PSN_ASCII_ImageToASCII()
        with pytest.raises(ValueError, match="expected 2"):
            node.run(_grid_json(grid), 2, "standard", False)

    def test_invalid_grid_value_out_of_range(self):
        """Values must be in [0,1]."""
        grid = [[0.0, 1.5]]
        node = PSN_ASCII_ImageToASCII()
        with pytest.raises(ValueError, match="must be in \\[0,1\\]"):
            node.run(_grid_json(grid), 2, "standard", False)

    def test_invalid_character_set(self):
        node = PSN_ASCII_ImageToASCII()
        grid = [[0.0]]
        with pytest.raises(ValueError, match="character_set must be one of"):
            node.run(_grid_json(grid), 1, "invalid_set", False)

    def test_invalid_grid_json(self):
        node = PSN_ASCII_ImageToASCII()
        with pytest.raises(ValueError, match="grid must be valid JSON"):
            node.run("not json", 1, "standard", False)

    def test_preview_grid_density(self):
        """Preview grid should reflect character density."""
        grid = [[0.0, 1.0]]
        node = PSN_ASCII_ImageToASCII()
        _, preview_str = node.run(_grid_json(grid), 2, "standard", False)
        preview = json.loads(preview_str)
        # standard has 10 chars. 0.0 -> idx 0 -> density 0/9 = 0.0; 1.0 -> idx 9 -> density 9/9 = 1.0
        assert preview[0][0] == pytest.approx(0.0)
        assert preview[0][1] == pytest.approx(1.0)


class TestTypographyArtisticText:
    def test_basic_layout(self):
        node = PSN_Typography_ArtisticText()
        layout_str = node.run("Hello", "monospace", 24, "shadow", "#000000")[0]
        layout = json.loads(layout_str)
        assert layout["text"] == "Hello"
        assert layout["font"] == "monospace"
        assert layout["size"] == 24
        assert layout["effect"] == "shadow"
        assert layout["color"] == "#000000"
        assert layout["width"] > 0
        assert layout["height"] > 0
        assert "shadow_offset" in layout

    def test_outline_effect(self):
        node = PSN_Typography_ArtisticText()
        layout_str = node.run("Test", "sans", 32, "outline", "white")[0]
        layout = json.loads(layout_str)
        assert layout["effect"] == "outline"
        assert "outline_width" in layout
        assert layout["color"] == "white"

    def test_gradient_effect(self):
        node = PSN_Typography_ArtisticText()
        layout_str = node.run("Grad", "serif", 16, "gradient", "#ff0000")[0]
        layout = json.loads(layout_str)
        assert layout["effect"] == "gradient"
        assert "gradient_stops" in layout
        assert layout["gradient_stops"][0] == "#ff0000"

    def test_invalid_effect(self):
        node = PSN_Typography_ArtisticText()
        with pytest.raises(ValueError, match="effect must be one of"):
            node.run("Hi", "monospace", 12, "invalid_effect", "#000000")

    def test_invalid_color(self):
        node = PSN_Typography_ArtisticText()
        with pytest.raises(ValueError, match="invalid color"):
            node.run("Hi", "monospace", 12, "shadow", "notacolor")

    def test_invalid_size(self):
        node = PSN_Typography_ArtisticText()
        with pytest.raises(ValueError, match="size must be a positive integer"):
            node.run("Hi", "monospace", 0, "shadow", "#000000")

    def test_multiline_text(self):
        node = PSN_Typography_ArtisticText()
        layout_str = node.run("Line1\nLine2", "monospace", 20, "shadow", "black")[0]
        layout = json.loads(layout_str)
        assert layout["lines"] == ["Line1", "Line2"]
        assert layout["height"] == 2 * 20  # 2 lines * size 20

    def test_named_color_transparent(self):
        node = PSN_Typography_ArtisticText()
        layout_str = node.run("Hi", "monospace", 10, "shadow", "transparent")[0]
        layout = json.loads(layout_str)
        assert layout["color"] == "transparent"


class TestHelperFunctions:
    def test_validate_grid_empty(self):
        with pytest.raises(ValueError, match="non-empty"):
            _validate_grid([], 1)

    def test_validate_grid_bad_width(self):
        with pytest.raises(ValueError, match="positive integer"):
            _validate_grid([[0.0]], 0)

    def test_luminance_to_char_edges(self):
        char_set = "abc"
        assert _luminance_to_char(0.0, char_set, False) == "a"
        assert _luminance_to_char(1.0, char_set, False) == "c"
        assert _luminance_to_char(0.5, char_set, False) == "b"
        # invert
        assert _luminance_to_char(0.0, char_set, True) == "c"
        assert _luminance_to_char(1.0, char_set, True) == "a"

    def test_parse_color_hex(self):
        assert _parse_color("#ff0000") == "#ff0000"
        assert _parse_color("#F00") == "#f00"
        with pytest.raises(ValueError):
            _parse_color("#GGGGGG")

    def test_build_layout_invalid_font(self):
        with pytest.raises(ValueError, match="font must be a non-empty string"):
            _build_layout("Hi", "", 12, "shadow", "#000000")
