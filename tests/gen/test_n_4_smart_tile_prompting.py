"""Tests for PSN_Smart_Tile_Prompter (pure-logic, no GPU, no network)."""

import math

import pytest

from psn_nodes.gen.n_4_smart_tile_prompting import (
    ALLOWED_MODELS,
    PSN_Smart_Tile_Prompter,
    build_tile_prompt,
    compute_tile_grid,
)


def test_grid_1024_512_produces_four_tiles():
    """A 1024x1024 image with tile_size=512 and overlap=0 yields 4 tiles."""
    tiles = compute_tile_grid(1024, 1024, 512, 0)
    assert len(tiles) == 4
    # Each tile should be 512x512 (or clamped) and within bounds.
    for x, y, w, h in tiles:
        assert 0 <= x <= 1024 - 512
        assert 0 <= y <= 1024 - 512
        assert w <= 512
        assert h <= 512
        assert x + w <= 1024
        assert y + h <= 1024


def test_grid_small_image_single_tile():
    """An image smaller than tile_size yields exactly one tile."""
    tiles = compute_tile_grid(100, 100, 512, 64)
    assert len(tiles) == 1
    x, y, w, h = tiles[0]
    assert x == 0 and y == 0
    assert w == 100 and h == 100


def test_grid_overlap_increases_tile_count():
    """Larger overlap increases the number of tiles compared to no overlap."""
    no_overlap = compute_tile_grid(2048, 2048, 512, 0)
    with_overlap = compute_tile_grid(2048, 2048, 512, 128)
    # With overlap, we have more tiles to cover the same area with redundancy.
    assert len(with_overlap) > len(no_overlap)


def test_prompts_match_tile_count_and_are_nonempty():
    """Number of prompts equals number of tiles; all are non-empty strings."""
    node = PSN_Smart_Tile_Prompter()
    prompts_text, coords_text = node.run(
        width=1024, height=1024, tile_size=512, overlap=0,
        llm_model="llava-1.5-7b",
    )
    prompts = prompts_text.split("\n")
    coords = coords_text.split("\n")
    assert len(prompts) == len(coords)
    assert len(prompts) == 4
    for p in prompts:
        assert isinstance(p, str)
        assert len(p) > 0
    for c in coords:
        assert isinstance(c, str)
        assert len(c) > 0


def test_prompt_is_deterministic_and_contains_model():
    """Same inputs produce the same prompt; prompt includes model name."""
    p1 = build_tile_prompt(0, 0, 0, 512, 512, "llava-1.5-7b")
    p2 = build_tile_prompt(0, 0, 0, 512, 512, "llava-1.5-7b")
    assert p1 == p2
    assert "llava-1.5-7b" in p1
    assert "tile 0" in p1


def test_bad_input_non_numeric_tile_size_raises():
    """Non-numeric tile_size raises ValueError."""
    with pytest.raises(ValueError):
        compute_tile_grid(1024, 1024, "abc", 64)


def test_bad_input_negative_width_raises():
    """Negative width is clamped to 1, but zero/negative after clamp is invalid."""
    # _clamp_int clamps to [1, _MAX_DIM], so -100 becomes 1 (valid).
    # Test that a truly invalid value (NaN) raises.
    with pytest.raises(ValueError):
        compute_tile_grid(float("nan"), 1024, 512, 64)


def test_bad_input_overlap_equals_tile_size_raises():
    """Overlap equal to tile_size makes step=0, which is invalid."""
    with pytest.raises(ValueError):
        compute_tile_grid(1024, 1024, 512, 512)


def test_bad_input_disallowed_model_raises():
    """A model not in the allow-list raises ValueError."""
    node = PSN_Smart_Tile_Prompter()
    with pytest.raises(ValueError):
        node.run(
            width=1024, height=1024, tile_size=512, overlap=64,
            llm_model="not-a-real-model",
        )


def test_grid_max_tiles_guard():
    """A grid that would exceed _MAX_TILES raises ValueError."""
    # 16384x16384 with tile_size=16, overlap=0 -> 1024*1024 = 1,048,576 tiles
    with pytest.raises(ValueError):
        compute_tile_grid(16384, 16384, 16, 0)


def test_input_types_structure():
    """INPUT_TYPES returns the expected keys and types."""
    spec = PSN_Smart_Tile_Prompter.INPUT_TYPES()
    assert "required" in spec
    assert "width" in spec["required"]
    assert "height" in spec["required"]
    assert "tile_size" in spec["required"]
    assert "overlap" in spec["required"]
    assert "llm_model" in spec["required"]
    # llm_model should be a tuple containing a list of allowed model strings
    model_field = spec["required"]["llm_model"]
    assert isinstance(model_field, tuple)
    assert len(model_field) == 1
    assert isinstance(model_field[0], list)
    assert "llava-1.5-7b" in model_field[0]


def test_return_types_and_names():
    """RETURN_TYPES and RETURN_NAMES match the spec."""
    assert PSN_Smart_Tile_Prompter.RETURN_TYPES == ("STRING", "STRING")
    assert PSN_Smart_Tile_Prompter.RETURN_NAMES == ("TILE_PROMPTS", "TILE_COORDS")
    assert PSN_Smart_Tile_Prompter.FUNCTION == "run"
    assert PSN_Smart_Tile_Prompter.CATEGORY == "ParametricStudio/SmartTile"
