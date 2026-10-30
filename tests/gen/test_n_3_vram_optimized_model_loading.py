"""
Tests for PSN_Model_Vram_Optimizer.
Pure-logic tests: no files, no network, no GPU.
"""

import json
import pytest

from psn_nodes.gen.n_3_vram_optimized_model_loading import (
    PSN_Model_Vram_Optimizer,
    _parse_state_dict_json,
    _is_prunable,
    _compute_memory_gb,
    _QUANT_MODES,
)


def _make_state_dict(entries):
    """Helper: build a state-dict JSON string from a list of (key, num_params)."""
    d = {k: {"num_params": n} for k, n in entries}
    return json.dumps(d)


class TestParseStateDictJson:
    def test_valid_simple(self):
        s = json.dumps({"a": {"num_params": 100}, "b": 200})
        result = _parse_state_dict_json(s)
        assert result == {"a": 100, "b": 200}

    def test_empty_object(self):
        result = _parse_state_dict_json("{}")
        assert result == {}

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            _parse_state_dict_json("not json")

    def test_not_a_dict(self):
        with pytest.raises(ValueError, match="must decode to a JSON object"):
            _parse_state_dict_json("[1, 2, 3]")

    def test_negative_params(self):
        with pytest.raises(ValueError, match="non-negative"):
            _parse_state_dict_json(json.dumps({"a": -5}))

    def test_non_numeric_params(self):
        with pytest.raises(ValueError, match="Invalid value"):
            _parse_state_dict_json(json.dumps({"a": "lots"}))


class TestIsPrunable:
    def test_vae_decoder(self):
        assert _is_prunable("vae.decoder.conv1.weight") is True

    def test_vae_encoder(self):
        assert _is_prunable("vae.encoder.conv1.weight") is True

    def test_ema(self):
        assert _is_prunable("ema.shadow") is True

    def test_optimizer(self):
        assert _is_prunable("optimizer.step") is True

    def test_metadata(self):
        assert _is_prunable(".metadata") is True

    def test_regular_weight(self):
        assert _is_prunable("unet.mid_block.0.weight") is False

    def test_regular_bias(self):
        assert _is_prunable("unet.input_blocks.0.bias") is False


class TestComputeMemoryGb:
    def test_fp32(self):
        # 1 billion params * 4 bytes = 4e9 bytes. 1 GiB = 1024^3 bytes.
        # 4e9 / 1024^3 = 3.725290298461914 GB
        gb = _compute_memory_gb(1_000_000_000, 4)
        assert abs(gb - 3.725290298461914) < 1e-6

    def test_int8(self):
        # 1 billion params * 1 byte = 1e9 bytes.
        # 1e9 / 1024^3 = 0.9313225746154785 GB
        gb = _compute_memory_gb(1_000_000_000, 1)
        assert abs(gb - 0.9313225746154785) < 1e-6

    def test_zero_params(self):
        assert _compute_memory_gb(0, 4) == 0.0


class TestPSNModelVramOptimizer:
    def setup_method(self):
        self.node = PSN_Model_Vram_Optimizer()

    def test_no_prune_no_quant_fits(self):
        # 100M params fp32 = 0.3725 GB, target 8 GB -> fits
        sd = _make_state_dict([("unet.mid.weight", 100_000_000)])
        fits, opt_json, report = self.node.run(sd, False, "none", 8.0)
        assert fits is True
        opt = json.loads(opt_json)
        assert "unet.mid.weight" in opt
        assert "FITS" in report

    def test_prune_removes_vae_keys(self):
        sd = _make_state_dict([
            ("unet.mid.weight", 50_000_000),
            ("vae.decoder.conv1.weight", 10_000_000),
            ("vae.encoder.conv1.weight", 10_000_000),
        ])
        fits, opt_json, report = self.node.run(sd, True, "none", 8.0)
        opt = json.loads(opt_json)
        assert "unet.mid.weight" in opt
        assert "vae.decoder.conv1.weight" not in opt
        assert "vae.encoder.conv1.weight" not in opt
        assert "Pruned keys (2)" in report

    def test_quantize_w8a8_reduces_memory(self):
        # 4B params fp32 = 14.90 GB; w8a8 = 3.725 GB
        sd = _make_state_dict([("unet.big.weight", 4_000_000_000)])
        fits_fp32, _, report_fp32 = self.node.run(sd, False, "none", 8.0)
        fits_w8a8, _, report_w8a8 = self.node.run(sd, False, "w8a8", 8.0)
        assert fits_fp32 is False
        assert fits_w8a8 is True
        assert "EXCEEDS" in report_fp32
        assert "FITS" in report_w8a8

    def test_quantize_int8(self):
        sd = _make_state_dict([("unet.big.weight", 4_000_000_000)])
        fits, opt_json, report = self.node.run(sd, False, "int8", 8.0)
        assert fits is True
        opt = json.loads(opt_json)
        assert opt["unet.big.weight"]["quantized"] is True
        assert opt["unet.big.weight"]["bytes_per_param"] == 1

    def test_prune_and_quant_combined(self):
        sd = _make_state_dict([
            ("unet.mid.weight", 2_000_000_000),
            ("vae.decoder.conv1.weight", 1_000_000_000),
            ("ema.shadow", 1_000_000_000),
        ])
        # After prune: 2B params. w8a8: 2B * 1 = 1.8626 GB. Target 2 GB -> fits.
        fits, opt_json, report = self.node.run(sd, True, "w8a8", 2.0)
        assert fits is True
        opt = json.loads(opt_json)
        assert len(opt) == 1
        assert "unet.mid.weight" in opt

    def test_exceeds_target_vram(self):
        # 10B params fp32 = 37.25 GB, target 8 GB
        sd = _make_state_dict([("unet.huge.weight", 10_000_000_000)])
        fits, _, report = self.node.run(sd, False, "none", 8.0)
        assert fits is False
        assert "EXCEEDS" in report

    def test_invalid_quantize_mode(self):
        sd = _make_state_dict([("a", 100)])
        with pytest.raises(ValueError, match="quantize_mode"):
            self.node.run(sd, False, "fp16", 8.0)

    def test_empty_state_dict(self):
        fits, opt_json, report = self.node.run("{}", True, "none", 8.0)
        assert fits is True
        opt = json.loads(opt_json)
        assert opt == {}
        assert "FITS" in report

    def test_all_keys_pruned(self):
        sd = _make_state_dict([
            ("vae.decoder.conv1.weight", 10_000_000),
            ("ema.shadow", 5_000_000),
        ])
        fits, opt_json, report = self.node.run(sd, True, "none", 8.0)
        opt = json.loads(opt_json)
        assert opt == {}
        assert fits is True

    def test_bad_state_dict_json(self):
        with pytest.raises(ValueError):
            self.node.run("not valid json", False, "none", 8.0)

    def test_state_dict_not_string(self):
        with pytest.raises(ValueError):
            self.node.run(12345, False, "none", 8.0)

    def test_report_contains_all_sections(self):
        sd = _make_state_dict([
            ("unet.mid.weight", 100_000_000),
            ("vae.decoder.conv1.weight", 50_000_000),
        ])
        fits, _, report = self.node.run(sd, True, "w8a8", 8.0)
        assert "=== VRAM Optimization Report ===" in report
        assert "Original parameters:" in report
        assert "Pruned parameters:" in report
        assert "Quantized parameters:" in report
        assert "Quantization mode:" in report
        assert "Final memory estimate:" in report
        assert "Target VRAM:" in report
        assert "Status:" in report
        assert "Pruned keys (1):" in report
        assert "vae.decoder.conv1.weight" in report
