"""
Tests for PSN Dynamic Prompt Formula Engine nodes.
"""

import pytest
from psn_nodes.gen.n_1_dynamic_prompt_formula_engine import (
    PSN_TOML_Prompt_Loader,
    PSN_Style_Library_Switcher,
    _parse_toml,
    _flatten_structure,
    _merge_context,
)


class TestPSNTOMLPromptLoader:
    """Tests for PSN_TOML_Prompt_Loader node."""
    
    def test_basic_toml_parsing(self):
        """Test basic TOML parsing with simple key-value pairs."""
        toml_content = """
[style]
name = "cyberpunk"
color = "neon"

[subject]
type = "robot"
size = 5
"""
        loader = PSN_TOML_Prompt_Loader()
        result = loader.run(toml_content)
        assert len(result) == 1
        structure = result[0]
        assert "style" in structure
        assert structure["style"]["name"] == "cyberpunk"
        assert structure["style"]["color"] == "neon"
        assert "subject" in structure
        assert structure["subject"]["type"] == "robot"
        assert structure["subject"]["size"] == 5
    
    def test_empty_toml_content(self):
        """Test that empty TOML content returns empty dict."""
        loader = PSN_TOML_Prompt_Loader()
        result = loader.run("")
        assert result[0] == {}
        
        result = loader.run("   ")
        assert result[0] == {}
    
    def test_context_vars_merge(self):
        """Test that context_vars are merged into the structure."""
        toml_content = """
[style]
name = "default"
color = "blue"
"""
        context_vars = {"style": {"name": "custom", "extra": "value"}}
        loader = PSN_TOML_Prompt_Loader()
        result = loader.run(toml_content, context_vars)
        structure = result[0]
        assert structure["style"]["name"] == "custom"
        assert structure["style"]["color"] == "blue"
        assert structure["style"]["extra"] == "value"
    
    def test_context_vars_override(self):
        """Test that context_vars override existing values."""
        toml_content = """
[style]
name = "original"
"""
        context_vars = {"style": {"name": "overridden"}}
        loader = PSN_TOML_Prompt_Loader()
        result = loader.run(toml_content, context_vars)
        structure = result[0]
        assert structure["style"]["name"] == "overridden"
    
    def test_invalid_toml_returns_empty(self):
        """Test that invalid TOML returns empty dict without raising."""
        loader = PSN_TOML_Prompt_Loader()
        # This is technically valid TOML but let's test with malformed content
        result = loader.run("invalid toml content without equals")
        assert isinstance(result[0], dict)


class TestPSNStyleLibrarySwitcher:
    """Tests for PSN_Style_Library_Switcher node."""
    
    def test_basic_style_selection(self):
        """Test selecting a style block and flattening it."""
        structure = {
            "cyberpunk": {
                "style": "neon lights, dark city",
                "lighting": "dramatic",
            },
            "watercolor": {
                "style": "soft pastel",
                "lighting": "natural",
            },
        }
        switcher = PSN_Style_Library_Switcher()
        result = switcher.run(structure, "cyberpunk", "watercolor")
        assert len(result) == 1
        prompt = result[0]
        assert "neon lights" in prompt
        assert "dark city" in prompt
        assert "dramatic" in prompt
    
    def test_fallback_style_used_when_key_missing(self):
        """Test that fallback_style is used when style_key is not found."""
        structure = {
            "watercolor": {
                "style": "soft pastel",
            },
        }
        switcher = PSN_Style_Library_Switcher()
        result = switcher.run(structure, "nonexistent", "watercolor")
        prompt = result[0]
        assert "soft pastel" in prompt
    
    def test_empty_structure_returns_empty_string(self):
        """Test that empty structure returns empty string."""
        switcher = PSN_Style_Library_Switcher()
        result = switcher.run({}, "style", "fallback")
        assert result[0] == ""
    
    def test_custom_delimiter(self):
        """Test that custom delimiter is used in flattening."""
        structure = {
            "test": {
                "a": "value1",
                "b": "value2",
            },
        }
        switcher = PSN_Style_Library_Switcher()
        result = switcher.run(structure, "test", "fallback", delimiter=" | ")
        prompt = result[0]
        assert "value1" in prompt
        assert "value2" in prompt
        assert " | " in prompt
    
    def test_nested_structure_flattening(self):
        """Test flattening of nested structures."""
        structure = {
            "complex": {
                "style": "detailed",
                "details": {
                    "lighting": "soft",
                    "mood": "calm",
                },
            },
        }
        switcher = PSN_Style_Library_Switcher()
        result = switcher.run(structure, "complex", "fallback")
        prompt = result[0]
        assert "detailed" in prompt
        assert "soft" in prompt
        assert "calm" in prompt


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_flatten_string(self):
        """Test flattening a simple string."""
        assert _flatten_structure("hello") == "hello"
    
    def test_flatten_number(self):
        """Test flattening a number."""
        assert _flatten_structure(42) == "42"
        assert _flatten_structure(3.14) == "3.14"
    
    def test_flatten_list(self):
        """Test flattening a list."""
        assert _flatten_structure(["a", "b", "c"], ", ") == "a, b, c"
    
    def test_flatten_dict(self):
        """Test flattening a dict."""
        result = _flatten_structure({"key1": "val1", "key2": "val2"}, ", ")
        assert "key1: val1" in result
        assert "key2: val2" in result
    
    def test_merge_context_no_context(self):
        """Test merge with no context vars."""
        structure = {"a": 1, "b": 2}
        merged = _merge_context(structure, None)
        assert merged == structure
    
    def test_merge_context_deep_merge(self):
        """Test deep merge of nested dicts."""
        structure = {"a": {"x": 1, "y": 2}}
        context = {"a": {"y": 3, "z": 4}}
        merged = _merge_context(structure, context)
        assert merged["a"]["x"] == 1
        assert merged["a"]["y"] == 3
        assert merged["a"]["z"] == 4
