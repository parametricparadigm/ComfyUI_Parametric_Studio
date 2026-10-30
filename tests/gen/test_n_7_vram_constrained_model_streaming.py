"""
Tests for PSN_WeightFerry (VRAM-Constrained Model Streaming plan).

All tests use pure Python; no GPU, no torch, no file/network I/O.
"""

import json
import pytest

from psn_nodes.gen.n_7_vram_constrained_model_streaming import (
    PSN_WeightFerry,
    _parse_model_json,
    _compute_plan,
)


def _make_model_json(sizes):
    """Build a model JSON string from a list of sizes (GB)."""
    blocks = [{"name": f"block_{i}", "size_gb": s} for i, s in enumerate(sizes)]
    return json.dumps({"blocks": blocks})


class TestParseModelJson:
    def test_valid_input(self):
        mj = _make_model_json([1.0, 2.0, 3.0])
        blocks = _parse_model_json(mj)
        assert len(blocks) == 3
        assert blocks[0] == ("block_0", 1.0)
        assert blocks[2] == ("block_2", 3.0)

    def test_empty_blocks(self):
        mj = json.dumps({"blocks": []})
        blocks = _parse_model_json(mj)
        assert blocks == []

    def test_invalid_json_string(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_model_json("not json at all")

    def test_missing_blocks_key(self):
        with pytest.raises(ValueError, match="must contain a 'blocks' key"):
            _parse_model_json(json.dumps({"foo": []}))

    def test_negative_block_size(self):
        mj = json.dumps({"blocks": [{"name": "b0", "size_gb": -1.0}]})
        with pytest.raises(ValueError, match="non-negative"):
            _parse_model_json(mj)

    def test_non_numeric_size(self):
        mj = json.dumps({"blocks": [{"name": "b0", "size_gb": "big"}]})
        with pytest.raises(ValueError, match="must be a number"):
            _parse_model_json(mj)


class TestComputePlan:
    def test_all_fit(self):
        blocks = [("b0", 1.0), ("b1", 1.0)]
        plan, fits, reason = _compute_plan(blocks, vram_limit_gb=10.0, overhead_gb=1.0)
        assert fits is True
        assert plan["resident_blocks"] == [0, 1]
        assert plan["offloaded_blocks"] == []
        assert plan["transfer_order"] == []
        assert plan["estimated_peak_vram_gb"] == pytest.approx(3.0)

    def test_none_fit(self):
        blocks = [("b0", 10.0), ("b1", 10.0)]
        plan, fits, reason = _compute_plan(blocks, vram_limit_gb=5.0, overhead_gb=2.0)
        assert fits is False
        assert plan["resident_blocks"] == []
        assert plan["offloaded_blocks"] == [0, 1]
        assert plan["transfer_order"] == [0, 1]

    def test_partial_fit(self):
        # Available = 10 - 2 = 8 GB. Blocks: 3, 3, 3, 3.
        # First two fit (6 <= 8), third would make 9 > 8.
        blocks = [("b0", 3.0), ("b1", 3.0), ("b2", 3.0), ("b3", 3.0)]
        plan, fits, reason = _compute_plan(blocks, vram_limit_gb=10.0, overhead_gb=2.0)
        assert plan["resident_blocks"] == [0, 1]
        assert plan["offloaded_blocks"] == [2, 3]
        assert plan["transfer_order"] == [2, 3]
        # Peak = overhead + max(resident_total=6, largest_offloaded=3) = 2 + 6 = 8
        assert plan["estimated_peak_vram_gb"] == pytest.approx(8.0)
        assert fits is True  # 8 <= 10

    def test_overhead_exceeds_limit(self):
        blocks = [("b0", 1.0)]
        plan, fits, reason = _compute_plan(blocks, vram_limit_gb=1.0, overhead_gb=2.0)
        assert fits is False
        assert plan["resident_blocks"] == []
        assert plan["offloaded_blocks"] == [0]

    def test_single_block_fits_exactly(self):
        blocks = [("b0", 8.0)]
        plan, fits, reason = _compute_plan(blocks, vram_limit_gb=10.0, overhead_gb=2.0)
        assert fits is True
        assert plan["resident_blocks"] == [0]
        assert plan["offloaded_blocks"] == []

    def test_single_block_does_not_fit(self):
        blocks = [("b0", 9.0)]
        plan, fits, reason = _compute_plan(blocks, vram_limit_gb=10.0, overhead_gb=2.0)
        assert fits is False
        assert plan["resident_blocks"] == []
        assert plan["offloaded_blocks"] == [0]


class TestNodeRun:
    def test_basic_run(self):
        node = PSN_WeightFerry()
        mj = _make_model_json([1.0, 1.0, 1.0])
        plan_json, resident, offloaded, fits, reason = node.run(
            model_json=mj, vram_limit=5.0, overhead_gb=1.0
        )
        plan = json.loads(plan_json)
        assert resident == 3
        assert offloaded == 0
        assert fits is True
        assert plan["total_blocks"] == 3

    def test_run_with_offload(self):
        node = PSN_WeightFerry()
        # Available = 10 - 2 = 8. Blocks 4, 4, 4.
        # 4 <= 8 (resident), 4+4=8 <= 8 (resident), 4+8=12 > 8 (offloaded).
        mj = _make_model_json([4.0, 4.0, 4.0])
        plan_json, resident, offloaded, fits, reason = node.run(
            model_json=mj, vram_limit=10.0, overhead_gb=2.0
        )
        plan = json.loads(plan_json)
        assert resident == 2
        assert offloaded == 1
        assert plan["resident_blocks"] == [0, 1]
        assert plan["offloaded_blocks"] == [2]

    def test_run_bad_json(self):
        node = PSN_WeightFerry()
        with pytest.raises(ValueError):
            node.run(model_json="garbage", vram_limit=10.0)

    def test_run_negative_vram(self):
        node = PSN_WeightFerry()
        mj = _make_model_json([1.0])
        with pytest.raises(ValueError, match="vram_limit"):
            node.run(model_json=mj, vram_limit=-1.0)

    def test_run_empty_blocks(self):
        node = PSN_WeightFerry()
        mj = json.dumps({"blocks": []})
        plan_json, resident, offloaded, fits, reason = node.run(
            model_json=mj, vram_limit=10.0, overhead_gb=1.0
        )
        plan = json.loads(plan_json)
        assert resident == 0
        assert offloaded == 0
        assert fits is True
        assert plan["total_blocks"] == 0

    def test_run_zero_size_blocks(self):
        node = PSN_WeightFerry()
        mj = _make_model_json([0.0, 0.0])
        plan_json, resident, offloaded, fits, reason = node.run(
            model_json=mj, vram_limit=1.0, overhead_gb=0.5
        )
        plan = json.loads(plan_json)
        assert resident == 2
        assert offloaded == 0
        assert fits is True
