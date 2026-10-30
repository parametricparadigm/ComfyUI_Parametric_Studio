"""
Tests for PSN_SmartModelLoader (pure logic, no GPU, no file I/O).
"""

import json
import pytest

from psn_nodes.gen.n_1_unified_model_loader_for_ps_backend import (
    PSN_SmartModelLoader,
    _validate_model_path,
    _get_extension,
    _determine_backend,
    _select_quantization,
    _dtype_for_quant,
)


class TestPSNSmartModelLoader:
    """Tests for the PSN_SmartModelLoader node."""

    def setup_method(self):
        self.node = PSN_SmartModelLoader()

    def test_safetensors_high_vram_returns_fp16(self):
        """High VRAM with .safetensors should select fp16."""
        (plan_str,) = self.node.run(
            model_path="model.safetensors",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=16384,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "ok"
        assert plan["backend"] == "safetensors"
        assert plan["quantization"] == "fp16"
        assert plan["outputs"]["MODEL"]["dtype"] == "float16"

    def test_safetensors_low_vram_returns_fp8(self):
        """Low VRAM with .safetensors should select fp8."""
        (plan_str,) = self.node.run(
            model_path="model.safetensors",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=2048,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "ok"
        assert plan["backend"] == "safetensors"
        assert plan["quantization"] == "fp8"
        assert plan["outputs"]["MODEL"]["dtype"] == "float8"

    def test_gguf_backend_selected(self):
        """GGUF file should select gguf backend."""
        (plan_str,) = self.node.run(
            model_path="model.gguf",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=8192,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "ok"
        assert plan["backend"] == "gguf"
        assert plan["quantization"] == "gguf_native"
        assert plan["outputs"]["MODEL"]["dtype"] == "gguf"

    def test_forced_quantization_q4_0(self):
        """Forced q4_0 quantization should be respected."""
        (plan_str,) = self.node.run(
            model_path="model.safetensors",
            min_vram_mb=4096,
            quantization_type="q4_0",
            vram_mb=16384,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "ok"
        assert plan["quantization"] == "q4_0"
        assert plan["outputs"]["MODEL"]["dtype"] == "q4_0"

    def test_invalid_extension_fails(self):
        """Unsupported file extension should return error."""
        (plan_str,) = self.node.run(
            model_path="model.bin",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=8192,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "failed"
        assert "Unsupported file extension" in plan["error"]

    def test_empty_model_path_fails(self):
        """Empty model path should return error."""
        (plan_str,) = self.node.run(
            model_path="",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=8192,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "failed"
        assert "must not be empty" in plan["error"]

    def test_negative_vram_fails(self):
        """Negative VRAM should return error."""
        (plan_str,) = self.node.run(
            model_path="model.safetensors",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=-1,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "failed"
        assert "non-negative integer" in plan["error"]

    def test_default_vram_when_not_provided(self):
        """When vram_mb is not provided, default 8192 should be used."""
        (plan_str,) = self.node.run(
            model_path="model.safetensors",
            min_vram_mb=4096,
            quantization_type="auto",
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "ok"
        assert plan["vram_mb"] == 8192
        assert plan["quantization"] == "fp16"

    def test_boundary_vram_equal_to_min(self):
        """VRAM exactly equal to min_vram_mb should use fp16."""
        (plan_str,) = self.node.run(
            model_path="model.safetensors",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=4096,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "ok"
        assert plan["quantization"] == "fp16"

    def test_boundary_vram_one_below_min(self):
        """VRAM one below min_vram_mb should use fp8."""
        (plan_str,) = self.node.run(
            model_path="model.safetensors",
            min_vram_mb=4096,
            quantization_type="auto",
            vram_mb=4095,
        )
        plan = json.loads(plan_str)
        assert plan["status"] == "ok"
        assert plan["quantization"] == "fp8"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_validate_model_path_valid(self):
        valid, err = _validate_model_path("model.safetensors")
        assert valid is True
        assert err == ""

    def test_validate_model_path_no_extension(self):
        valid, err = _validate_model_path("model")
        assert valid is False
        assert "file extension" in err

    def test_get_extension_safetensors(self):
        assert _get_extension("path/to/model.safetensors") == ".safetensors"

    def test_get_extension_gguf(self):
        assert _get_extension("path/to/model.gguf") == ".gguf"

    def test_get_extension_case_insensitive(self):
        assert _get_extension("path/to/model.SAFETENSORS") == ".safetensors"

    def test_determine_backend_safetensors(self):
        backend, err = _determine_backend("model.safetensors")
        assert backend == "safetensors"
        assert err == ""

    def test_determine_backend_gguf(self):
        backend, err = _determine_backend("model.gguf")
        assert backend == "gguf"
        assert err == ""

    def test_determine_backend_unknown(self):
        backend, err = _determine_backend("model.bin")
        assert backend == "unknown"
        assert "Unsupported" in err

    def test_select_quantization_auto_high_vram(self):
        quant, reason = _select_quantization("safetensors", "auto", 8192, 4096)
        assert quant == "fp16"

    def test_select_quantization_auto_low_vram(self):
        quant, reason = _select_quantization("safetensors", "auto", 2048, 4096)
        assert quant == "fp8"

    def test_select_quantization_forced(self):
        quant, reason = _select_quantization("safetensors", "q8_0", 8192, 4096)
        assert quant == "q8_0"

    def test_dtype_for_quant_fp16(self):
        assert _dtype_for_quant("fp16") == "float16"

    def test_dtype_for_quant_fp8(self):
        assert _dtype_for_quant("fp8") == "float8"

    def test_dtype_for_quant_gguf(self):
        assert _dtype_for_quant("gguf_native") == "gguf"
