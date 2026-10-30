"""Tests for PSN_Memory_Store node."""

import pytest

from psn_nodes.gen.psn_memory_store import (
    PSN_Memory_Store,
    _STORE,
    _make_handle,
    _validate_agent_id,
    _validate_key,
    _validate_value,
    _validate_mode,
)


@pytest.fixture(autouse=True)
def clear_store():
    """Clear the in-process store before and after each test."""
    _STORE.clear()
    yield
    _STORE.clear()


def test_set_mode_stores_value():
    node = PSN_Memory_Store()
    handle = node.run("agent1", "style", "watercolor", "SET")[0]
    assert handle == _make_handle("agent1", "style")
    assert _STORE[("agent1", "style")] == "watercolor"


def test_set_mode_overwrites_existing_value():
    node = PSN_Memory_Store()
    node.run("agent1", "style", "watercolor", "SET")
    node.run("agent1", "style", "oil_painting", "SET")
    assert _STORE[("agent1", "style")] == "oil_painting"


def test_append_mode_appends_to_existing():
    node = PSN_Memory_Store()
    node.run("agent1", "tags", "dark", "SET")
    node.run("agent1", "tags", "moody", "APPEND")
    assert _STORE[("agent1", "tags")] == "dark\nmoody"


def test_append_mode_creates_entry_if_missing():
    node = PSN_Memory_Store()
    node.run("agent1", "tags", "first", "APPEND")
    assert _STORE[("agent1", "tags")] == "first"


def test_different_agents_have_separate_stores():
    node = PSN_Memory_Store()
    node.run("agentA", "key", "valueA", "SET")
    node.run("agentB", "key", "valueB", "SET")
    assert _STORE[("agentA", "key")] == "valueA"
    assert _STORE[("agentB", "key")] == "valueB"


def test_empty_agent_id_raises():
    node = PSN_Memory_Store()
    with pytest.raises(ValueError, match="agent_id must not be empty"):
        node.run("   ", "key", "value", "SET")


def test_empty_key_raises():
    node = PSN_Memory_Store()
    with pytest.raises(ValueError, match="key must not be empty"):
        node.run("agent1", "  ", "value", "SET")


def test_invalid_mode_raises():
    node = PSN_Memory_Store()
    with pytest.raises(ValueError, match="mode must be one of"):
        node.run("agent1", "key", "value", "DELETE")


def test_non_string_agent_id_raises():
    node = PSN_Memory_Store()
    with pytest.raises(ValueError, match="agent_id must be a string"):
        node.run(123, "key", "value", "SET")


def test_non_string_value_raises():
    node = PSN_Memory_Store()
    with pytest.raises(ValueError, match="value must be a string"):
        node.run("agent1", "key", 42, "SET")


def test_handle_is_deterministic():
    h1 = _make_handle("agent1", "key1")
    h2 = _make_handle("agent1", "key1")
    assert h1 == h2
    assert h1.startswith("mem:agent1:key1:")


def test_handle_differs_for_different_keys():
    h1 = _make_handle("agent1", "key1")
    h2 = _make_handle("agent1", "key2")
    assert h1 != h2


def test_long_agent_id_raises():
    node = PSN_Memory_Store()
    long_id = "a" * 257
    with pytest.raises(ValueError, match="agent_id must be at most 256"):
        node.run(long_id, "key", "value", "SET")


def test_long_key_raises():
    node = PSN_Memory_Store()
    long_key = "k" * 513
    with pytest.raises(ValueError, match="key must be at most 512"):
        node.run("agent1", long_key, "value", "SET")


def test_long_value_raises():
    node = PSN_Memory_Store()
    long_value = "v" * 1_000_001
    with pytest.raises(ValueError, match="value must be at most 1,000,000"):
        node.run("agent1", "key", long_value, "SET")


def test_whitespace_in_agent_id_and_key_is_stripped():
    node = PSN_Memory_Store()
    node.run("  agent1  ", "  key1  ", "value", "SET")
    assert ("agent1", "key1") in _STORE
    assert _STORE[("agent1", "key1")] == "value"
