"""
Tests for PSN_FluxNAG: Adaptive Guidance for Flux Models.

Tests cover:
- Valid configurations for each supported model family
- Edge cases: boundary nag_scale values, enable_negative toggling
- Bad inputs: invalid model family, out-of-range nag_scale, non-numeric nag_scale
- Effective scale computation with and without negative prompts
- JSON config structure and content
"""

import json
import math
import pytest

from psn_nodes.gen.n_7_adaptive_guidance_for_flux_models import (
    PSN_FluxNAG,
    _validate_nag_scale,
    _validate_model_family,
    _build_nag_config,
    _SUPPORTED_MODELS,
    _NAG_SCALE_MIN,
    _NAG_SCALE_MAX,
)


class TestValidateNagScale:
    """Tests for nag_scale validation."""

    def test_valid_default_scale(self):
        ok, val, reason = _validate_nag_scale(1.0)
        assert ok is True
        assert val == 1.0
        assert reason == "ok"

    def test_valid_boundary_min(self):
        ok, val, reason = _validate_nag_scale(_NAG_SCALE_MIN)
        assert ok is True
        assert val == 0.0

    def test_valid_boundary_max(self):
        ok, val, reason = _validate_nag_scale(_NAG_SCALE_MAX)
        assert ok is True
        assert val == 10.0

    def test_invalid_below_min(self):
        ok, val, reason = _validate_nag_scale(-0.1)
        assert ok is False
        assert "must be in" in reason

    def test_invalid_above_max(self):
        ok, val, reason = _validate_nag_scale(10.1)
        assert ok is False
        assert "must be in" in reason

    def test_invalid_nan(self):
        ok, val, reason = _validate_nag_scale(float("nan"))
        assert ok is False
        assert "finite" in reason

    def test_invalid_inf(self):
        ok, val, reason = _validate_nag_scale(float("inf"))
        assert ok is False
        assert "finite" in reason

    def test_invalid_string(self):
        ok, val, reason = _validate_nag_scale("1.0")
        assert ok is False
        assert "must be a number" in reason

    def test_invalid_none(self):
        ok, val, reason = _validate_nag_scale(None)
        assert ok is False
        assert "must be a number" in reason


class TestValidateModelFamily:
    """Tests for model family validation."""

    def test_valid_flux(self):
        ok, norm, reason = _validate_model_family("flux")
        assert ok is True
        assert norm == "flux"

    def test_valid_flux2klein(self):
        ok, norm, reason = _validate_model_family("flux2klein")
        assert ok is True
        assert norm == "flux2klein"

    def test_valid_anima(self):
        ok, norm, reason = _validate_model_family("anima")
        assert ok is True
        assert norm == "anima"

    def test_valid_case_insensitive(self):
        ok, norm, reason = _validate_model_family("Flux")
        assert ok is True
        assert norm == "flux"

    def test_valid_with_whitespace(self):
        ok, norm, reason = _validate_model_family("  anima  ")
        assert ok is True
        assert norm == "anima"

    def test_invalid_unknown_model(self):
        ok, norm, reason = _validate_model_family("sd15")
        assert ok is False
        assert "not supported" in reason

    def test_invalid_empty_string(self):
        ok, norm, reason = _validate_model_family("")
        assert ok is False
        assert "not supported" in reason

    def test_invalid_non_string(self):
        ok, norm, reason = _validate_model_family(123)
        assert ok is False
        assert "must be a string" in reason


class TestBuildNagConfig:
    """Tests for NAG configuration building."""

    def test_config_with_negative_enabled(self):
        config = _build_nag_config(1.0, True, "flux")
        assert config["nag_scale"] == 1.0
        assert config["effective_scale"] == 1.0
        assert config["enable_negative"] is True
        assert config["model_family"] == "flux"
        assert config["guidance_method"] == "nag"
        assert config["normalization"] == "attention_l2"
        assert config["supported"] is True

    def test_config_with_negative_disabled(self):
        config = _build_nag_config(1.0, False, "flux")
        assert config["effective_scale"] == pytest.approx(0.85, abs=1e-6)
        assert config["enable_negative"] is False

    def test_config_scale_scaling(self):
        config = _build_nag_config(2.5, True, "anima")
        assert config["effective_scale"] == pytest.approx(2.5, abs=1e-6)

    def test_config_scale_scaling_no_negative(self):
        config = _build_nag_config(2.0, False, "flux2klein")
        assert config["effective_scale"] == pytest.approx(1.7, abs=1e-6)

    def test_config_zero_scale(self):
        config = _build_nag_config(0.0, True, "flux")
        assert config["effective_scale"] == 0.0


