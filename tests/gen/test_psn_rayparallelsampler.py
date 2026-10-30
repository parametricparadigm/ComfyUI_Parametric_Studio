"""
Tests for psn_nodes.gen.psn_rayparallelsampler
"""

import json

from psn_nodes.gen.psn_rayparallelsampler import (
    PSN_RayParallelSampler,
    psn_validate_config,
    psn_compute_shard_sizes,
    psn_build_work_plan,
    psn_format_payload,
    SCHEDULING_MODES,
    PAYLOAD_FORMATS,
)


def test_validate_config_valid():
    ok, errors = psn_validate_config(4, 64, 8, "round_robin", "json")
    assert ok is True
    assert errors == []


def test_validate_config_bad_workers():
    ok, errors = psn_validate_config(0, 64, 8, "round_robin", "json")
    assert ok is False
    assert any("num_workers" in e for e in errors)

    ok2, errors2 = psn_validate_config(-1, 64, 8, "round_robin", "json")
    assert ok2 is False

    ok3, errors3 = psn_validate_config(1025, 64, 8, "round_robin", "json")
    assert ok3 is False


def test_validate_config_bad_scheduling():
    ok, errors = psn_validate_config(4, 64, 8, "invalid_mode", "json")
    assert ok is False
    assert any("scheduling" in e for e in errors)


def test_validate_config_bad_payload_format():
    ok, errors = psn_validate_config(4, 64, 8, "round_robin", "xml")
    assert ok is False
    assert any("payload_format" in e for e in errors)


def test_compute_shard_sizes_even():
    sizes = psn_compute_shard_sizes(4, 64)
    assert sizes == [16, 16, 16, 16]
    assert sum(sizes) == 64


def test_compute_shard_sizes_uneven():
    sizes = psn_compute_shard_sizes(3, 10)
    assert sizes == [4, 3, 3]
    assert sum(sizes) == 10


def test_compute_shard_sizes_zero_workers():
    sizes = psn_compute_shard_sizes(0, 64)
    assert sizes == []


def test_build_work_plan_static():
    plan = psn_build_work_plan(2, 10, 4, "static")
    # chunk=4: tasks of 4,4,2
    # static: worker 0 gets first, worker 1 gets next, etc.
    assert len(plan) == 3
    assert plan[0] == {"worker": 0, "start": 0, "count": 4}
    assert plan[1] == {"worker": 1, "start": 4, "count": 4}
    assert plan[2] == {"worker": 1, "start": 8, "count": 2}
    total = sum(t["count"] for t in plan)
    assert total == 10


def test_build_work_plan_round_robin():
    plan = psn_build_work_plan(3, 10, 4, "round_robin")
    # chunk=4: tasks of 4,4,2
    # round_robin: worker 0, 1, 2
    assert len(plan) == 3
    assert plan[0] == {"worker": 0, "start": 0, "count": 4}
    assert plan[1] == {"worker": 1, "start": 4, "count": 4}
    assert plan[2] == {"worker": 2, "start": 8, "count": 2}
    total = sum(t["count"] for t in plan)
    assert total == 10


def test_build_work_plan_dynamic():
    plan = psn_build_work_plan(3, 10, 4, "dynamic")
    # dynamic: one task per worker with shard size
    sizes = psn_compute_shard_sizes(3, 10)  # [4, 3, 3]
    assert len(plan) == 3
    assert plan[0] == {"worker": 0, "start": 0, "count": 4}
    assert plan[1] == {"worker": 1, "start": 4, "count": 3}
    assert plan[2] == {"worker": 2, "start": 7, "count": 3}
    total = sum(t["count"] for t in plan)
    assert total == 10


def test_format_payload_json():
    config = {"num_workers": 2, "batch_size": 8, "items_per_task": 4, "scheduling": "static", "payload_format": "json"}
    plan = psn_build_work_plan(2, 8, 4, "static")
    payload = psn_format_payload(config, plan, "json")
    parsed = json.loads(payload)
    assert parsed["config"]["num_workers"] == 2
    assert len(parsed["plan"]) == 2


def test_format_payload_csv():
    config = {"num_workers": 2, "batch_size": 8, "items_per_task": 4, "scheduling": "static", "payload_format": "csv"}
    plan = psn_build_work_plan(2, 8, 4, "static")
    payload = psn_format_payload(config, plan, "csv")
    lines = payload.strip().split("\n")
    assert lines[0] == "worker,start,count"
    assert len(lines) == 3  # header + 2 tasks


def test_node_run_valid():
    node = PSN_RayParallelSampler()
    valid, payload, reason, task_count = node.run(4, 64, 8, "round_robin", "json")
    assert valid is True
    assert reason == "ok"
    assert task_count > 0
    parsed = json.loads(payload)
    assert "config" in parsed
    assert "plan" in parsed


def test_node_run_invalid():
    node = PSN_RayParallelSampler()
    valid, payload, reason, task_count = node.run(0, 64, 8, "round_robin", "json")
    assert valid is False
    assert payload == ""
    assert task_count == 0
    assert "num_workers" in reason


def test_node_run_bad_scheduling():
    node = PSN_RayParallelSampler()
    valid, payload, reason, task_count = node.run(4, 64, 8, "bogus", "json")
    assert valid is False
    assert "scheduling" in reason


def test_edge_single_worker_single_item():
    plan = psn_build_work_plan(1, 1, 1, "static")
    assert plan == [{"worker": 0, "start": 0, "count": 1}]
    sizes = psn_compute_shard_sizes(1, 1)
    assert sizes == [1]


def test_edge_batch_larger_than_workers():
    plan = psn_build_work_plan(2, 100, 10, "round_robin")
    total = sum(t["count"] for t in plan)
    assert total == 100
    # 100 / 10 = 10 tasks, round_robin over 2 workers
    assert len(plan) == 10
