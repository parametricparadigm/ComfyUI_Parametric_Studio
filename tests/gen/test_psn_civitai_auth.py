"""Tests for psn_nodes.gen.psn_civitai_auth (pure-logic Civitai auth node)."""

import pytest

from psn_nodes.gen.psn_civitai_auth import (
    PSN_Civitai_Auth,
    CivitaiConfig,
    build_config,
    redact_token,
    _validate_endpoint,
    _validate_token,
    ALLOWED_ENDPOINTS,
)


def test_config_creation_valid():
    cfg = build_config("abcdef123456", "production")
    assert isinstance(cfg, CivitaiConfig)
    assert cfg.is_valid() is True
    assert cfg.endpoint == "production"
    assert cfg.token_valid is True
    assert cfg.endpoint_valid is True
    assert cfg.token_redacted == "ab" + "*" * 8 + "56"


def test_endpoint_allowlist_rejects_unknown():
    ok, why = _validate_endpoint("https://evil.example.com")
    assert ok is False
    assert "allow-list" in why
    cfg = build_config("abcdef123456", "https://evil.example.com")
    assert cfg.is_valid() is False
    assert cfg.endpoint_valid is False


def test_endpoint_empty_rejected():
    ok, why = _validate_endpoint("   ")
    assert ok is False
    assert "empty" in why


def test_token_too_short_rejected():
    ok, why = _validate_token("abc")
    assert ok is False
    assert "too short" in why
    cfg = build_config("abc", "production")
    assert cfg.is_valid() is False
    assert cfg.token_valid is False


def test_token_with_whitespace_rejected():
    ok, why = _validate_token("abcd efgh")
    assert ok is False
    assert "whitespace" in why


def test_token_non_string_rejected():
    ok, why = _validate_token(12345)
    assert ok is False
    assert "string" in why
    cfg = build_config(12345, "production")
    assert cfg.is_valid() is False
    assert cfg.token_redacted == "<invalid>"


def test_redact_short_token():
    assert redact_token("ab") == "**"
    assert redact_token("abcd") == "****"
    assert redact_token("abcdef") == "ab**ef"


def test_node_run_returns_config():
    node = PSN_Civitai_Auth()
    (cfg,) = node.run("abcdef123456", "staging")
    assert isinstance(cfg, CivitaiConfig)
    assert cfg.endpoint == "staging"
    assert cfg.is_valid() is True


def test_node_run_invalid_endpoint():
    node = PSN_Civitai_Auth()
    (cfg,) = node.run("abcdef123456", "bogus")
    assert cfg.is_valid() is False
    assert cfg.endpoint_valid is False


def test_config_to_dict_shape():
    cfg = build_config("abcdef123456", "local")
    d = cfg.to_dict()
    assert d["endpoint"] == "local"
    assert d["valid"] is True
    assert "token_redacted" in d
    assert "token_reason" in d
    assert "endpoint_reason" in d


def test_allowed_endpoints_constant():
    assert "production" in ALLOWED_ENDPOINTS
    assert "staging" in ALLOWED_ENDPOINTS
    assert "local" in ALLOWED_ENDPOINTS
