"""
Tests for PSN_HSWQ_Model_Loader.

Covers:
- Valid configurations
- Invalid model_path (empty, non-string, null bytes, too long)
- Invalid quantization_bit (non-int, out of range)
- Invalid device (non-string, not in allowlist)
- Invalid model_size_gb (negative, too large, non-numeric)
- VRAM estimation correctness
- Edge cases (zero size, max size)
"""

import pytest
from psn_nodes.gen.psn_hswq_model_loader import (
    PSN_HSWQ_Model_Loader,
    _validate_model_path,
    _validate_quantization_bit,
    _validate_device,
    _estimate_vram_usage,
    ALLOWED_BITS,
    ALLOWED_DEVICES,
    MAX_MODEL_SIZE_GB,
)


class TestValidateModelPath:
    def test_valid_path(self):
        ok, reason = _validate_model_path("/models/sdxl_hswq_4bit.onnx")
        assert ok is True
        assert reason == "ok"

    def test_empty_path(self):
        ok, reason = _validate_model_path("")
        assert ok is False
        assert "empty" in reason

    def test_non_string_path(self):
        ok, reason = _validate_model_path(12345)
        assert ok is False
        assert "string" in reason

    def test_null_byte_path(self):
        ok, reason = _validate_model_path("/models/\x00bad.onnx")
        assert ok is False
        assert "null" in reason

    def test_too_long_path(self):
        long_path = "a" * 1025
        ok, reason = _validate_model_path(long_path)
        assert ok is False
        assert "length" in reason

    def test_max_length_path(self):
        max_path = "a" * 1024
        ok, reason = _validate_model_path(max_path)
        assert ok is True


class TestValidateQuantizationBit:
    def test_valid_bits(self):
        for bit in ALLOWED_BITS:
            ok, reason = _validate_quantization_bit(bit)
            assert ok is True, f"Bit {bit} should be valid"

    def test_invalid_bit_value(self):
        ok, reason = _validate_quantization_bit(3)
        assert ok is False
        assert "one of" in reason

    def test_non_integer_bit(self):
        ok, reason = _validate_quantization_bit(4.0)
        assert ok is False
        assert "integer" in reason

    def test_string_bit(self):
        ok, reason = _validate_quantization_bit("4")
        assert ok is False
        assert "integer" in reason


class TestValidateDevice:
    def test_valid_devices(self):
        for dev in ALLOWED_DEVICES:
            ok, reason = _validate_device(dev)
            assert ok is True, f"Device {dev} should be valid"

    def test_invalid_device(self):
        ok, reason = _validate_device("gpu")
        assert ok is False
        assert "one of" in reason

    def test_non_string_device(self):
        ok, reason = _validate_device(1)
        assert ok is False
        assert "string" in reason


class TestEstimateVramUsage:
    def test_fp16_no_quantization(self):
        # 16-bit means no reduction
        vram = _estimate_vram_usage(6.5, 16, "cuda")
        assert vram == pytest.approx(6.5, abs=0.001)

    def test_8bit_quantization(self):
        # 8-bit is half of 16-bit
        vram = _estimate_vram_usage(6.5, 8, "cuda")
        assert vram == pytest.approx(3.25, abs=0.001)

    def test_4bit_quantization(self):
        # 4-bit is quarter of 16-bit
        vram = _estimate_vram_usage(6.5, 4, "cuda")
        assert vram == pytest.approx(1.625, abs=0.001)

    def test_2bit_quantization(self):
        # 2-bit is eighth of 16-bit
        vram = _estimate_vram_usage(6.5, 2, "cuda")
        assert vram == pytest.approx(0.8125, abs=0.001)

    def test_zero_size(self):
        vram = _estimate_vram_usage(0.0, 4, "cuda")
        assert vram == 0.0

    def test_negative_size_clamped(self):
        vram = _estimate_vram_usage(-1.0, 4, "cuda")
        assert vram == 0.0

    def test_cpu_device_same_estimation(self):
        vram_cuda = _estimate_vram_usage(6.5, 4, "cuda")
        vram_cpu = _estimate_vram_usage(6.5, 4, "cpu")
        assert vram_cuda == vram_cpu


class TestPSNHSWQModelLoaderRun:
    def setup_method(self):
        self.node = PSN_HSWQ_Model_Loader()

    def test_valid_configuration(self):
        valid, vram, reason = self.node.run(
            model_path="/models/sdxl_hswq_4bit.onnx",
            quantization_bit=4,
            device="cuda",
            model_size_gb=6.5,
        )
        assert valid is True
        assert reason == "ok"
        assert vram == pytest.approx(1.625, abs=0.001)

    def test_invalid_empty_path(self):
        valid, vram, reason = self.node.run(
            model_path="",
            quantization_bit=4,
            device="cuda",
        )
        assert valid is False
        assert vram == 0.0
        assert "empty" in reason

    def test_invalid_bit(self):
        valid, vram, reason = self.node.run(
            model_path="/models/test.onnx",
            quantization_bit=3,
            device="cuda",
        )
        assert valid is False
        assert vram == 0.0
        assert "one of" in reason

    def test_invalid_device(self):
        valid, vram, reason = self.node.run(
            model_path="/models/test.onnx",
            quantization_bit=4,
            device="tpu",
        )
        assert valid is False
        assert vram == 0.0
        assert "one of" in reason

    def test_negative_model_size(self):
        valid, vram, reason = self.node.run(
            model_path="/models/test.onnx",
            quantization_bit=4,
            device="cuda",
            model_size_gb=-1.0,
        )
        assert valid is False
        assert vram == 0.0
        assert "non-negative" in reason

    def test_excessive_model_size(self):
        valid, vram, reason = self.node.run(
            model_path="/models/test.onnx",
            quantization_bit=4,
            device="cuda",
            model_size_gb=MAX_MODEL_SIZE_GB + 1.0,
        )
        assert valid is False
        assert vram == 0.0
        assert "exceeds" in reason

    def test_non_numeric_model_size(self):
        valid, vram, reason = self.node.run(
            model_path="/models/test.onnx",
            quantization_bit=4,
            device="cuda",
            model_size_gb="six",
        )
        assert valid is False
        assert vram == 0.0
        assert "number" in reason

    def test_8bit_vram_estimation(self):
        valid, vram, reason = self.node.run(
            model_path="/models/sdxl_hswq_8bit.onnx",
            quantization_bit=8,
            device="cuda",
            model_size_gb=6.5,
        )
        assert valid is True
        assert vram == pytest.approx(3.25, abs=0.001)

    def test_2bit_vram_estimation(self):
        valid, vram, reason = self.node.run(
            model_path="/models/sdxl_hswq_2bit.onnx",
            quantization_bit=2,
            device="cuda",
            model_size_gb=6.5,
        )
        assert valid is True
        assert vram == pytest.approx(0.8125, abs=0.001)

    def test_cpu_device_valid(self):
        valid, vram, reason = self.node.run(
            model_path="/models/sdxl_hswq_4bit.onnx",
            quantization_bit=4,
            device="cpu",
            model_size_gb=6.5,
        )
        assert valid is True
        assert vram == pytest.approx(1.625, abs=0.001)
