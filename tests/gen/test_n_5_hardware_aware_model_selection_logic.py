"""
Tests for psn_nodes.gen.n_5_hardware_aware_model_selection_logic
"""

import pytest
from psn_nodes.gen.n_5_hardware_aware_model_selection_logic import (
    PSN_VRAM_Checker,
    PSN_Model_Selector,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


class TestPSN_VRAM_Checker:
    def setup_method(self):
        self.node = PSN_VRAM_Checker()

    def test_sufficient_vram_returns_true(self):
        has_vram, free_mb, reason = self.node.run(free_vram_mb=8192, threshold_mb=4096)
        assert has_vram is True
        assert free_mb == 8192
        assert "meets threshold" in reason

    def test_insufficient_vram_returns_false(self):
        has_vram, free_mb, reason = self.node.run(free_vram_mb=2048, threshold_mb=4096)
        assert has_vram is False
        assert free_mb == 2048
        assert "below threshold" in reason

    def test_exact_threshold_returns_true(self):
        has_vram, free_mb, reason = self.node.run(free_vram_mb=4096, threshold_mb=4096)
        assert has_vram is True

    def test_zero_vram_with_zero_threshold(self):
        has_vram, free_mb, reason = self.node.run(free_vram_mb=0, threshold_mb=0)
        assert has_vram is True

    def test_zero_vram_with_positive_threshold(self):
        has_vram, free_mb, reason = self.node.run(free_vram_mb=0, threshold_mb=1)
        assert has_vram is False

    def test_negative_vram_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            self.node.run(free_vram_mb=-1, threshold_mb=100)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            self.node.run(free_vram_mb=100, threshold_mb=-1)

    def test_non_integer_input_raises(self):
        with pytest.raises(ValueError, match="integers"):
            self.node.run(free_vram_mb=100.5, threshold_mb=100)


class TestPSN_Model_Selector:
    def setup_method(self):
        self.node = PSN_Model_Selector()

    def test_selects_large_when_vram_available(self):
        selected, reason = self.node.run(
            has_vram=True, model_small="small", model_large="large"
        )
        assert selected == "large"
        assert "large model" in reason

    def test_selects_small_when_vram_unavailable(self):
        selected, reason = self.node.run(
            has_vram=False, model_small="small", model_large="large"
        )
        assert selected == "small"
        assert "small model" in reason

    def test_non_boolean_has_vram_raises(self):
        with pytest.raises(ValueError, match="boolean"):
            self.node.run(has_vram=1, model_small="s", model_large="l")

    def test_non_string_model_raises(self):
        with pytest.raises(ValueError, match="strings"):
            self.node.run(has_vram=True, model_small=123, model_large="l")

    def test_empty_string_models_allowed(self):
        selected, reason = self.node.run(
            has_vram=False, model_small="", model_large="large"
        )
        assert selected == ""


class TestNodeMappings:
    def test_node_class_mappings_present(self):
        assert "PSN_VRAM_Checker" in NODE_CLASS_MAPPINGS
        assert "PSN_Model_Selector" in NODE_CLASS_MAPPINGS

    def test_display_name_mappings_present(self):
        assert "PSN_VRAM_Checker" in NODE_DISPLAY_NAME_MAPPINGS
        assert "PSN_Model_Selector" in NODE_DISPLAY_NAME_MAPPINGS

    def test_input_types_return_dict(self):
        it = PSN_VRAM_Checker.INPUT_TYPES()
        assert "required" in it
        assert "free_vram_mb" in it["required"]
        assert "threshold_mb" in it["required"]

        it2 = PSN_Model_Selector.INPUT_TYPES()
        assert "has_vram" in it2["required"]
        assert "model_small" in it2["required"]
        assert "model_large" in it2["required"]
