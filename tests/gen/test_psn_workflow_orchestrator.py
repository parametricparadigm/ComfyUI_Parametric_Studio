"""Tests for PSN_Workflow_Orchestrator."""

import json
import pytest

from psn_nodes.gen.psn_workflow_orchestrator import (
    PSN_Workflow_Orchestrator,
    _validate_workflow_json,
    _compute_vram_budget,
    _split_into_batches,
)


def _make_workflow_json(segment_ids, seg_type="transform"):
    segments = [{"id": sid, "type": seg_type} for sid in segment_ids]
    return json.dumps({"segments": segments})


class TestPSNWorkflowOrchestrator:

    def test_valid_workflow_two_segments(self):
        node = PSN_Workflow_Orchestrator()
        wf = _make_workflow_json(["a", "b"])
        ids, status = node.run(wf, max_parallel=2, vram_per_instance=4.0)
        assert len(ids) == 2
        assert "inst_0_a" in ids
        assert "inst_0_b" in ids
        assert status.startswith("ok:")
        assert "2 segments" in status
        assert "1 batch" in status

    def test_valid_workflow_batching(self):
        node = PSN_Workflow_Orchestrator()
        wf = _make_workflow_json(["a", "b", "c", "d", "e"])
        ids, status = node.run(wf, max_parallel=2, vram_per_instance=2.0)
        assert len(ids) == 5
        # 5 segments / 2 per batch = 3 batches
        assert "3 batch" in status
        # First batch: inst_0_a, inst_0_b; second: inst_1_c, inst_1_d; third: inst_2_e
        assert "inst_0_a" in ids
        assert "inst_1_c" in ids
        assert "inst_2_e" in ids

    def test_invalid_json(self):
        node = PSN_Workflow_Orchestrator()
        ids, status = node.run("not valid json", max_parallel=2, vram_per_instance=4.0)
        assert ids == []
        assert status.startswith("error:")
        assert "invalid JSON" in status

    def test_empty_workflow_json(self):
        node = PSN_Workflow_Orchestrator()
        ids, status = node.run("", max_parallel=2, vram_per_instance=4.0)
        assert ids == []
        assert "empty" in status

    def test_disallowed_segment_type(self):
        node = PSN_Workflow_Orchestrator()
        wf = json.dumps({"segments": [{"id": "x", "type": "hack"}]})
        ids, status = node.run(wf, max_parallel=2, vram_per_instance=4.0)
        assert ids == []
        assert "disallowed type" in status

    def test_missing_segments_key(self):
        node = PSN_Workflow_Orchestrator()
        wf = json.dumps({"foo": "bar"})
        ids, status = node.run(wf, max_parallel=2, vram_per_instance=4.0)
        assert ids == []
        assert "'segments' or 'nodes'" in status

    def test_max_parallel_too_small(self):
        node = PSN_Workflow_Orchestrator()
        wf = _make_workflow_json(["a"])
        ids, status = node.run(wf, max_parallel=0, vram_per_instance=4.0)
        assert ids == []
        assert "max_parallel must be >= 1" in status

    def test_vram_per_instance_zero(self):
        node = PSN_Workflow_Orchestrator()
        wf = _make_workflow_json(["a"])
        ids, status = node.run(wf, max_parallel=2, vram_per_instance=0.0)
        assert ids == []
        assert "vram_per_instance must be > 0" in status

    def test_vram_per_instance_negative(self):
        node = PSN_Workflow_Orchestrator()
        wf = _make_workflow_json(["a"])
        ids, status = node.run(wf, max_parallel=2, vram_per_instance=-1.0)
        assert ids == []
        assert "vram_per_instance must be > 0" in status

    def test_nodes_key_also_accepted(self):
        node = PSN_Workflow_Orchestrator()
        wf = json.dumps({"nodes": [{"id": "n1", "type": "load"}, {"id": "n2", "type": "save"}]})
        ids, status = node.run(wf, max_parallel=2, vram_per_instance=1.0)
        assert len(ids) == 2
        assert "inst_0_n1" in ids
        assert "inst_0_n2" in ids

    def test_single_segment_single_batch(self):
        node = PSN_Workflow_Orchestrator()
        wf = _make_workflow_json(["only"])
        ids, status = node.run(wf, max_parallel=4, vram_per_instance=8.0)
        assert ids == ["inst_0_only"]
        assert "1 batch" in status
        assert "total_vram=32.00GB" in status

    def test_max_parallel_larger_than_segments(self):
        node = PSN_Workflow_Orchestrator()
        wf = _make_workflow_json(["a", "b"])
        ids, status = node.run(wf, max_parallel=10, vram_per_instance=1.0)
        assert len(ids) == 2
        assert "1 batch" in status

    def test_validate_workflow_json_non_string(self):
        segments, err = _validate_workflow_json(12345)
        assert segments is None
        assert "must be a string" in err

    def test_compute_vram_budget_bad_type(self):
        total, err = _compute_vram_budget("two", 4.0)
        assert total is None
        assert "must be an integer" in err

    def test_split_into_batches_edge(self):
        segs = [{"id": f"s{i}", "type": "transform"} for i in range(7)]
        batches = _split_into_batches(segs, 3)
        assert len(batches) == 3
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 1