class TestPSNFluxNAGNode:
    """Tests for the PSN_FluxNAG node class."""

    def setup_method(self):
        self.node = PSN_FluxNAG()

    def test_input_types_structure(self):
        inputs = PSN_FluxNAG.INPUT_TYPES()
        assert "required" in inputs
        assert "model_family" in inputs["required"]
        assert "nag_scale" in inputs["required"]
        assert "enable_negative" in inputs["required"]

    def test_return_types(self):
        assert PSN_FluxNAG.RETURN_TYPES == ("STRING", "STRING", "FLOAT")
        assert PSN_FluxNAG.RETURN_NAMES == ("config", "status", "effective_scale")
        assert PSN_FluxNAG.FUNCTION == "run"

    def test_run_valid_flux(self):
        config_json, status, eff_scale = self.node.run("flux", 1.0, False)
        config = json.loads(config_json)
        assert config["supported"] is True
        assert config["model_family"] == "flux"
        assert config["effective_scale"] == pytest.approx(0.85, abs=1e-6)
        assert eff_scale == pytest.approx(0.85, abs=1e-6)
        assert "NAG configured" in status
        assert "flux" in status

    def test_run_valid_flux2klein_with_negative(self):
        config_json, status, eff_scale = self.node.run("flux2klein", 2.0, True)
        config = json.loads(config_json)
        assert config["supported"] is True
        assert config["model_family"] == "flux2klein"
        assert config["effective_scale"] == pytest.approx(2.0, abs=1e-6)
        assert eff_scale == pytest.approx(2.0, abs=1e-6)
        assert "negative=enabled" in status

    def test_run_valid_anima(self):
        config_json, status, eff_scale = self.node.run("anima", 0.5, False)
        config = json.loads(config_json)
        assert config["supported"] is True
        assert config["model_family"] == "anima"
        assert config["effective_scale"] == pytest.approx(0.425, abs=1e-6)
        assert eff_scale == pytest.approx(0.425, abs=1e-6)

    def test_run_invalid_model_family(self):
        config_json, status, eff_scale = self.node.run("sd15", 1.0, False)
        config = json.loads(config_json)
        assert config["supported"] is False
        assert "error" in config
        assert "ERROR" in status
        assert eff_scale == 0.0

    def test_run_invalid_nag_scale_too_high(self):
        config_json, status, eff_scale = self.node.run("flux", 100.0, False)
        config = json.loads(config_json)
        assert config["supported"] is False
        assert "ERROR" in status
        assert eff_scale == 0.0

    def test_run_invalid_nag_scale_negative(self):
        config_json, status, eff_scale = self.node.run("flux", -1.0, False)
        config = json.loads(config_json)
        assert config["supported"] is False
        assert "ERROR" in status
        assert eff_scale == 0.0

    def test_run_nag_scale_nan(self):
        config_json, status, eff_scale = self.node.run("flux", float("nan"), False)
        config = json.loads(config_json)
        assert config["supported"] is False
        assert "ERROR" in status
        assert eff_scale == 0.0

    def test_run_nag_scale_zero(self):
        config_json, status, eff_scale = self.node.run("flux", 0.0, True)
        config = json.loads(config_json)
        assert config["supported"] is True
        assert config["effective_scale"] == 0.0
        assert eff_scale == 0.0

    def test_run_nag_scale_max(self):
        config_json, status, eff_scale = self.node.run("flux", 10.0, True)
        config = json.loads(config_json)
        assert config["supported"] is True
        assert config["effective_scale"] == pytest.approx(10.0, abs=1e-6)
        assert eff_scale == pytest.approx(10.0, abs=1e-6)

    def test_run_enable_negative_coerced_from_int(self):
        config_json, status, eff_scale = self.node.run("flux", 1.0, 1)
        config = json.loads(config_json)
        assert config["enable_negative"] is True
        assert config["effective_scale"] == pytest.approx(1.0, abs=1e-6)

    def test_run_enable_negative_coerced_from_zero(self):
        config_json, status, eff_scale = self.node.run("flux", 1.0, 0)
        config = json.loads(config_json)
        assert config["enable_negative"] is False
        assert config["effective_scale"] == pytest.approx(0.85, abs=1e-6)

    def test_config_json_is_valid_json(self):
        config_json, status, _ = self.node.run("flux", 1.0, False)
        parsed = json.loads(config_json)
        assert isinstance(parsed, dict)
        assert "nag_scale" in parsed
        assert "effective_scale" in parsed
        assert "enable_negative" in parsed
        assert "model_family" in parsed
        assert "guidance_method" in parsed
        assert "normalization" in parsed
        assert "supported" in parsed

    def test_node_class_mappings(self):
        from psn_nodes.gen.n_7_adaptive_guidance_for_flux_models import NODE_CLASS_MAPPINGS
        assert "PSN_FluxNAG" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["PSN_FluxNAG"] is PSN_FluxNAG

    def test_node_display_name(self):
        from psn_nodes.gen.n_7_adaptive_guidance_for_flux_models import NODE_DISPLAY_NAME_MAPPINGS
        assert "PSN_FluxNAG" in NODE_DISPLAY_NAME_MAPPINGS
        assert "NAG" in NODE_DISPLAY_NAME_MAPPINGS["PSN_FluxNAG"]
