"""Tests for PSN_Dynamic_Model_Selector node."""

import pytest
from psn_nodes.gen.psn_dynamic_model_selector import (
    PSN_Dynamic_Model_Selector,
    _find_model,
    _extract_model_name,
    MATCH_MODES,
    ON_MISSING_MODES,
)


class TestExtractModelName:
    """Tests for the _extract_model_name helper function."""
    
    def test_basic_path(self):
        assert _extract_model_name("/models/sdxl_base.safetensors") == "sdxl_base"
    
    def test_windows_path(self):
        assert _extract_model_name("C:\\models\\sdxl_base.safetensors") == "sdxl_base"
    
    def test_no_extension(self):
        assert _extract_model_name("/models/sdxl_base") == "sdxl_base"
    
    def test_ckpt_extension(self):
        assert _extract_model_name("/models/model.ckpt") == "model"
    
    def test_empty_string(self):
        assert _extract_model_name("") == ""
    
    def test_none_input(self):
        assert _extract_model_name(None) == ""
    
    def test_multiple_extensions(self):
        assert _extract_model_name("/models/model.safetensors.bak") == "model.safetensors.bak"


class TestFindModel:
    """Tests for the _find_model helper function."""
    
    def test_exact_match(self):
        models = ["/models/sdxl_base.safetensors", "/models/sd15.safetensors"]
        path, name, reason = _find_model(models, "sdxl_base", "exact")
        assert path == "/models/sdxl_base.safetensors"
        assert name == "sdxl_base"
        assert "Exact" in reason
    
    def test_exact_match_no_match(self):
        models = ["/models/sdxl_base.safetensors", "/models/sd15.safetensors"]
        path, name, reason = _find_model(models, "nonexistent", "exact")
        assert path is None
        assert name is None
        assert "No exact match" in reason
    
    def test_case_insensitive_match(self):
        models = ["/models/sdxl_base.safetensors", "/models/sd15.safetensors"]
        path, name, reason = _find_model(models, "SDXL_BASE", "case_insensitive")
        assert path == "/models/sdxl_base.safetensors"
        assert name == "sdxl_base"
        assert "Case-insensitive" in reason
    
    def test_contains_match(self):
        models = ["/models/sdxl_base_v2.safetensors", "/models/sd15.safetensors"]
        path, name, reason = _find_model(models, "sdxl", "contains")
        assert path == "/models/sdxl_base_v2.safetensors"
        assert name == "sdxl_base_v2"
        assert "Contains" in reason
    
    def test_empty_model_list(self):
        path, name, reason = _find_model([], "sdxl", "exact")
        assert path is None
        assert "empty" in reason.lower()
    
    def test_empty_selector_value(self):
        models = ["/models/sdxl_base.safetensors"]
        path, name, reason = _find_model(models, "", "exact")
        assert path is None
        assert "empty" in reason.lower()
    
    def test_invalid_match_mode(self):
        models = ["/models/sdxl_base.safetensors"]
        path, name, reason = _find_model(models, "sdxl", "invalid_mode")
        assert path is None
        assert "Unknown match mode" in reason


