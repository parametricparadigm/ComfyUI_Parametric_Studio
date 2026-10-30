"""Tests for PSN_CV_VRAMGuard node."""

import pytest

from psn_nodes.gen.psn_cv_vramguard import PSN_CV_VRAMGuard


def _make_node():
    return PSN_CV_VRAMGuard()


def test_auto_low_vram_returns_cuda():
    node = _make_node()
    device, warning = node.run(vram_used_mb=100.0, threshold_mb=500, device="auto")
    assert device == "cuda"
    assert warning == ""


def test_auto_high_vram_returns_cpu_with_warning():
    node = _make_node()
    device, warning = node.run(vram_used_mb=600.0, threshold_mb=500, device="auto")
    assert device == "cpu"
    assert "CPU" in warning
    assert "600" in warning


def test_auto_exact_threshold_returns_cpu():
    node = _make_node()
    device, warning = node.run(vram_used_mb=500.0, threshold_mb=500, device="auto")
    assert device == "cpu"
    assert warning != ""


def test_device_cpu_always_cpu():
    node = _make_node()
    device, warning = node.run(vram_used_mb=99999.0, threshold_mb=1, device="cpu")
    assert device == "cpu"
    assert warning == ""


def test_device_cuda_always_cuda():
    node = _make_node()
    device, warning = node.run(vram_used_mb=99999.0, threshold_mb=1, device="cuda")
    assert device == "cuda"
    assert warning == ""


def test_invalid_device_raises():
    node = _make_node()
    with pytest.raises(ValueError, match="device must be one of"):
        node.run(vram_used_mb=100.0, threshold_mb=500, device="metal")


def test_negative_vram_raises():
    node = _make_node()
    with pytest.raises(ValueError, match="non-negative"):
        node.run(vram_used_mb=-1.0, threshold_mb=500, device="auto")


def test_negative_threshold_raises():
    node = _make_node()
    with pytest.raises(ValueError, match="non-negative"):
        node.run(vram_used_mb=100.0, threshold_mb=-1, device="auto")


def test_non_numeric_vram_raises():
    node = _make_node()
    with pytest.raises(TypeError, match="vram_used_mb must be a number"):
        node.run(vram_used_mb="100", threshold_mb=500, device="auto")


def test_non_numeric_threshold_raises():
    node = _make_node()
    with pytest.raises(TypeError, match="threshold_mb must be a number"):
        node.run(vram_used_mb=100.0, threshold_mb="500", device="auto")


def test_zero_vram_auto_returns_cuda():
    node = _make_node()
    device, warning = node.run(vram_used_mb=0.0, threshold_mb=500, device="auto")
    assert device == "cuda"
    assert warning == ""


def test_zero_threshold_any_positive_vram_returns_cpu():
    node = _make_node()
    device, warning = node.run(vram_used_mb=1.0, threshold_mb=0, device="auto")
    assert device == "cpu"
    assert warning != ""
