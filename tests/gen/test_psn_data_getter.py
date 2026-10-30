"""Tests for PSN_Data_Getter node."""

import pytest
from psn_nodes.gen.psn_data_getter import (
    PSN_Data_Getter,
    psn_set_global_data,
    psn_clear_global_data,
    _PSN_GLOBAL_DATA,
)


@pytest.fixture(autouse=True)
def clean_global_data():
    """Ensure global data is cleared before and after each test."""
    psn_clear_global_data()
    yield
    psn_clear_global_data()


def test_get_set_value_returns_stored_data():
    """Test that retrieving a set value returns the stored data."""
    psn_set_global_data("test_key", 42)
    node = PSN_Data_Getter()
    result = node.run(name="test_key", default=None)
    assert result == (42,)


def test_get_unset_value_returns_default():
    """Test that retrieving an unset value returns the default."""
    node = PSN_Data_Getter()
    result = node.run(name="nonexistent_key", default="fallback_value")
    assert result == ("fallback_value",)


def test_get_unset_value_with_none_default():
    """Test that retrieving an unset value with None default returns None."""
    node = PSN_Data_Getter()
    result = node.run(name="nonexistent_key", default=None)
    assert result == (None,)


def test_get_string_value():
    """Test retrieving a string value."""
    psn_set_global_data("string_key", "hello world")
    node = PSN_Data_Getter()
    result = node.run(name="string_key", default="default_str")
    assert result == ("hello world",)


def test_get_list_value():
    """Test retrieving a list value."""
    test_list = [1, 2, 3, 4, 5]
    psn_set_global_data("list_key", test_list)
    node = PSN_Data_Getter()
    result = node.run(name="list_key", default=[])
    assert result == (test_list,)


def test_get_dict_value():
    """Test retrieving a dictionary value."""
    test_dict = {"a": 1, "b": 2, "c": 3}
    psn_set_global_data("dict_key", test_dict)
    node = PSN_Data_Getter()
    result = node.run(name="dict_key", default={})
    assert result == (test_dict,)


def test_get_empty_string_name():
    """Test retrieving with an empty string name."""
    psn_set_global_data("", "empty_name_value")
    node = PSN_Data_Getter()
    result = node.run(name="", default="default")
    assert result == ("empty_name_value",)


def test_get_empty_string_name_not_set():
    """Test retrieving with an empty string name that is not set."""
    node = PSN_Data_Getter()
    result = node.run(name="", default="default")
    assert result == ("default",)


def test_overwrite_existing_value():
    """Test that setting a value twice overwrites the previous value."""
    psn_set_global_data("key", "first_value")
    psn_set_global_data("key", "second_value")
    node = PSN_Data_Getter()
    result = node.run(name="key", default="default")
    assert result == ("second_value",)


def test_multiple_keys_independent():
    """Test that multiple keys are stored and retrieved independently."""
    psn_set_global_data("key1", "value1")
    psn_set_global_data("key2", "value2")
    psn_set_global_data("key3", "value3")
    node = PSN_Data_Getter()
    assert node.run(name="key1", default=None) == ("value1",)
    assert node.run(name="key2", default=None) == ("value2",)
    assert node.run(name="key3", default=None) == ("value3",)


def test_get_boolean_value():
    """Test retrieving a boolean value."""
    psn_set_global_data("bool_key", True)
    node = PSN_Data_Getter()
    result = node.run(name="bool_key", default=False)
    assert result == (True,)


def test_get_float_value():
    """Test retrieving a float value."""
    psn_set_global_data("float_key", 3.14159)
    node = PSN_Data_Getter()
    result = node.run(name="float_key", default=0.0)
    assert result == (3.14159,)


def test_get_none_value_stored():
    """Test retrieving a stored None value (distinct from not found)."""
    psn_set_global_data("none_key", None)
    node = PSN_Data_Getter()
    result = node.run(name="none_key", default="default")
    # The key exists with value None, so it should return None, not the default
    assert result == (None,)


def test_bad_input_non_string_name():
    """Test that a non-string name does not crash (returns default)."""
    node = PSN_Data_Getter()
    # Passing a non-string should not raise, just return default
    result = node.run(name=12345, default="fallback")
    assert result == ("fallback",)


def test_bad_input_none_name():
    """Test that a None name does not crash (returns default)."""
    node = PSN_Data_Getter()
    result = node.run(name=None, default="fallback")
    assert result == ("fallback",)


def test_global_data_cleared():
    """Test that clearing global data removes all entries."""
    psn_set_global_data("key1", "value1")
    psn_set_global_data("key2", "value2")
    psn_clear_global_data()
    node = PSN_Data_Getter()
    assert node.run(name="key1", default="default") == ("default",)
    assert node.run(name="key2", default="default") == ("default",)
