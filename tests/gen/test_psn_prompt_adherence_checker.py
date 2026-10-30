"""Tests for PSN_Prompt_Adherence_Checker."""

import pytest
from psn_nodes.gen.psn_prompt_adherence_checker import (
    PSN_Prompt_Adherence_Checker,
    _psn_validate_constraints,
    _psn_check_adherence,
)


def test_psn_compliant_prompt_passes():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "A cyberpunk city at night"
    constraints = '{"must_include": ["cyberpunk"], "must_exclude": ["blood"]}'
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is True
    assert "No violations" in report


def test_psn_missing_required_term_fails():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "A medieval castle"
    constraints = '{"must_include": ["cyberpunk"]}'
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is False
    assert "cyberpunk" in report


def test_psn_forbidden_term_fails():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "A scene with blood and gore"
    constraints = '{"must_exclude": ["blood"]}'
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is False
    assert "blood" in report


def test_psn_min_length_violation():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "short"
    constraints = '{"min_length": 10}'
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is False
    assert "minimum" in report


def test_psn_max_length_violation():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "x" * 100
    constraints = '{"max_length": 50}'
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is False
    assert "maximum" in report


def test_psn_invalid_json_raises():
    node = PSN_Prompt_Adherence_Checker()
    with pytest.raises(ValueError, match="Invalid JSON"):
        node.run("test prompt", "not valid json")


def test_psn_disallowed_key_raises():
    node = PSN_Prompt_Adherence_Checker()
    with pytest.raises(ValueError, match="Disallowed constraint key"):
        node.run("test prompt", '{"unknown_key": "value"}')


def test_psn_wrong_type_raises():
    node = PSN_Prompt_Adherence_Checker()
    with pytest.raises(ValueError, match="must be of type"):
        node.run("test prompt", '{"must_include": "cyberpunk"}')


def test_psn_empty_constraints_passes():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "Any prompt here"
    constraints = "{}"
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is True
    assert "No violations" in report


def test_psn_case_insensitive_matching():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "A CYBERPUNK city"
    constraints = '{"must_include": ["cyberpunk"]}'
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is True


def test_psn_multiple_violations_reported():
    node = PSN_Prompt_Adherence_Checker()
    prompt = "short"
    constraints = '{"must_include": ["cyberpunk"], "must_exclude": ["blood"], "min_length": 10}'
    is_compliant, report = node.run(prompt, constraints)
    assert is_compliant is False
    assert "cyberpunk" in report
    assert "minimum" in report
