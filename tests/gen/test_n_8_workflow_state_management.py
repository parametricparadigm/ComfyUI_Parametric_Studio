"""
Pytest suite for psn_nodes.gen.n_8_workflow_state_management.

Tests cover:
- PSN_State_Container storing values and returning updated state.
- PSN_State_Retriever retrieving values and falling back to default.
- PSN_Iteration_Toggle alternating correctly and reporting last iteration.
- Edge cases: empty key, missing key, boundary iterations, bad types.
"""

import pytest

from psn_nodes.gen.n_8_workflow_state_management import (
    PSN_State_Container,
    PSN_State_Retriever,
    PSN_Iteration_Toggle,
    _psn_state_store,
    _psn_state_clear,
)


@pytest.fixture(autouse=True)
def _clear_state():
    """Ensure each test starts with a clean state store."""
    _psn_state_clear()
    yield
    _psn_state_clear()


class TestPSNStateContainer:
    def test_store_and_return_state(self):
        node = PSN_State_Container()
        (state,) = node.run("iter_count", 42)
        assert state == {"iter_count": 42}
        assert _psn_state_store() == {"iter_count": 42}

    def test_store_multiple_keys(self):
        node = PSN_State_Container()
        node.run("a", 1)
        (state,) = node.run("b", "hello")
        assert state == {"a": 1, "b": "hello"}

    def test_overwrite_existing_key(self):
        node = PSN_State_Container()
        node.run("k", "first")
        (state,) = node.run("k", "second")
        assert state["k"] == "second"

    def test_empty_key_raises(self):
        node = PSN_State_Container()
        with pytest.raises(ValueError, match="non-empty"):
            node.run("", "value")

    def test_non_string_key_raises(self):
        node = PSN_State_Container()
        with pytest.raises(TypeError, match="string"):
            node.run(123, "value")


class TestPSNStateRetriever:
    def test_retrieve_existing_key(self):
        node = PSN_State_Retriever()
        (value,) = node.run({"foo": "bar"}, "foo", "default")
        assert value == "bar"

    def test_retrieve_missing_key_returns_default(self):
        node = PSN_State_Retriever()
        (value,) = node.run({"foo": "bar"}, "missing", "fallback")
        assert value == "fallback"

    def test_retrieve_empty_dict_returns_default(self):
        node = PSN_State_Retriever()
        (value,) = node.run({}, "any", 99)
        assert value == 99

    def test_non_dict_state_raises(self):
        node = PSN_State_Retriever()
        with pytest.raises(TypeError, match="dict"):
            node.run("not_a_dict", "key", "default")

    def test_non_string_key_raises(self):
        node = PSN_State_Retriever()
        with pytest.raises(TypeError, match="string"):
            node.run({"a": 1}, 42, "default")


class TestPSNIterationToggle:
    def test_even_iteration_selects_mode_a(self):
        node = PSN_Iteration_Toggle()
        (selected, is_last) = node.run(0, 4, "A", "B")
        assert selected == "A"
        assert is_last is False

    def test_odd_iteration_selects_mode_b(self):
        node = PSN_Iteration_Toggle()
        (selected, is_last) = node.run(1, 4, "A", "B")
        assert selected == "B"
        assert is_last is False

    def test_last_iteration_even(self):
        node = PSN_Iteration_Toggle()
        (selected, is_last) = node.run(4, 4, "A", "B")
        assert selected == "A"
        assert is_last is True

    def test_last_iteration_odd(self):
        node = PSN_Iteration_Toggle()
        (selected, is_last) = node.run(3, 3, "A", "B")
        assert selected == "B"
        assert is_last is True

    def test_single_iteration(self):
        node = PSN_Iteration_Toggle()
        (selected, is_last) = node.run(1, 1, "A", "B")
        assert selected == "B"
        assert is_last is True

    def test_negative_current_iteration_raises(self):
        node = PSN_Iteration_Toggle()
        with pytest.raises(ValueError, match=">= 0"):
            node.run(-1, 4, "A", "B")

    def test_zero_total_iterations_raises(self):
        node = PSN_Iteration_Toggle()
        with pytest.raises(ValueError, match=">= 1"):
            node.run(0, 0, "A", "B")

    def test_non_int_current_iteration_raises(self):
        node = PSN_Iteration_Toggle()
        with pytest.raises(TypeError, match="integer"):
            node.run(1.5, 4, "A", "B")

    def test_bool_current_iteration_raises(self):
        node = PSN_Iteration_Toggle()
        with pytest.raises(TypeError, match="integer"):
            node.run(True, 4, "A", "B")

    def test_non_int_total_iterations_raises(self):
        node = PSN_Iteration_Toggle()
        with pytest.raises(TypeError, match="integer"):
            node.run(0, "four", "A", "B")
