"""Tests for psn_nodes.gen.n_1_dynamic_vram_aware_pipeline_selector."""

import math
import pytest

from psn_nodes.gen.n_1_dynamic_vram_aware_pipeline_selector import (
    PSN_VRAM_Query,
    PSN_Pipeline_Selector,
    _FALLBACK_PIPELINE_ID,
)


# ---------------------------------------------------------------------------
# PSN_VRAM_Query tests
# ---------------------------------------------------------------------------

class TestPSNVRAMQuery:
    def test_basic_utilization(self):
        node = PSN_VRAM_Query()
        free, total, util = node.run(
            free_vram_gb=48.0,
            total_vram_gb=96.0,
            device_index=0,
            refresh=True,
        )
        assert free == pytest.approx(48.0)
        assert total == pytest.approx(96.0)
        assert util == pytest.approx(50.0)

    def test_full_vram_available(self):
        node = PSN_VRAM_Query()
        free, total, util = node.run(
            free_vram_gb=96.0,
            total_vram_gb=96.0,
            device_index=0,
            refresh=False,
        )
        assert util == pytest.approx(0.0)

    def test_zero_free_vram(self):
        node = PSN_VRAM_Query()
        free, total, util = node.run(
            free_vram_gb=0.0,
            total_vram_gb=96.0,
            device_index=1,
            refresh=True,
        )
        assert util == pytest.approx(100.0)

    def test_free_exceeds_total_raises(self):
        node = PSN_VRAM_Query()
        with pytest.raises(ValueError, match="cannot exceed"):
            node.run(
                free_vram_gb=100.0,
                total_vram_gb=96.0,
                device_index=0,
                refresh=True,
            )

    def test_zero_total_raises(self):
        node = PSN_VRAM_Query()
        with pytest.raises(ValueError, match="must be > 0"):
            node.run(
                free_vram_gb=0.0,
                total_vram_gb=0.0,
                device_index=0,
                refresh=True,
            )

    def test_negative_free_raises(self):
        node = PSN_VRAM_Query()
        with pytest.raises(ValueError, match="must be >= 0"):
            node.run(
                free_vram_gb=-1.0,
                total_vram_gb=96.0,
                device_index=0,
                refresh=True,
            )

    def test_non_numeric_input_raises(self):
        node = PSN_VRAM_Query()
        with pytest.raises(ValueError, match="must be a number"):
            node.run(
                free_vram_gb="48",
                total_vram_gb=96.0,
                device_index=0,
                refresh=True,
            )

    def test_nan_input_raises(self):
        node = PSN_VRAM_Query()
        with pytest.raises(ValueError, match="finite"):
            node.run(
                free_vram_gb=float("nan"),
                total_vram_gb=96.0,
                device_index=0,
                refresh=True,
            )

    def test_negative_device_index_raises(self):
        node = PSN_VRAM_Query()
        with pytest.raises(ValueError, match="device_index must be >= 0"):
            node.run(
                free_vram_gb=48.0,
                total_vram_gb=96.0,
                device_index=-1,
                refresh=True,
            )

    def test_bool_device_index_raises(self):
        node = PSN_VRAM_Query()
        with pytest.raises(ValueError, match="not a bool"):
            node.run(
                free_vram_gb=48.0,
                total_vram_gb=96.0,
                device_index=True,
                refresh=True,
            )


# ---------------------------------------------------------------------------
# PSN_Pipeline_Selector tests
# ---------------------------------------------------------------------------

