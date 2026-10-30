"""
Tests for psn_nodes.gen.psn_param_hub
"""

import pytest
from psn_nodes.gen.psn_param_hub import (
    PSN_ParamHub,
    PSN_ParamHubRead,
    set_param,
    get_param,
    list_params,
    clear_params,
)


@pytest.fixture(autouse=True)
def clean_store():
    """Clear the parameter store before and after each test."""
    clear_params()
    yield
    clear_params()


class TestSetAndGetParam:
    def test_set_and_read_float(self):
        success, msg = set_param("cfg_scale", 7.5, "GLOBAL")
        assert success is True
        found, val, msg2 = get_param("cfg_scale", "GLOBAL")
        assert found is True
        assert val == 7.5

    def test_set_and_read_int(self):
        success, msg = set_param("steps", 50, "GLOBAL")
        assert success is True
        found, val, msg2 = get_param("steps", "GLOBAL")
        assert found is True
        assert val == 50

    def test_set_and_read_string(self):
        success, msg = set_param("model_name", "sd_xl_base", "GLOBAL")
        assert success is True
        found, val, msg2 = get_param("model_name", "GLOBAL")
        assert found is True
        assert val == "sd_xl_base"

    def test_local_scope_isolation(self):
        set_param("param", "global_val", "GLOBAL")
        set_param("param", "local_val", "LOCAL")
        found_g, val_g, _ = get_param("param", "GLOBAL")
        found_l, val_l, _ = get_param("param", "LOCAL")
        assert found_g is True
        assert val_g == "global_val"
        assert found_l is True
        assert val_l == "local_val"

    def test_read_nonexistent_param(self):
        found, val, msg = get_param("nonexistent", "GLOBAL")
        assert found is False
        assert val is None
        assert "not found" in msg


class TestValidation:
    def test_invalid_param_name_empty(self):
        success, msg = set_param("", 1.0, "GLOBAL")
        assert success is False
        assert "empty" in msg

    def test_invalid_param_name_non_string(self):
        success, msg = set_param(123, 1.0, "GLOBAL")
        assert success is False
        assert "string" in msg

    def test_invalid_param_name_bad_chars(self):
        success, msg = set_param("bad/name", 1.0, "GLOBAL")
        assert success is False
        assert "invalid character" in msg

    def test_invalid_scope(self):
        success, msg = set_param("param", 1.0, "INVALID")
        assert success is False
        assert "scope" in msg

    def test_invalid_value_type(self):
        success, msg = set_param("param", [1, 2, 3], "GLOBAL")
        assert success is False
        assert "FLOAT, INT, or STRING" in msg


class TestNodeClasses:
    def test_psn_param_hub_run(self):
        node = PSN_ParamHub()
        hub_handle, success, message = node.run(
            param_name="test_param",
            value=42.0,
            scope="GLOBAL",
        )
        assert success is True
        assert "Set" in message
        found, val, _ = get_param("test_param", "GLOBAL")
        assert found is True
        assert val == 42.0

    def test_psn_param_hub_run_with_string_value(self):
        node = PSN_ParamHub()
        hub_handle, success, message = node.run(
            param_name="test_str",
            value=0.0,
            scope="GLOBAL",
            value_str="hello",
        )
        assert success is True
        found, val, _ = get_param("test_str", "GLOBAL")
        assert found is True
        assert val == "hello"

    def test_psn_param_hub_read(self):
        set_param("read_test", 99.9, "GLOBAL")
        node = PSN_ParamHubRead()
        value, found, message = node.run(
            param_name="read_test",
            scope="GLOBAL",
        )
        assert found is True
        assert value == 99.9

    def test_psn_param_hub_read_default(self):
        node = PSN_ParamHubRead()
        value, found, message = node.run(
            param_name="missing_param",
            scope="GLOBAL",
            default_value=123.456,
        )
        assert found is False
        assert value == 123.456

    def test_psn_param_hub_read_string_value_returns_default(self):
        set_param("str_param", "not_a_number", "GLOBAL")
        node = PSN_ParamHubRead()
        value, found, message = node.run(
            param_name="str_param",
            scope="GLOBAL",
            default_value=0.0,
        )
        assert found is True
        assert value == 0.0  # Falls back to default since string can't be float


class TestListAndClear:
    def test_list_params_all(self):
        set_param("a", 1, "GLOBAL")
        set_param("b", 2, "LOCAL")
        params = list_params()
        assert "GLOBAL:a" in params
        assert "LOCAL:b" in params
        assert len(params) == 2

    def test_list_params_by_scope(self):
        set_param("a", 1, "GLOBAL")
        set_param("b", 2, "LOCAL")
        global_params = list_params("GLOBAL")
        assert "GLOBAL:a" in global_params
        assert "LOCAL:b" not in global_params

    def test_clear_all(self):
        set_param("a", 1, "GLOBAL")
        set_param("b", 2, "LOCAL")
        count = clear_params()
        assert count == 2
        assert len(list_params()) == 0

    def test_clear_by_scope(self):
        set_param("a", 1, "GLOBAL")
        set_param("b", 2, "LOCAL")
        count = clear_params("GLOBAL")
        assert count == 1
        params = list_params()
        assert "LOCAL:b" in params
        assert "GLOBAL:a" not in params
