"""Tests for psn_nodes.gen.n_6_secure_api_key_management."""

import pytest

from psn_nodes.gen.n_6_secure_api_key_management import (
    PSN_Key_Store,
    PSN_Key_Retriever,
    psn_store_key,
    psn_retrieve_key,
    psn_delete_key,
    psn_clear_store,
    psn_list_keys,
    _KEY_STORE,
)


@pytest.fixture(autouse=True)
def clear_store():
    """Ensure the key store is empty before and after each test."""
    psn_clear_store()
    yield
    psn_clear_store()


def test_store_and_retrieve_basic():
    """Store a key and retrieve it; assert equality."""
    success, reason = psn_store_key("my_api_key", "secret123")
    assert success is True
    assert reason == "stored"

    value, found = psn_retrieve_key("my_api_key")
    assert found is True
    assert value == "secret123"


def test_retrieve_nonexistent_key_returns_empty():
    """Retrieving a key that was never stored returns empty string and found=False."""
    value, found = psn_retrieve_key("nonexistent_key")
    assert found is False
    assert value == ""


def test_store_rejects_empty_key_name():
    """Storing with an empty key name should fail."""
    success, reason = psn_store_key("", "some_value")
    assert success is False
    assert "empty" in reason.lower()


def test_store_rejects_invalid_characters_in_key_name():
    """Key names with spaces, slashes, or other invalid chars should be rejected."""
    for bad_name in ["has space", "has/slash", "has$special", "tab\there", "newline\nhere"]:
        success, reason = psn_store_key(bad_name, "value")
        assert success is False, "Should reject key name: %r" % bad_name


def test_store_rejects_non_string_inputs():
    """Non-string key_name or key_value should be rejected."""
    success, reason = psn_store_key(12345, "value")
    assert success is False

    success, reason = psn_store_key("valid_name", 99999)
    assert success is False


def test_delete_key():
    """Delete a stored key and verify it is gone."""
    psn_store_key("temp_key", "temp_value")
    value, found = psn_retrieve_key("temp_key")
    assert found is True

    success, reason = psn_delete_key("temp_key")
    assert success is True

    value, found = psn_retrieve_key("temp_key")
    assert found is False
    assert value == ""


def test_delete_nonexistent_key():
    """Deleting a key that does not exist should return failure."""
    success, reason = psn_delete_key("ghost_key")
    assert success is False
    assert "not found" in reason.lower()


def test_list_keys_returns_sorted_names_only():
    """psn_list_keys should return sorted key names, not values."""
    psn_store_key("zeta", "zval")
    psn_store_key("alpha", "aval")
    psn_store_key("mid", "mval")

    keys = psn_list_keys()
    assert keys == ["alpha", "mid", "zeta"]
    # Ensure values are not in the list
    for k in keys:
        assert k in ("alpha", "mid", "zeta")


def test_node_store_and_retrieve_integration():
    """Use the node classes directly to store and retrieve."""
    store_node = PSN_Key_Store()
    retriever_node = PSN_Key_Retriever()

    (status,) = store_node.run(key_name="integration_key", key_value="int_value_42")
    assert status is True

    (value,) = retriever_node.run(key_name="integration_key")
    assert value == "int_value_42"


def test_node_retrieve_missing_key_returns_empty():
    """Retriever node for a missing key should return empty string."""
    retriever_node = PSN_Key_Retriever()
    (value,) = retriever_node.run(key_name="never_stored")
    assert value == ""


def test_overwrite_existing_key():
    """Storing a key that already exists should overwrite the value."""
    psn_store_key("overwrite_key", "first_value")
    psn_store_key("overwrite_key", "second_value")

    value, found = psn_retrieve_key("overwrite_key")
    assert found is True
    assert value == "second_value"


def test_key_name_max_length_enforced():
    """Key names longer than 128 chars should be rejected."""
    long_name = "a" * 129
    success, reason = psn_store_key(long_name, "value")
    assert success is False
    assert "maximum length" in reason.lower()

    # Exactly 128 should be fine
    ok_name = "a" * 128
    success, reason = psn_store_key(ok_name, "value")
    assert success is True


def test_key_value_max_length_enforced():
    """Key values longer than 4096 chars should be rejected."""
    long_value = "x" * 4097
    success, reason = psn_store_key("val_key", long_value)
    assert success is False
    assert "maximum length" in reason.lower()

    # Exactly 4096 should be fine
    ok_value = "x" * 4096
    success, reason = psn_store_key("val_key", ok_value)
    assert success is True


def test_store_isolated_between_tests():
    """Verify the store is cleared between tests (autouse fixture)."""
    psn_store_key("isolated_key", "isolated_value")
    assert psn_retrieve_key("isolated_key")[1] is True
    # After fixture cleanup, this key should be gone (checked in next test implicitly)
