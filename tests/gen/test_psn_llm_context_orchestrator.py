"""Tests for PSN_LLM_Context_Orchestrator."""

import pytest
from psn_nodes.gen.psn_llm_context_orchestrator import (
    PSN_LLM_Context_Orchestrator,
    _validate_provider,
    _validate_model_id,
    _sanitize_context,
    _default_context,
    ALLOWED_PROVIDERS,
)


def test_valid_provider_update_preserves_history():
    """Changing provider should update provider_type and model_id, keep history."""
    node = PSN_LLM_Context_Orchestrator()
    ctx = {
        "provider_type": "local",
        "model_id": "old-model",
        "history": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
        "metadata": {"key": "value"},
    }
    (updated,) = node.run("cloud_openai", "gpt-4", context=ctx)
    assert updated["provider_type"] == "cloud_openai"
    assert updated["model_id"] == "gpt-4"
    assert updated["history"] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert updated["metadata"] == {"key": "value"}


def test_default_context_when_none_provided():
    """When context is None, a default context is created with new settings."""
    node = PSN_LLM_Context_Orchestrator()
    (updated,) = node.run("cloud_gemini", "gemini-pro", context=None)
    assert updated["provider_type"] == "cloud_gemini"
    assert updated["model_id"] == "gemini-pro"
    assert updated["history"] == []
    assert updated["metadata"] == {}


def test_invalid_provider_raises():
    """Invalid provider_type should raise ValueError."""
    node = PSN_LLM_Context_Orchestrator()
    with pytest.raises(ValueError, match="not in allow-list"):
        node.run("cloud_azure", "some-model", context=None)


def test_empty_model_id_raises():
    """Empty or whitespace-only model_id should raise ValueError."""
    node = PSN_LLM_Context_Orchestrator()
    with pytest.raises(ValueError, match="non-empty"):
        node.run("local", "   ", context=None)


def test_non_string_model_id_raises():
    """Non-string model_id should raise ValueError."""
    node = PSN_LLM_Context_Orchestrator()
    with pytest.raises(ValueError, match="must be a string"):
        node.run("local", 12345, context=None)


def test_corrupt_history_raises():
    """History entries that are not dicts should raise ValueError."""
    node = PSN_LLM_Context_Orchestrator()
    ctx = {
        "provider_type": "local",
        "model_id": "m",
        "history": ["not-a-dict"],
        "metadata": {},
    }
    with pytest.raises(ValueError, match="must be a dict"):
        node.run("local", "m", context=ctx)


def test_history_entry_missing_fields_raises():
    """History entry with non-string role or content should raise."""
    node = PSN_LLM_Context_Orchestrator()
    ctx = {
        "provider_type": "local",
        "model_id": "m",
        "history": [{"role": 123, "content": "hi"}],
        "metadata": {},
    }
    with pytest.raises(ValueError, match="string 'role' and 'content'"):
        node.run("local", "m", context=ctx)


def test_metadata_preserved_across_updates():
    """Metadata should be preserved when updating provider."""
    node = PSN_LLM_Context_Orchestrator()
    ctx = {
        "provider_type": "local",
        "model_id": "a",
        "history": [],
        "metadata": {"temperature": 0.7, "max_tokens": 100},
    }
    (updated,) = node.run("cloud_openai", "gpt-4", context=ctx)
    assert updated["metadata"] == {"temperature": 0.7, "max_tokens": 100}


def test_validate_provider_helper():
    """Direct test of _validate_provider."""
    ok, reason = _validate_provider("local")
    assert ok is True
    ok, reason = _validate_provider("cloud_openai")
    assert ok is True
    ok, reason = _validate_provider("cloud_gemini")
    assert ok is True
    ok, reason = _validate_provider("invalid")
    assert ok is False
    ok, reason = _validate_provider(123)
    assert ok is False


def test_validate_model_id_helper():
    """Direct test of _validate_model_id."""
    ok, reason = _validate_model_id("gpt-4")
    assert ok is True
    ok, reason = _validate_model_id("")
    assert ok is False
    ok, reason = _validate_model_id("   ")
    assert ok is False
    ok, reason = _validate_model_id(None)
    assert ok is False


def test_sanitize_context_none_returns_default():
    """_sanitize_context(None) should return default context."""
    ctx, err = _sanitize_context(None)
    assert err is None
    assert ctx == _default_context()


def test_sanitize_context_non_dict_raises():
    """_sanitize_context with non-dict should return error."""
    ctx, err = _sanitize_context("not a dict")
    assert ctx is None
    assert "must be a dict" in err


def test_all_allowed_providers_accepted():
    """All providers in ALLOWED_PROVIDERS should be accepted."""
    node = PSN_LLM_Context_Orchestrator()
    for p in ALLOWED_PROVIDERS:
        (updated,) = node.run(p, "test-model", context=None)
        assert updated["provider_type"] == p
