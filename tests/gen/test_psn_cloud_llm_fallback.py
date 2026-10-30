"""Tests for PSN_Cloud_LLM_Fallback node."""

import pytest
from psn_nodes.gen.psn_cloud_llm_fallback import (
    PSN_Cloud_LLM_Fallback,
    _estimate_complexity,
    _format_local_payload,
    _format_cloud_payload,
)


class TestEstimateComplexity:
    def test_empty_string_returns_zero(self):
        assert _estimate_complexity("") == 0.0

    def test_short_simple_prompt_low_complexity(self):
        score = _estimate_complexity("hello world")
        assert 0.0 <= score < 0.1

    def test_long_prompt_high_complexity(self):
        prompt = " ".join(["word"] * 60)
        score = _estimate_complexity(prompt)
        assert score > 0.5

    def test_keyword_density_increases_score(self):
        simple = " ".join(["word"] * 10)
        complex_prompt = " ".join(["analyze", "optimize", "debug", "refactor", "migrate", "word"] * 2)
        assert _estimate_complexity(complex_prompt) > _estimate_complexity(simple)

    def test_score_capped_at_one(self):
        prompt = " ".join(["analyze"] * 100)
        assert _estimate_complexity(prompt) <= 1.0

    def test_non_string_input_coerced(self):
        score = _estimate_complexity(12345)
        assert 0.0 <= score <= 1.0


class TestFormatPayloads:
    def test_local_payload_prefix(self):
        assert _format_local_payload("test") == "[LOCAL] test"

    def test_cloud_payload_prefix(self):
        assert _format_cloud_payload("test") == "[CLOUD] test"


class TestRoutingLogic:
    def setup_method(self):
        self.node = PSN_Cloud_LLM_Fallback()

    def test_simple_prompt_routes_local(self):
        response, source = self.node.run("hello", 0.5)
        assert source == "local"
        assert response.startswith("[LOCAL]")

    def test_complex_prompt_routes_cloud(self):
        prompt = " ".join(["analyze", "optimize", "debug", "refactor", "migrate", "scale", "benchmark", "profile", "diagnose", "troubleshoot"] * 3)
        response, source = self.node.run(prompt, 0.5)
        assert source == "cloud"
        assert response.startswith("[CLOUD]")

    def test_resource_guard_false_forces_cloud(self):
        response, source = self.node.run("hello", 0.5, resource_guard_ok=False)
        assert source == "cloud"
        assert response.startswith("[CLOUD]")

    def test_threshold_zero_always_cloud(self):
        response, source = self.node.run("hello", 0.0)
        assert source == "cloud"

    def test_threshold_one_always_local_when_guard_ok(self):
        response, source = self.node.run("hello", 1.0, resource_guard_ok=True)
        assert source == "local"

    def test_non_string_prompt_coerced(self):
        response, source = self.node.run(12345, 0.5)
        assert source in ("local", "cloud")
        assert isinstance(response, str)

    def test_invalid_threshold_clamped(self):
        response, source = self.node.run("hello", 5.0)
        assert source in ("local", "cloud")

    def test_invalid_resource_guard_coerced(self):
        response, source = self.node.run("hello", 0.5, resource_guard_ok="yes")
        assert source in ("local", "cloud")

    def test_boundary_complexity_equal_threshold_goes_local(self):
        # "hello world" has complexity well below 0.5, so with threshold 0.5 it goes local
        response, source = self.node.run("hello world", 0.5)
        assert source == "local"

    def test_boundary_complexity_above_threshold_goes_cloud(self):
        # Build a prompt with known complexity just above 0.5
        # 30 tokens, 0 keywords: 0.6 * (30/50) + 0.4 * 0 = 0.36
        # 40 tokens, 0 keywords: 0.6 * (40/50) + 0.4 * 0 = 0.48
        # 45 tokens, 0 keywords: 0.6 * (45/50) + 0.4 * 0 = 0.54
        prompt = " ".join(["word"] * 45)
        response, source = self.node.run(prompt, 0.5)
        assert source == "cloud"
