"""
Tests for PSN_ELLA_Semantic_Connector.

All tests use only the Python standard library. No files, no network,
no torch, no comfy imports.
"""

import json
import pytest

from psn_nodes.gen.n_5_dynamic_semantic_adaptation_with_ella import (
    PSN_ELLA_Semantic_Connector,
    _validate_sigma,
    _validate_strength,
    _validate_model,
    _redact_sensitive,
    _deterministic_transform,
    _format_request_payload,
    _parse_response,
    _ella_rate_limiter,
    ALLOWED_ELLA_MODELS,
)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the rate limiter before each test to avoid cross-test interference."""
    _ella_rate_limiter.reset()
    yield


class TestValidation:
    def test_validate_sigma_valid(self):
        ok, reason = _validate_sigma(0.5)
        assert ok is True
        assert reason == "ok"

    def test_validate_sigma_negative(self):
        ok, reason = _validate_sigma(-0.1)
        assert ok is False
        assert "non-negative" in reason

    def test_validate_sigma_nan(self):
        ok, reason = _validate_sigma(float("nan"))
        assert ok is False
        assert "finite" in reason

    def test_validate_sigma_inf(self):
        ok, reason = _validate_sigma(float("inf"))
        assert ok is False
        assert "finite" in reason

    def test_validate_sigma_non_numeric(self):
        ok, reason = _validate_sigma("0.5")
        assert ok is False
        assert "number" in reason

    def test_validate_strength_valid(self):
        ok, reason = _validate_strength(0.7)
        assert ok is True

    def test_validate_strength_out_of_range_high(self):
        ok, reason = _validate_strength(1.5)
        assert ok is False
        assert "[0, 1]" in reason

    def test_validate_strength_out_of_range_low(self):
        ok, reason = _validate_strength(-0.1)
        assert ok is False
        assert "[0, 1]" in reason

    def test_validate_model_valid(self):
        ok, reason = _validate_model("ella_v1_small")
        assert ok is True

    def test_validate_model_not_in_allowlist(self):
        ok, reason = _validate_model("unknown_model")
        assert ok is False
        assert "allow-list" in reason

    def test_validate_model_non_string(self):
        ok, reason = _validate_model(123)
        assert ok is False
        assert "string" in reason


class TestRedaction:
    def test_redact_sensitive_fields(self):
        payload = {"api_key": "secret123", "sigma": 0.5, "token": "abc"}
        redacted = _redact_sensitive(payload)
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["token"] == "***REDACTED***"
        assert redacted["sigma"] == 0.5

    def test_redact_no_sensitive_fields(self):
        payload = {"sigma": 0.5, "strength": 0.3}
        redacted = _redact_sensitive(payload)
        assert redacted == payload

    def test_redact_nested_sensitive_fields(self):
        payload = {"conditioning": {"api_key": "nested_secret", "value": 1.0}}
        redacted = _redact_sensitive(payload)
        assert redacted["conditioning"]["api_key"] == "***REDACTED***"
        assert redacted["conditioning"]["value"] == 1.0


class TestDeterministicTransform:
    def test_transform_is_deterministic(self):
        cond = {"a": 1.0, "b": 2.0}
        result1 = _deterministic_transform(cond, 0.5, 0.5, "ella_v1_small")
        result2 = _deterministic_transform(cond, 0.5, 0.5, "ella_v1_small")
        assert result1 == result2

    def test_transform_changes_with_sigma(self):
        cond = {"a": 1.0}
        r1 = _deterministic_transform(cond, 0.1, 0.5, "ella_v1_small")
        r2 = _deterministic_transform(cond, 0.9, 0.5, "ella_v1_small")
        assert r1["a"] != r2["a"]

    def test_transform_changes_with_strength(self):
        cond = {"a": 1.0}
        r1 = _deterministic_transform(cond, 0.5, 0.1, "ella_v1_small")
        r2 = _deterministic_transform(cond, 0.5, 0.9, "ella_v1_small")
        assert r1["a"] != r2["a"]

    def test_transform_preserves_non_numeric(self):
        cond = {"a": 1.0, "label": "cat"}
        result = _deterministic_transform(cond, 0.5, 0.5, "ella_v1_small")
        assert result["label"] == "cat"

    def test_transform_zero_strength_no_scale_change(self):
        cond = {"a": 10.0}
        result = _deterministic_transform(cond, 0.0, 0.0, "ella_v1_small")
        # With strength=0, scale=1.0, sigma_shift=0.0, so value unchanged
        assert result["a"] == 10.0


class TestFormatRequestPayload:
    def test_format_includes_required_fields(self):
        payload = _format_request_payload({"a": 1}, 0.5, 0.3, "ella_v1_small")
        parsed = json.loads(payload)
        assert parsed["type"] == "ella_semantic_connector"
        assert parsed["model"] == "ella_v1_small"
        assert parsed["sigma"] == 0.5
        assert parsed["strength"] == 0.3
        assert parsed["conditioning"] == {"a": 1}

    def test_format_redacts_sensitive(self):
        payload = _format_request_payload({"api_key": "xyz"}, 0.5, 0.3, "ella_v1_small")
        parsed = json.loads(payload)
        assert parsed["conditioning"]["api_key"] == "***REDACTED***"


class TestParseResponse:
    def test_parse_valid_response(self):
        resp = json.dumps({"conditioning": {"a": 1.0}, "status": "ok"})
        ok, result = _parse_response(resp)
        assert ok is True
        assert result["conditioning"] == {"a": 1.0}

    def test_parse_invalid_json(self):
        ok, result = _parse_response("not json")
        assert ok is False
        assert "invalid JSON" in result

    def test_parse_missing_conditioning(self):
        resp = json.dumps({"status": "ok"})
        ok, result = _parse_response(resp)
        assert ok is False
        assert "conditioning" in result

    def test_parse_non_string(self):
        ok, result = _parse_response(123)
        assert ok is False
        assert "string" in result


class TestNodeRun:
    def test_run_success(self):
        node = PSN_ELLA_Semantic_Connector()
        cond_json = json.dumps({"a": 1.0, "b": 2.0})
        result_cond, status, request_payload = node.run(
            conditioning=cond_json,
            sigma=0.5,
            ella_model="ella_v1_small",
            strength=0.5,
        )
        assert status == "ok"
        parsed_cond = json.loads(result_cond)
        assert "a" in parsed_cond
        assert "b" in parsed_cond
        # Request payload should be valid JSON
        parsed_req = json.loads(request_payload)
        assert parsed_req["model"] == "ella_v1_small"

    def test_run_invalid_sigma(self):
        node = PSN_ELLA_Semantic_Connector()
        result_cond, status, _ = node.run(
            conditioning="{}",
            sigma=-1.0,
            ella_model="ella_v1_small",
            strength=0.5,
        )
        assert status.startswith("error:")
        assert "non-negative" in status

    def test_run_invalid_strength(self):
        node = PSN_ELLA_Semantic_Connector()
        result_cond, status, _ = node.run(
            conditioning="{}",
            sigma=0.5,
            ella_model="ella_v1_small",
            strength=2.0,
        )
        assert status.startswith("error:")
        assert "[0, 1]" in status

    def test_run_invalid_model(self):
        node = PSN_ELLA_Semantic_Connector()
        result_cond, status, _ = node.run(
            conditioning="{}",
            sigma=0.5,
            ella_model="bad_model",
            strength=0.5,
        )
        assert status.startswith("error:")
        assert "allow-list" in status

    def test_run_invalid_conditioning_json(self):
        node = PSN_ELLA_Semantic_Connector()
        result_cond, status, _ = node.run(
            conditioning="not valid json",
            sigma=0.5,
            ella_model="ella_v1_small",
            strength=0.5,
        )
        assert status.startswith("error:")
        assert "invalid JSON" in status

    def test_run_conditioning_not_object(self):
        node = PSN_ELLA_Semantic_Connector()
        result_cond, status, _ = node.run(
            conditioning="[1, 2, 3]",
            sigma=0.5,
            ella_model="ella_v1_small",
            strength=0.5,
        )
        assert status.startswith("error:")
        assert "JSON object" in status

    def test_run_rate_limit(self):
        node = PSN_ELLA_Semantic_Connector()
        # Exhaust the rate limiter
        for _ in range(10):
            node.run(
                conditioning="{}",
                sigma=0.5,
                ella_model="ella_v1_small",
                strength=0.5,
            )
        # Next call should be rate-limited
        result_cond, status, _ = node.run(
            conditioning="{}",
            sigma=0.5,
            ella_model="ella_v1_small",
            strength=0.5,
        )
        assert status == "error: rate limit exceeded"

    def test_run_conditioning_changes_with_sigma(self):
        node = PSN_ELLA_Semantic_Connector()
        cond_json = json.dumps({"a": 1.0})
        r1, s1, _ = node.run(cond_json, 0.1, "ella_v1_small", 0.5)
        r2, s2, _ = node.run(cond_json, 0.9, "ella_v1_small", 0.5)
        assert s1 == "ok" and s2 == "ok"
        c1 = json.loads(r1)
        c2 = json.loads(r2)
        assert c1["a"] != c2["a"]

    def test_run_empty_conditioning(self):
        node = PSN_ELLA_Semantic_Connector()
        result_cond, status, _ = node.run(
            conditioning="{}",
            sigma=0.5,
            ella_model="ella_v1_small",
            strength=0.5,
        )
        assert status == "ok"
        parsed = json.loads(result_cond)
        assert parsed == {}
