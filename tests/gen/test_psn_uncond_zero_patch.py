"""Tests for PSN_Uncond_Zero_Patch node."""

import json
import pytest

from psn_nodes.gen.psn_uncond_zero_patch import (
    PSN_Uncond_Zero_Patch,
    _validate_enable,
    _validate_min_steps,
    _validate_max_quality_drop,
    _build_patch_config,
    _simulate_skip,
)


class TestPSNUncondZeroPatch:
    """Test suite for PSN_Uncond_Zero_Patch."""

    def test_enabled_with_safe_min_steps(self):
        """When enabled with min_steps >= 10, the patch should be enabled and safe."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=15, max_quality_drop=0.1, total_steps=20
        )
        config = json.loads(patch_config)
        assert config["enabled"] is True
        assert config["mode"] == "skip_uncond"
        assert config["safe"] is True
        assert enabled is True
        assert warning == ""
        sim = json.loads(simulation)
        assert sim["skipped_count"] == 5  # steps 15,16,17,18,19
        assert sim["skipped_ratio"] == pytest.approx(5 / 20)

    def test_disabled_patch(self):
        """When disabled, the patch should not be enabled and no steps should be skipped."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=False, min_steps=10, max_quality_drop=0.1, total_steps=20
        )
        config = json.loads(patch_config)
        assert config["enabled"] is False
        assert config["mode"] == "disabled"
        assert enabled is False
        sim = json.loads(simulation)
        assert sim["skipped_count"] == 0
        assert sim["skipped_steps"] == []

    def test_low_min_steps_warning(self):
        """When min_steps < 10, a warning should be issued and safe should be False."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=5, max_quality_drop=0.1, total_steps=20
        )
        config = json.loads(patch_config)
        assert config["enabled"] is True
        assert config["safe"] is False
        assert enabled is False
        assert "below the recommended threshold" in warning
        sim = json.loads(simulation)
        assert sim["skipped_count"] == 15  # steps 5..19

    def test_high_quality_drop_warning(self):
        """When max_quality_drop > 0.15 and min_steps is safe, a warning should be issued."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=20, max_quality_drop=0.3, total_steps=30
        )
        config = json.loads(patch_config)
        assert config["enabled"] is True
        assert config["safe"] is True  # min_steps is safe
        assert enabled is True
        assert "exceeds the recommended threshold" in warning

    def test_invalid_enable_type(self):
        """Non-boolean enable should return an error."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable="yes", min_steps=10, max_quality_drop=0.1, total_steps=20
        )
        config = json.loads(patch_config)
        assert "error" in config
        assert enabled is False
        assert "enable must be a boolean" in warning

    def test_invalid_min_steps_negative(self):
        """Negative min_steps should return an error."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=-1, max_quality_drop=0.1, total_steps=20
        )
        config = json.loads(patch_config)
        assert "error" in config
        assert enabled is False
        assert "non-negative" in warning

    def test_invalid_max_quality_drop_out_of_range(self):
        """max_quality_drop > 1.0 should return an error."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=10, max_quality_drop=1.5, total_steps=20
        )
        config = json.loads(patch_config)
        assert "error" in config
        assert enabled is False
        assert "between 0.0 and 1.0" in warning

    def test_invalid_total_steps_zero(self):
        """total_steps = 0 should return an error."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=10, max_quality_drop=0.1, total_steps=0
        )
        config = json.loads(patch_config)
        assert "error" in config
        assert enabled is False
        assert "between 1 and 10000" in warning

    def test_min_steps_equals_total_steps(self):
        """When min_steps == total_steps, no steps should be skipped."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=20, max_quality_drop=0.1, total_steps=20
        )
        sim = json.loads(simulation)
        assert sim["skipped_count"] == 0
        assert sim["skipped_steps"] == []

    def test_min_steps_zero_skips_all(self):
        """When min_steps = 0, all steps should be skipped."""
        node = PSN_Uncond_Zero_Patch()
        patch_config, enabled, warning, simulation = node.run(
            enable=True, min_steps=0, max_quality_drop=0.1, total_steps=10
        )
        sim = json.loads(simulation)
        assert sim["skipped_count"] == 10
        assert sim["skipped_ratio"] == pytest.approx(1.0)
        # min_steps=0 < 10, so safe is False
        config = json.loads(patch_config)
        assert config["safe"] is False

    def test_validate_enable_helper(self):
        """Test the _validate_enable helper directly."""
        ok, err = _validate_enable(True)
        assert ok is True and err == ""
        ok, err = _validate_enable(False)
        assert ok is True and err == ""
        ok, err = _validate_enable(1)
        assert ok is False
        ok, err = _validate_enable("true")
        assert ok is False

    def test_validate_min_steps_helper(self):
        """Test the _validate_min_steps helper directly."""
        ok, err = _validate_min_steps(10)
        assert ok is True
        ok, err = _validate_min_steps(0)
        assert ok is True
        ok, err = _validate_min_steps(-1)
        assert ok is False
        ok, err = _validate_min_steps(10001)
        assert ok is False
        ok, err = _validate_min_steps("10")
        assert ok is False

    def test_validate_max_quality_drop_helper(self):
        """Test the _validate_max_quality_drop helper directly."""
        ok, err = _validate_max_quality_drop(0.5)
        assert ok is True
        ok, err = _validate_max_quality_drop(0.0)
        assert ok is True
        ok, err = _validate_max_quality_drop(1.0)
        assert ok is True
        ok, err = _validate_max_quality_drop(1.1)
        assert ok is False
        ok, err = _validate_max_quality_drop(-0.1)
        assert ok is False

    def test_build_patch_config_structure(self):
        """Test that _build_patch_config returns the expected structure."""
        config = _build_patch_config(True, 15, 0.1)
        assert set(config.keys()) == {"enabled", "mode", "min_steps", "max_quality_drop", "safe", "warning"}
        assert config["enabled"] is True
        assert config["mode"] == "skip_uncond"
        assert config["min_steps"] == 15
        assert config["max_quality_drop"] == 0.1
        assert config["safe"] is True
        assert config["warning"] == ""

    def test_simulate_skip_disabled(self):
        """Test _simulate_skip when disabled."""
        sim = _simulate_skip(False, 20, 10)
        assert sim["skipped_count"] == 0
        assert sim["skipped_steps"] == []
        assert sim["skipped_ratio"] == 0.0

    def test_simulate_skip_enabled(self):
        """Test _simulate_skip when enabled."""
        sim = _simulate_skip(True, 20, 10)
        assert sim["skipped_count"] == 10
        assert sim["skipped_steps"] == list(range(10, 20))
        assert sim["skipped_ratio"] == pytest.approx(0.5)
