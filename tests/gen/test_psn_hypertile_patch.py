"""Tests for psn_nodes.gen.psn_hypertile_patch."""

import json
import math

from psn_nodes.gen.psn_hypertile_patch import (
    PSN_HyperTile_Patch,
    validate_tile_size,
    compute_tiling_plan,
    build_patch_descriptor,
)


def test_validate_tile_size_valid():
    ok, reason, val = validate_tile_size(64)
    assert ok is True
    assert reason == "ok"
    assert val == 64


def test_validate_tile_size_not_power_of_two():
    ok, reason, val = validate_tile_size(48)
    assert ok is False
    assert "power of two" in reason
    assert val is None


def test_validate_tile_size_too_small():
    ok, reason, val = validate_tile_size(4)
    assert ok is False
    assert ">= 8" in reason


def test_validate_tile_size_too_large():
    ok, reason, val = validate_tile_size(8192)
    assert ok is False
    assert "<= 4096" in reason


def test_validate_tile_size_non_integer():
    ok, reason, val = validate_tile_size(64.0)
    assert ok is False
    assert "integer" in reason


def test_validate_tile_size_bool_rejected():
    ok, reason, val = validate_tile_size(True)
    assert ok is False
    assert "integer" in reason


def test_compute_tiling_plan_basic():
    plan = compute_tiling_plan(1024, 1024, 64)
    assert plan["width"] == 1024
    assert plan["height"] == 1024
    assert plan["tile_size"] == 64
    assert len(plan["levels"]) >= 1
    # Level 0: tile_size=64, tiles_w=16, tiles_h=16, tiles=256
    assert plan["levels"][0]["tile_size"] == 64
    assert plan["levels"][0]["tiles_w"] == 16
    assert plan["levels"][0]["tiles_h"] == 16
    assert plan["levels"][0]["tiles"] == 256
    assert plan["total_tiles"] >= 256
    assert plan["estimated_memory_factor"] <= 1.0


def test_compute_tiling_plan_memory_reduction():
    # For a 1024x1024 image with tile_size=64, memory factor should be < 1.0
    plan = compute_tiling_plan(1024, 1024, 64)
    assert plan["estimated_memory_factor"] < 1.0
    # Factor should be roughly 64 / (1024*1024) = 64/1048576 ≈ 0.000061
    expected = 64 / (1024 * 1024)
    assert abs(plan["estimated_memory_factor"] - expected) < 0.001


def test_compute_tiling_plan_small_image():
    # Image smaller than tile: should still produce a valid plan
    plan = compute_tiling_plan(32, 32, 64)
    assert plan["levels"][0]["tiles_w"] == 1
    assert plan["levels"][0]["tiles_h"] == 1
    assert plan["levels"][0]["tiles"] == 1


def test_compute_tiling_plan_invalid_dimensions():
    try:
        compute_tiling_plan(0, 1024, 64)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_build_patch_descriptor_valid():
    desc = build_patch_descriptor(1024, 1024, 64)
    assert desc["ok"] is True
    assert desc["patch_type"] == "hyper_tile_attention"
    assert desc["plan"]["total_tiles"] > 0
    # Should be JSON-serialisable
    json.dumps(desc)


def test_build_patch_descriptor_invalid_tile():
    desc = build_patch_descriptor(1024, 1024, 48)
    assert desc["ok"] is False
    assert "power of two" in desc["reason"]
    assert desc["plan"] is None


def test_node_run_valid():
    node = PSN_HyperTile_Patch()
    valid, plan_json, mem_factor, total_tiles = node.run(1024, 1024, 64)
    assert valid is True
    desc = json.loads(plan_json)
    assert desc["ok"] is True
    assert mem_factor < 1.0
    assert total_tiles > 0


def test_node_run_invalid_tile():
    node = PSN_HyperTile_Patch()
    valid, plan_json, mem_factor, total_tiles = node.run(1024, 1024, 48)
    assert valid is False
    desc = json.loads(plan_json)
    assert desc["ok"] is False
    assert total_tiles == 0


def test_node_run_invalid_dimensions():
    node = PSN_HyperTile_Patch()
    valid, plan_json, mem_factor, total_tiles = node.run(0, 1024, 64)
    assert valid is False
    desc = json.loads(plan_json)
    assert desc["ok"] is False


def test_node_run_large_resolution():
    node = PSN_HyperTile_Patch()
    valid, plan_json, mem_factor, total_tiles = node.run(4096, 4096, 128)
    assert valid is True
    desc = json.loads(plan_json)
    assert desc["ok"] is True
    assert mem_factor < 1.0
    assert total_tiles > 0
    # Memory factor for 4096x4096 with tile 128: 128 / (4096*4096) ≈ 7.6e-6
    expected = 128 / (4096 * 4096)
    assert abs(mem_factor - expected) < 0.0001


def test_node_run_with_overlap():
    node = PSN_HyperTile_Patch()
    valid, plan_json, mem_factor, total_tiles = node.run(1024, 1024, 64, overlap_ratio=0.1)
    assert valid is True
    desc = json.loads(plan_json)
    assert desc["ok"] is True
