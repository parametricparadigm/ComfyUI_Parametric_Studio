"""Tests for PSN_Memory_Recall node."""

import json

from psn_nodes.gen.psn_memory_recall import PSN_Memory_Recall, _parse_store, _filter_entries, _format_output


def _make_store(entries):
    """Helper to create a store_handle JSON string from a list of dicts."""
    return json.dumps(entries)


def test_recall_substring_match():
    """Store 'cyberpunk' and recall with 'cyber' should match."""
    node = PSN_Memory_Recall()
    store = _make_store([{"text": "cyberpunk city", "id": 1}, {"text": "medieval castle", "id": 2}])
    result = node.run(store, "cyber")
    memories = json.loads(result[0])
    assert len(memories) == 1
    assert memories[0]["text"] == "cyberpunk city"


def test_recall_empty_query_returns_all():
    """Empty query should return all entries."""
    node = PSN_Memory_Recall()
    store = _make_store([{"text": "alpha", "id": 1}, {"text": "beta", "id": 2}, {"text": "gamma", "id": 3}])
    result = node.run(store, "")
    memories = json.loads(result[0])
    assert len(memories) == 3


def test_recall_no_match_returns_empty_list():
    """Query with no matches should return an empty list."""
    node = PSN_Memory_Recall()
    store = _make_store([{"text": "hello", "id": 1}])
    result = node.run(store, "nonexistent")
    memories = json.loads(result[0])
    assert memories == []


def test_recall_case_insensitive():
    """Substring match should be case-insensitive."""
    node = PSN_Memory_Recall()
    store = _make_store([{"text": "CyberPunk", "id": 1}])
    result = node.run(store, "cyber")
    memories = json.loads(result[0])
    assert len(memories) == 1


def test_recall_invalid_json_store():
    """Invalid JSON in store_handle should return an error object."""
    node = PSN_Memory_Recall()
    result = node.run("not valid json", "test")
    data = json.loads(result[0])
    assert "error" in data


def test_recall_store_not_a_list():
    """store_handle JSON that is not a list should return an error."""
    node = PSN_Memory_Recall()
    store = json.dumps({"key": "value"})
    result = node.run(store, "test")
    data = json.loads(result[0])
    assert "error" in data


def test_recall_entry_missing_text_key():
    """Entry without a 'text' key should return an error."""
    node = PSN_Memory_Recall()
    store = json.dumps([{"id": 1}])
    result = node.run(store, "test")
    data = json.loads(result[0])
    assert "error" in data


def test_recall_non_string_store_handle():
    """Non-string store_handle should return an error."""
    node = PSN_Memory_Recall()
    result = node.run(12345, "test")
    data = json.loads(result[0])
    assert "error" in data


def test_parse_store_valid():
    """_parse_store should return entries and None error for valid input."""
    entries, err = _parse_store(json.dumps([{"text": "a"}, {"text": "b"}]))
    assert err is None
    assert len(entries) == 2


def test_filter_entries_empty_query():
    """_filter_entries with empty query returns all entries."""
    entries = [{"text": "x"}, {"text": "y"}]
    result = _filter_entries(entries, "")
    assert result == entries


def test_format_output_roundtrip():
    """_format_output should produce valid JSON that round-trips."""
    entries = [{"text": "hello", "id": 1}]
    formatted = _format_output(entries)
    parsed = json.loads(formatted)
    assert parsed == entries