class TestPSNDynamicModelSelector:
    """Tests for the PSN_Dynamic_Model_Selector node class."""
    
    def setup_method(self):
        self.node = PSN_Dynamic_Model_Selector()
    
    def test_input_types_structure(self):
        input_types = PSN_Dynamic_Model_Selector.INPUT_TYPES()
        assert "required" in input_types
        assert "model_list" in input_types["required"]
        assert "selector_key" in input_types["required"]
        assert "selector_value" in input_types["required"]
        assert "match_mode" in input_types["required"]
        assert "on_missing" in input_types["required"]
    
    def test_return_types(self):
        assert PSN_Dynamic_Model_Selector.RETURN_TYPES == ("STRING", "STRING", "BOOLEAN", "STRING")
        assert PSN_Dynamic_Model_Selector.RETURN_NAMES == ("model_path", "model_name", "matched", "reason")
    
    def test_exact_match_success(self):
        model_list = ["/models/sdxl_base.safetensors", "/models/sd15.safetensors"]
        model_path, model_name, matched, reason = self.node.run(
            model_list=model_list,
            selector_key="model_name",
            selector_value="sdxl_base",
            match_mode="exact",
            on_missing="error"
        )
        assert model_path == "/models/sdxl_base.safetensors"
        assert model_name == "sdxl_base"
        assert matched is True
        assert "Exact" in reason
    
    def test_no_match_error(self):
        model_list = ["/models/sdxl_base.safetensors"]
        with pytest.raises(ValueError, match="Model not found"):
            self.node.run(
                model_list=model_list,
                selector_key="model_name",
                selector_value="nonexistent",
                match_mode="exact",
                on_missing="error"
            )
    
    def test_no_match_first_fallback(self):
        model_list = ["/models/sdxl_base.safetensors", "/models/sd15.safetensors"]
        model_path, model_name, matched, reason = self.node.run(
            model_list=model_list,
            selector_key="model_name",
            selector_value="nonexistent",
            match_mode="exact",
            on_missing="first"
        )
        assert model_path == "/models/sdxl_base.safetensors"
        assert model_name == "sdxl_base"
        assert matched is False
        assert "first model" in reason
    
    def test_no_match_empty_fallback(self):
        model_list = ["/models/sdxl_base.safetensors"]
        model_path, model_name, matched, reason = self.node.run(
            model_list=model_list,
            selector_key="model_name",
            selector_value="nonexistent",
            match_mode="exact",
            on_missing="empty"
        )
        assert model_path == ""
        assert model_name == ""
        assert matched is False
    
    def test_case_insensitive_match(self):
        model_list = ["/models/sdxl_base.safetensors"]
        model_path, model_name, matched, reason = self.node.run(
            model_list=model_list,
            selector_key="model_name",
            selector_value="SDXL_BASE",
            match_mode="case_insensitive",
            on_missing="error"
        )
        assert model_path == "/models/sdxl_base.safetensors"
        assert model_name == "sdxl_base"
        assert matched is True
    
    def test_contains_match(self):
        model_list = ["/models/sdxl_base_v2.safetensors", "/models/sd15.safetensors"]
        model_path, model_name, matched, reason = self.node.run(
            model_list=model_list,
            selector_key="model_name",
            selector_value="sdxl",
            match_mode="contains",
            on_missing="error"
        )
        assert model_path == "/models/sdxl_base_v2.safetensors"
        assert model_name == "sdxl_base_v2"
        assert matched is True
    
    def test_invalid_model_list_type(self):
        with pytest.raises(ValueError, match="model_list must be a list"):
            self.node.run(
                model_list="not_a_list",
                selector_key="model_name",
                selector_value="sdxl",
                match_mode="exact",
                on_missing="error"
            )
    
    def test_invalid_selector_key_type(self):
        with pytest.raises(ValueError, match="selector_key must be a string"):
            self.node.run(
                model_list=["/models/sdxl.safetensors"],
                selector_key=123,
                selector_value="sdxl",
                match_mode="exact",
                on_missing="error"
            )
    
    def test_invalid_match_mode(self):
        with pytest.raises(ValueError, match="match_mode must be one of"):
            self.node.run(
                model_list=["/models/sdxl.safetensors"],
                selector_key="model_name",
                selector_value="sdxl",
                match_mode="invalid",
                on_missing="error"
            )
    
    def test_invalid_on_missing_mode(self):
        with pytest.raises(ValueError, match="on_missing must be one of"):
            self.node.run(
                model_list=["/models/sdxl.safetensors"],
                selector_key="model_name",
                selector_value="sdxl",
                match_mode="exact",
                on_missing="invalid"
            )
    
    def test_default_model_used_when_no_match(self):
        model_list = ["/models/sdxl_base.safetensors"]
        model_path, model_name, matched, reason = self.node.run(
            model_list=model_list,
            selector_key="model_name",
            selector_value="nonexistent",
            match_mode="exact",
            on_missing="first",
            default_model="/models/default.safetensors"
        )
        assert model_path == "/models/default.safetensors"
        assert model_name == "default"
        assert matched is False
        assert "default model" in reason
    
    def test_empty_model_list_with_first_fallback(self):
        model_path, model_name, matched, reason = self.node.run(
            model_list=[],
            selector_key="model_name",
            selector_value="sdxl",
            match_mode="exact",
            on_missing="first"
        )
        assert model_path == ""
        assert model_name == ""
        assert matched is False
        assert "empty" in reason.lower()
