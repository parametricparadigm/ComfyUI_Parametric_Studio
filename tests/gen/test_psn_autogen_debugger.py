"""Tests for psn_nodes.gen.psn_autogen_debugger."""

import json
import pytest

from psn_nodes.gen.psn_autogen_debugger import (
    PSN_AutoGen_Debugger,
    _sanitize_agents,
    _extract_consensus,
    _run_debate,
    _default_llm,
    _CONSENSUS_MARKER,
)


def test_sanitize_agents_valid():
    cleaned, err = _sanitize_agents(["Engineer", "Artist", "Manager"])
    assert err is None
    assert cleaned == ["Engineer", "Artist", "Manager"]


def test_sanitize_agents_duplicate():
    cleaned, err = _sanitize_agents(["Engineer", "Engineer"])
    assert err is not None
    assert "duplicate" in err


def test_sanitize_agents_empty_list():
    cleaned, err = _sanitize_agents([])
    assert err is not None
    assert "at least one" in err


def test_sanitize_agents_non_string():
    cleaned, err = _sanitize_agents(["Engineer", 42])
    assert err is not None
    assert "not a string" in err


def test_extract_consensus_present():
    response = "After discussion, CONSENSUS: increase the learning rate to 0.01"
    result = _extract_consensus(response)
    assert result == "increase the learning rate to 0.01"


def test_extract_consensus_absent():
    response = "I think we should try a different approach."
    result = _extract_consensus(response)
    assert result is None


def test_extract_consensus_empty_resolution():
    response = "CONSENSUS:"
    result = _extract_consensus(response)
    assert result is None


def test_run_debate_consensus_on_first_turn():
    agents = ["Engineer", "Artist"]
    def mock_llm(prompt):
        return "CONSENSUS: fix the parameter"
    resolution, chat_log, reason = _run_debate("some error", agents, mock_llm, 6)
    assert resolution == "fix the parameter"
    assert reason == "consensus_reached"
    assert "Engineer" in chat_log


def test_run_debate_max_turns_no_consensus():
    agents = ["Engineer", "Artist"]
    def mock_llm(prompt):
        return "No consensus yet."
    resolution, chat_log, reason = _run_debate("some error", agents, mock_llm, 4)
    assert resolution is None
    assert reason == "max_turns_reached"
    # 4 turns, 2 agents -> 4 entries
    entries = chat_log.strip().split("\n")
    assert len(entries) == 4


def test_node_run_with_json_mock_llm():
    node = PSN_AutoGen_Debugger()
    responses = [
        "I propose adjusting the threshold.",
        "CONSENSUS: set threshold to 0.5",
    ]
    mock_json = json.dumps({"responses": responses})
    resolution, chat_log, reason = node.run(
        error_log="threshold conflict",
        agents="Engineer,Artist",
        max_turns=6,
        mock_llm=mock_json,
    )
    assert resolution == "set threshold to 0.5"
    assert reason == "consensus_reached"
    assert "Engineer" in chat_log
    assert "Artist" in chat_log


def test_node_run_invalid_agents():
    node = PSN_AutoGen_Debugger()
    resolution, chat_log, reason = node.run(
        error_log="some error",
        agents="",
        max_turns=6,
    )
    assert reason == "invalid_agents"
    assert resolution.startswith("ERROR:")


def test_node_run_default_llm_no_consensus():
    node = PSN_AutoGen_Debugger()
    resolution, chat_log, reason = node.run(
        error_log="some error",
        agents="Engineer,Artist",
        max_turns=3,
    )
    assert resolution is None
    assert reason == "max_turns_reached"
    # 3 turns
    entries = chat_log.strip().split("\n")
    assert len(entries) == 3


def test_node_run_single_agent():
    node = PSN_AutoGen_Debugger()
    def mock_llm(prompt):
        return "CONSENSUS: single agent fix"
    resolution, chat_log, reason = node.run(
        error_log="error",
        agents="Solo",
        max_turns=5,
        mock_llm=mock_llm,
    )
    assert resolution == "single agent fix"
    assert reason == "consensus_reached"
    assert "Solo" in chat_log


def test_node_run_llm_exception_handled():
    node = PSN_AutoGen_Debugger()
    def bad_llm(prompt):
        raise RuntimeError("LLM down")
    resolution, chat_log, reason = node.run(
        error_log="error",
        agents="Engineer",
        max_turns=2,
        mock_llm=bad_llm,
    )
    assert resolution is None
    assert reason == "max_turns_reached"
    assert "Error: LLM call failed." in chat_log