class TestPSNPipelineSelector:
    def test_selects_heavy_pipeline(self):
        node = PSN_Pipeline_Selector()
        pid, reason = node.run(
            free_vram_gb=90.0,
            threshold_light=10.0,
            threshold_heavy=50.0,
            pipeline_light_id="sdxl",
            pipeline_heavy_id="video",
        )
        assert pid == "video"
        assert "heavy" in reason

    def test_selects_light_pipeline(self):
        node = PSN_Pipeline_Selector()
        pid, reason = node.run(
            free_vram_gb=30.0,
            threshold_light=10.0,
            threshold_heavy=50.0,
            pipeline_light_id="sdxl",
            pipeline_heavy_id="video",
        )
        assert pid == "sdxl"
        assert "light" in reason

    def test_selects_fallback_pipeline(self):
        node = PSN_Pipeline_Selector()
        pid, reason = node.run(
            free_vram_gb=5.0,
            threshold_light=10.0,
            threshold_heavy=50.0,
            pipeline_light_id="sdxl",
            pipeline_heavy_id="video",
        )
        assert pid == _FALLBACK_PIPELINE_ID
        assert "fallback" in reason

    def test_boundary_at_heavy_threshold(self):
        """free == threshold_heavy should NOT select heavy (strict >)."""
        node = PSN_Pipeline_Selector()
        pid, _ = node.run(
            free_vram_gb=50.0,
            threshold_light=10.0,
            threshold_heavy=50.0,
            pipeline_light_id="sdxl",
            pipeline_heavy_id="video",
        )
        assert pid == "sdxl"

    def test_boundary_at_light_threshold(self):
        """free == threshold_light should NOT select light (strict >)."""
        node = PSN_Pipeline_Selector()
        pid, _ = node.run(
            free_vram_gb=10.0,
            threshold_light=10.0,
            threshold_heavy=50.0,
            pipeline_light_id="sdxl",
            pipeline_heavy_id="video",
        )
        assert pid == _FALLBACK_PIPELINE_ID

    def test_light_geq_heavy_raises(self):
        node = PSN_Pipeline_Selector()
        with pytest.raises(ValueError, match="must be <"):
            node.run(
                free_vram_gb=30.0,
                threshold_light=50.0,
                threshold_heavy=50.0,
                pipeline_light_id="sdxl",
                pipeline_heavy_id="video",
            )

    def test_empty_pipeline_id_raises(self):
        node = PSN_Pipeline_Selector()
        with pytest.raises(ValueError, match="non-empty"):
            node.run(
                free_vram_gb=30.0,
                threshold_light=10.0,
                threshold_heavy=50.0,
                pipeline_light_id="   ",
                pipeline_heavy_id="video",
            )

    def test_non_string_pipeline_id_raises(self):
        node = PSN_Pipeline_Selector()
        with pytest.raises(ValueError, match="must be a string"):
            node.run(
                free_vram_gb=30.0,
                threshold_light=10.0,
                threshold_heavy=50.0,
                pipeline_light_id=123,
                pipeline_heavy_id="video",
            )

    def test_negative_free_raises(self):
        node = PSN_Pipeline_Selector()
        with pytest.raises(ValueError, match="must be >= 0"):
            node.run(
                free_vram_gb=-5.0,
                threshold_light=10.0,
                threshold_heavy=50.0,
                pipeline_light_id="sdxl",
                pipeline_heavy_id="video",
            )

    def test_inf_free_raises(self):
        node = PSN_Pipeline_Selector()
        with pytest.raises(ValueError, match="finite"):
            node.run(
                free_vram_gb=float("inf"),
                threshold_light=10.0,
                threshold_heavy=50.0,
                pipeline_light_id="sdxl",
                pipeline_heavy_id="video",
            )

    def test_custom_pipeline_ids(self):
        node = PSN_Pipeline_Selector()
        pid, _ = node.run(
            free_vram_gb=90.0,
            threshold_light=10.0,
            threshold_heavy=50.0,
            pipeline_light_id="my-light",
            pipeline_heavy_id="my-heavy",
        )
        assert pid == "my-heavy"

    def test_zero_free_selects_fallback(self):
        node = PSN_Pipeline_Selector()
        pid, _ = node.run(
            free_vram_gb=0.0,
            threshold_light=10.0,
            threshold_heavy=50.0,
            pipeline_light_id="sdxl",
            pipeline_heavy_id="video",
        )
        assert pid == _FALLBACK_PIPELINE_ID
