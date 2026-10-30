"""Tests for PSN_Core_VRAM_Guard."""

import pytest
from psn_nodes.gen.psn_core_vram_guard import PSN_Core_VRAM_Guard


def test_offload_when_usage_exceeds_threshold():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.8, vram_usage=0.9)
    assert model == "my_model"
    assert offloaded is True
    assert "exceeds threshold" in reason


def test_no_offload_when_usage_below_threshold():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.8, vram_usage=0.5)
    assert model == "my_model"
    assert offloaded is False
    assert "within threshold" in reason


def test_no_offload_when_usage_equals_threshold():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.8, vram_usage=0.8)
    assert model == "my_model"
    assert offloaded is False
    assert "within threshold" in reason


def test_default_vram_usage_is_zero():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.8)
    assert model == "my_model"
    assert offloaded is False
    assert "within threshold" in reason


def test_invalid_threshold_below_zero():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=-0.1, vram_usage=0.5)
    assert model == "my_model"
    assert offloaded is False
    assert "threshold must be in [0.0, 1.0]" in reason


def test_invalid_threshold_above_one():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=1.5, vram_usage=0.5)
    assert model == "my_model"
    assert offloaded is False
    assert "threshold must be in [0.0, 1.0]" in reason


def test_invalid_vram_usage_below_zero():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.8, vram_usage=-0.1)
    assert model == "my_model"
    assert offloaded is False
    assert "vram_usage must be in [0.0, 1.0]" in reason


def test_invalid_vram_usage_above_one():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.8, vram_usage=1.5)
    assert model == "my_model"
    assert offloaded is False
    assert "vram_usage must be in [0.0, 1.0]" in reason


def test_non_numeric_threshold():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold="high", vram_usage=0.5)
    assert model == "my_model"
    assert offloaded is False
    assert "threshold must be a number" in reason


def test_non_numeric_vram_usage():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.8, vram_usage="full")
    assert model == "my_model"
    assert offloaded is False
    assert "vram_usage must be a number" in reason


def test_model_payload_is_passed_through_unchanged():
    node = PSN_Core_VRAM_Guard()
    payload = {"weights": [1, 2, 3], "name": "test"}
    model, offloaded, reason = node.run(model=payload, threshold=0.8, vram_usage=0.9)
    assert model is payload
    assert offloaded is True


def test_boundary_threshold_zero():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=0.0, vram_usage=0.0)
    assert offloaded is False
    model, offloaded, reason = node.run(model="my_model", threshold=0.0, vram_usage=0.001)
    assert offloaded is True


def test_boundary_threshold_one():
    node = PSN_Core_VRAM_Guard()
    model, offloaded, reason = node.run(model="my_model", threshold=1.0, vram_usage=0.999)
    assert offloaded is False
    model, offloaded, reason = node.run(model="my_model", threshold=1.0, vram_usage=1.0)
    assert offloaded is False
