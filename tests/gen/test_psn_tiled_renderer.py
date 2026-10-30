"""Tests for psn_nodes.gen.psn_tiled_renderer."""

import pytest
from psn_nodes.gen.psn_tiled_renderer import (
    PSN_Tiled_Renderer,
    compute_tile_grid,
    stitch_tiles,
    _validate_image,
    _validate_positive_int,
    _validate_non_negative_int,
)


def _make_image(h, w, ch=3, fill=0.5):
    return [[[fill] * ch for _ in range(w)] for _ in range(h)]


def test_compute_tile_grid_basic():
    # 100x100 image, tile_size=50, overlap=10 -> step=40
    tiles = compute_tile_grid(100, 100, 50, 10)
    # Row starts: 0, 40, 80 (80+50=130>=100 so stop)
    # Col starts: 0, 40, 80
    # Last tile clamped: at 80, size = min(50, 100-80)=20
    assert len(tiles) == 9
    # First tile
    assert tiles[0] == (0, 0, 50, 50)
    # Last tile in row 0
    assert tiles[2] == (0, 80, 50, 20)
    # Last tile overall
    assert tiles[8] == (80, 80, 20, 20)


def test_compute_tile_grid_no_overlap():
    tiles = compute_tile_grid(100, 100, 50, 0)
    # step=50, starts: 0, 50
    assert len(tiles) == 4
    assert tiles[0] == (0, 0, 50, 50)
    assert tiles[3] == (50, 50, 50, 50)


def test_compute_tile_grid_single_tile():
    tiles = compute_tile_grid(30, 30, 50, 10)
    assert len(tiles) == 1
    assert tiles[0] == (0, 0, 30, 30)


def test_stitch_tiles_no_overlap():
    image = _make_image(100, 100, 3, 0.5)
    tiles = compute_tile_grid(100, 100, 50, 0)
    # Create tile images with distinct values per tile.
    tile_images = []
    for i, (rs, cs, th, tw) in enumerate(tiles):
        tile = [[[float(i)] * 3 for _ in range(tw)] for _ in range(th)]
        tile_images.append(tile)
    rendered = stitch_tiles(image, tiles, tile_images, blend_mode="none")
    # Check a pixel in the first tile region.
    assert rendered[0][0] == [0.0, 0.0, 0.0]
    # Check a pixel in the last tile region.
    assert rendered[99][99] == [3.0, 3.0, 3.0]


def test_stitch_tiles_with_overlap_blending():
    image = _make_image(100, 100, 3, 0.5)
    tiles = compute_tile_grid(100, 100, 50, 10)
    # All tiles have value 1.0, so blending should yield 1.0 everywhere.
    tile_images = []
    for (rs, cs, th, tw) in tiles:
        tile = [[[1.0] * 3 for _ in range(tw)] for _ in range(th)]
        tile_images.append(tile)
    rendered = stitch_tiles(image, tiles, tile_images, blend_mode="linear")
    # Every pixel should be 1.0.
    for r in range(100):
        for c in range(100):
            assert rendered[r][c] == [1.0, 1.0, 1.0], "pixel (%d,%d) = %s" % (r, c, rendered[r][c])


def test_node_run_valid_input():
    node = PSN_Tiled_Renderer()
    image = _make_image(100, 100, 3, 0.5)
    rendered, grid_str, reason = node.run(
        image=image,
        tile_size=50,
        overlap=10,
        model="test_model",
        blend_mode="linear",
        tile_images=None,
    )
    assert reason == "ok (no tile_images provided; returned input)"
    assert rendered is image
    assert "0, 0, 50, 50" in grid_str


def test_node_run_bad_tile_size():
    node = PSN_Tiled_Renderer()
    image = _make_image(100, 100, 3, 0.5)
    rendered, grid_str, reason = node.run(
        image=image,
        tile_size=0,
        overlap=10,
        model="test_model",
        blend_mode="linear",
    )
    assert rendered is None
    assert "tile_size" in reason


def test_node_run_overlap_ge_tile_size():
    node = PSN_Tiled_Renderer()
    image = _make_image(100, 100, 3, 0.5)
    rendered, grid_str, reason = node.run(
        image=image,
        tile_size=50,
        overlap=50,
        model="test_model",
        blend_mode="linear",
    )
    assert rendered is None
    assert "overlap must be < tile_size" in reason


def test_node_run_bad_image():
    node = PSN_Tiled_Renderer()
    rendered, grid_str, reason = node.run(
        image=[],
        tile_size=50,
        overlap=10,
        model="test_model",
        blend_mode="linear",
    )
    assert rendered is None
    assert "image" in reason


def test_node_run_bad_model():
    node = PSN_Tiled_Renderer()
    image = _make_image(100, 100, 3, 0.5)
    rendered, grid_str, reason = node.run(
        image=image,
        tile_size=50,
        overlap=10,
        model="",
        blend_mode="linear",
    )
    assert rendered is None
    assert "model" in reason


def test_validate_image_inconsistent_rows():
    image = [
        [[0.5, 0.5, 0.5], [0.5, 0.5, 0.5]],
        [[0.5, 0.5, 0.5]],  # shorter row
    ]
    ok, reason, h, w, ch = _validate_image(image)
    assert not ok
    assert "inconsistent width" in reason


def test_validate_positive_int_bool():
    ok, reason, val = _validate_positive_int(True, "test")
    assert not ok
    assert "bool" in reason


def test_validate_non_negative_int_negative():
    ok, reason, val = _validate_non_negative_int(-1, "overlap")
    assert not ok
    assert ">= 0" in reason


def test_node_run_with_tile_images():
    node = PSN_Tiled_Renderer()
    image = _make_image(100, 100, 3, 0.5)
    tiles = compute_tile_grid(100, 100, 50, 0)
    tile_images = []
    for (rs, cs, th, tw) in tiles:
        tile = [[[1.0] * 3 for _ in range(tw)] for _ in range(th)]
        tile_images.append(tile)
    rendered, grid_str, reason = node.run(
        image=image,
        tile_size=50,
        overlap=0,
        model="test_model",
        blend_mode="none",
        tile_images=tile_images,
    )
    assert reason == "ok"
    assert rendered is not None
    assert rendered[0][0] == [1.0, 1.0, 1.0]
