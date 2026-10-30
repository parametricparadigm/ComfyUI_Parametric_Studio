"""Tests for the context-aware tile refinement planning node."""

import json

import pytest

from psn_nodes.gen.n_9_context_aware_tile_refinement import (
    PSN_Context_Tile_Refine,
    compute_tile_grid,
    compute_context_window,
    blend_weight,
    check_seam_continuity,
    plan_refinement,
    _validate_tile_params,
)


def test_tile_grid_covers_image():
    """Tiles must cover the whole image without gaps or overflow."""
    tiles = compute_tile_grid(1024, 1024, 512, 64)
    assert len(tiles) > 0
    # Every tile lies within the image bounds.
    for t in tiles:
        assert t["x"] >= 0 and t["y"] >= 0
        assert t["x"] + t["w"] <= 1024
        assert t["y"] + t["h"] <= 1024
    # The grid must reach the far corners (coverage).
    max_x = max(t["x"] + t["w"] for t in tiles)
    max_y = max(t["y"] + t["h"] for t in tiles)
    assert max_x == 1024
    assert max_y == 1024


def test_tile_grid_overlap_is_respected():
    """Consecutive tiles along an axis should overlap by the requested amount."""
    tiles = compute_tile_grid(1024, 1024, 512, 64)
    # Collect the x positions of the first row.
    xs = sorted({t["x"] for t in tiles if t["y"] == 0})
    # Step should be tile_size - overlap = 448.
    for a, b in zip(xs, xs[1:]):
        assert b - a == 512 - 64


def test_context_window_clamped_to_bounds():
    """Context windows must never extend past the image edges."""
    tiles = compute_tile_grid(1024, 1024, 512, 64)
    for t in tiles:
        c = compute_context_window(t, 1024, 1024, 64)
        assert c["x"] >= 0 and c["y"] >= 0
        assert c["x"] + c["w"] <= 1024
        assert c["y"] + c["h"] <= 1024
        # Context must contain the tile itself.
        assert c["x"] <= t["x"]
        assert c["y"] <= t["y"]
        assert c["x"] + c["w"] >= t["x"] + t["w"]
        assert c["y"] + c["h"] >= t["y"] + t["h"]


def test_blend_weight_center_is_one_edges_zero():
    """Feathered weight is 1 at the centre and 0 at the edges."""
    assert blend_weight(0.5, 0.5, "cosine") == pytest.approx(1.0)
    assert blend_weight(0.0, 0.5, "cosine") == pytest.approx(0.0)
    assert blend_weight(1.0, 0.5, "cosine") == pytest.approx(0.0)
    assert blend_weight(0.5, 0.0, "cosine") == pytest.approx(0.0)
    # Linear mode.
    assert blend_weight(0.5, 0.5, "linear") == pytest.approx(1.0)
    assert blend_weight(0.0, 0.5, "linear") == pytest.approx(0.0)
    # None mode is always 1.
    assert blend_weight(0.1, 0.9, "none") == 1.0


def test_seam_continuity_detects_artifact():
    """A large jump across the seam must be flagged as a discontinuity."""
    left = [1.0, 2.0, 3.0]
    right = [1.0, 2.0, 3.0]
    ok = check_seam_continuity(left, right, tolerance=1e-3)
    assert ok["continuous"] is True
    assert ok["max_diff"] == pytest.approx(0.0)

    right_bad = [1.0, 2.0, 9.0]
    bad = check_seam_continuity(left, right_bad, tolerance=1e-3)
    assert bad["continuous"] is False
    assert bad["max_diff"] == pytest.approx(6.0)


def test_seam_continuity_length_mismatch():
    """Mismatched seam lengths are treated as a discontinuity."""
    res = check_seam_continuity([1.0, 2.0], [1.0], tolerance=1.0)
    assert res["continuous"] is False
    assert res["reason"] == "length mismatch"


def test_validate_clamps_bad_overlap():
    """overlap >= tile_size must be clamped and warned about."""
    p = _validate_tile_params(1024, 1024, 512, 600)
    assert p["overlap"] == 511
    assert any("overlap" in w for w in p["warnings"])


def test_validate_rejects_nonpositive_image():
    """Non-positive image dimensions must raise ValueError."""
    with pytest.raises(ValueError):
        _validate_tile_params(0, 1024, 512, 64)
    with pytest.raises(ValueError):
        _validate_tile_params(1024, -5, 512, 64)


def test_plan_refinement_full_structure():
    """plan_refinement returns params, tiles with context, and a count."""
    plan = plan_refinement(1024, 1024, 512, 64, blend_mode="cosine")
    assert plan["blend_mode"] == "cosine"
    assert plan["tile_count"] == len(plan["tiles"])
    assert plan["tile_count"] > 0
    for t in plan["tiles"]:
        assert "context" in t
        assert set(t["context"]) == {"x", "y", "w", "h"}


def test_node_run_returns_valid_json_and_seam():
    """The node run() returns parseable JSON and a seam verdict."""
    node = PSN_Context_Tile_Refine()
    plan_json, count, continuous, reason = node.run(
        width=1024, height=1024, tile_size=512, overlap=64,
        blend_mode="cosine", seam_tolerance=1e-3,
        left_seam="1,2,3", right_seam="1,2,3",
    )
    plan = json.loads(plan_json)
    assert plan["tile_count"] == count
    assert continuous is True
    assert reason == "ok"


def test_node_run_bad_seam_input():
    """Non-numeric seam input must yield continuous=False with a reason."""
    node = PSN_Context_Tile_Refine()
    plan_json, count, continuous, reason = node.run(
        width=512, height=512, tile_size=256, overlap=32,
        blend_mode="linear", left_seam="1,2,3", right_seam="1,foo,3",
    )
    assert continuous is False
    assert "seam" in reason.lower()
    # Plan is still produced and valid.
    assert json.loads(plan_json)["tile_count"] == count


def test_node_run_unknown_blend_mode_falls_back():
    """An unknown blend mode is normalised to cosine with a warning."""
    node = PSN_Context_Tile_Refine()
    plan_json, count, continuous, reason = node.run(
        width=256, height=256, tile_size=128, overlap=16,
        blend_mode="bogus", left_seam="0", right_seam="0",
    )
    plan = json.loads(plan_json)
    assert plan["blend_mode"] == "cosine"
    assert any("blend_mode" in w for w in plan["params"]["warnings"])
    assert continuous is True
