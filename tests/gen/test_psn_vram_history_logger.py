"""Tests for PSN_VRAM_History_Logger."""

import json
import pytest
from psn_nodes.gen.psn_vram_history_logger import (
    PSN_VRAM_History_Logger,
    VRAMHistoryLogger,
    _validate_inputs,
)


def test_valid_inputs_produce_history():
    node = PSN_VRAM_History_Logger()
    samples = [100.0, 200.0, 300.0]
    history, history_json = node.run("test_run", 100, samples)
    assert len(history) == 3
    assert history[0]["vram_mb"] == 100.0
    assert history[1]["vram_mb"] == 200.0
    assert history[2]["vram_mb"] == 300.0
    parsed = json.loads(history_json)
    assert parsed["run_id"] == "test_run"
    assert parsed["interval_ms"] == 100
    assert len(parsed["samples"]) == 3


def test_empty_samples_returns_empty_history():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run("test_run", 100, [])
    assert history == []
    parsed = json.loads(history_json)
    assert parsed["samples"] == []


def test_invalid_run_id_empty_string():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run("", 100, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_run_id_non_string():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run(123, 100, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_interval_ms_zero():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run("test_run", 0, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_interval_ms_negative():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run("test_run", -5, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_samples_non_list():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run("test_run", 100, "not_a_list")
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_samples_negative_value():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run("test_run", 100, [100.0, -5.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_samples_non_numeric():
    node = PSN_VRAM_History_Logger()
    history, history_json = node.run("test_run", 100, [100.0, "bad"])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_logger_rejects_samples_within_interval():
    logger = VRAMHistoryLogger("test", 100)
    assert logger.add_sample(100.0, timestamp_ms=0.0) is True
    assert logger.add_sample(200.0, timestamp_ms=50.0) is False  # within 100ms
    assert logger.add_sample(300.0, timestamp_ms=100.0) is True  # exactly at interval
    assert len(logger.get_history()) == 2


def test_logger_rejects_negative_vram():
    logger = VRAMHistoryLogger("test", 100)
    with pytest.raises(ValueError):
        logger.add_sample(-1.0, timestamp_ms=0.0)


def test_logger_rejects_negative_timestamp():
    logger = VRAMHistoryLogger("test", 100)
    with pytest.raises(ValueError):
        logger.add_sample(100.0, timestamp_ms=-1.0)


def test_history_json_structure():
    node = PSN_VRAM_History_Logger()
    samples = [50.0, 150.0]
    history, history_json = node.run("json_test", 200, samples)
    parsed = json.loads(history_json)
    assert "run_id" in parsed
    assert "interval_ms" in parsed
    assert "samples" in parsed
    assert parsed["run_id"] == "json_test"
    assert parsed["interval_ms"] == 200
    assert len(parsed["samples"]) == 2
    for s in parsed["samples"]:
        assert "timestamp_ms" in s
        assert "vram_mb" in s
