import json
import pytest
from psn_nodes.gen.n_4_real_time_prompt_enhancement_a_b_test import (
    PSN_Prompt_Enhancer_Interface,
    PSN_RealTime_A_B_Generator,
)


class TestPSN_Prompt_Enhancer_Interface:
    def test_returns_original_when_toggle_false(self):
        node = PSN_Prompt_Enhancer_Interface()
        active, source = node.run("original prompt", "enhanced prompt", False)
        assert active == "original prompt"
        assert source == "original"

    def test_returns_enhanced_when_toggle_true(self):
        node = PSN_Prompt_Enhancer_Interface()
        active, source = node.run("original prompt", "enhanced prompt", True)
        assert active == "enhanced prompt"
        assert source == "enhanced"

    def test_empty_prompts(self):
        node = PSN_Prompt_Enhancer_Interface()
        active, source = node.run("", "", False)
        assert active == ""
        assert source == "original"

    def test_multiline_prompts(self):
        node = PSN_Prompt_Enhancer_Interface()
        orig = "line1\nline2"
        enh = "line1\nline2\nline3"
        active, source = node.run(orig, enh, True)
        assert active == enh
        assert source == "enhanced"


class TestPSN_RealTime_A_B_Generator:
    def test_valid_payload(self):
        node = PSN_RealTime_A_B_Generator()
        payload_str, status = node.run("test prompt", "original", 42, 20, 7.0)
        assert status == "ok"
        payload = json.loads(payload_str)
        assert payload["prompt"] == "test prompt"
        assert payload["source"] == "original"
        assert payload["seed"] == 42
        assert payload["steps"] == 20
        assert payload["cfg"] == 7.0
        assert "hash" in payload

    def test_deterministic_hash(self):
        node = PSN_RealTime_A_B_Generator()
        p1, _ = node.run("test", "original", 1, 10, 5.0)
        p2, _ = node.run("test", "original", 1, 10, 5.0)
        assert p1 == p2

    def test_different_seed_different_hash(self):
        node = PSN_RealTime_A_B_Generator()
        p1, _ = node.run("test", "original", 1, 10, 5.0)
        p2, _ = node.run("test", "original", 2, 10, 5.0)
        assert json.loads(p1)["hash"] != json.loads(p2)["hash"]

    def test_invalid_prompt_source(self):
        node = PSN_RealTime_A_B_Generator()
        payload_str, status = node.run("test", "invalid_source", 1, 10, 5.0)
        assert status == "error"
        payload = json.loads(payload_str)
        assert "error" in payload

    def test_invalid_steps(self):
        node = PSN_RealTime_A_B_Generator()
        payload_str, status = node.run("test", "original", 1, 0, 5.0)
        assert status == "error"

    def test_invalid_cfg(self):
        node = PSN_RealTime_A_B_Generator()
        payload_str, status = node.run("test", "original", 1, 10, -1.0)
        assert status == "error"

    def test_invalid_seed(self):
        node = PSN_RealTime_A_B_Generator()
        payload_str, status = node.run("test", "original", -1, 10, 5.0)
        assert status == "error"
