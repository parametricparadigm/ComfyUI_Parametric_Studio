"""Tests for psn_nodes.gen.n_7_stateful_live_workflow_transformation."""

import pytest
from psn_nodes.gen.n_7_stateful_live_workflow_transformation import (
    PSN_Live_State_Init,
    PSN_Live_State_Update,
    PSN_Live_State_Loop,
    _make_initial_state,
    _apply_update,
    _loop_decision,
    _MAX_HISTORY,
)


class TestPSN_Live_State_Init:
    def test_init_with_none(self):
        node = PSN_Live_State_Init()
        (state,) = node.run(None)
        assert isinstance(state, dict)
        assert state["value"] is None
        assert state["history"] == []
        assert state["step"] == 0
        assert state["last_input"] is None

    def test_init_with_number(self):
        node = PSN_Live_State_Init()
        (state,) = node.run(42)
        assert state["value"] == 42
        assert state["step"] == 0

    def test_init_with_string(self):
        node = PSN_Live_State_Init()
        (state,) = node.run("hello")
        assert state["value"] == "hello"

    def test_init_with_dict_preserves_keys(self):
        node = PSN_Live_State_Init()
        (state,) = node.run({"custom_key": "custom_value"})
        assert state["custom_key"] == "custom_value"
        assert state["step"] == 0
        assert state["history"] == []

    def test_init_with_dict_sets_value_to_none(self):
        node = PSN_Live_State_Init()
        (state,) = node.run({"a": 1})
        # When initial_state is a dict, value is set to None
        assert state["value"] is None


class TestPSN_Live_State_Update:
    def test_update_numeric_accumulation(self):
        node = PSN_Live_State_Update()
        state = _make_initial_state(10)
        updated_state, output = node.run(state, 5)
        assert output == 15
        assert updated_state["value"] == 15
        assert updated_state["step"] == 1
        assert updated_state["last_input"] == 5
        assert len(updated_state["history"]) == 1

    def test_update_string_concatenation(self):
        node = PSN_Live_State_Update()
        state = _make_initial_state("hello ")
        updated_state, output = node.run(state, "world")
        assert output == "hello world"
        assert updated_state["value"] == "hello world"

    def test_update_mixed_types_last_write_wins(self):
        node = PSN_Live_State_Update()
        state = _make_initial_state(42)
        updated_state, output = node.run(state, "text")
        assert output == "text"
        assert updated_state["value"] == "text"

    def test_update_multiple_steps(self):
        node = PSN_Live_State_Update()
        state = _make_initial_state(0)
        for i in range(1, 6):
            state, _ = node.run(state, i)
        assert state["value"] == 15  # 1+2+3+4+5
        assert state["step"] == 5
        assert len(state["history"]) == 5

    def test_update_history_bounded(self):
        node = PSN_Live_State_Update()
        state = _make_initial_state(0)
        # Run more updates than the max history size
        total_updates = _MAX_HISTORY + 10
        for i in range(total_updates):
            state, _ = node.run(state, i)
        
        assert len(state["history"]) == _MAX_HISTORY
        # The history should contain the last _MAX_HISTORY entries.
        # The inputs were 0, 1, ..., total_updates - 1.
        # The last entry is total_updates - 1.
        # The first entry in the bounded history should be total_updates - _MAX_HISTORY.
        expected_first_input = total_updates - _MAX_HISTORY
        assert state["history"][0]["input"] == expected_first_input
        assert state["history"][-1]["input"] == total_updates - 1

    def test_update_with_invalid_state(self):
        node = PSN_Live_State_Update()
        # Passing a non-dict state should still work
        updated_state, output = node.run("not_a_dict", 5)
        assert isinstance(updated_state, dict)
        assert updated_state["step"] == 1


class TestPSN_Live_State_Loop:
    def test_loop_immediate_poll(self):
        node = PSN_Live_State_Loop()
        state = _make_initial_state(None)
        state, continue_flag, reason = node.run(state, 0)
        assert continue_flag is True
        assert reason == "immediate_poll"

    def test_loop_with_processed_input(self):
        node = PSN_Live_State_Loop()
        state = _make_initial_state(0)
        state["step"] = 1
        state, continue_flag, reason = node.run(state, 100)
        assert continue_flag is True
        assert reason == "has_processed_input"

    def test_loop_timeout_no_input(self):
        node = PSN_Live_State_Loop()
        state = _make_initial_state(None)
        state["step"] = 0
        state, continue_flag, reason = node.run(state, 100)
        assert continue_flag is False
        assert reason == "timeout_no_input"

    def test_loop_with_invalid_state(self):
        node = PSN_Live_State_Loop()
        state, continue_flag, reason = node.run("bad_state", 0)
        assert isinstance(state, dict)
        assert continue_flag is True  # wait_ms=0 means immediate poll


class TestEdgeCases:
    def test_full_workflow_cycle(self):
        """Simulate a complete init -> update -> loop cycle."""
        init_node = PSN_Live_State_Init()
        update_node = PSN_Live_State_Update()
        loop_node = PSN_Live_State_Loop()

        # Init
        (state,) = init_node.run(0)
        assert state["step"] == 0

        # Update
        state, output = update_node.run(state, 10)
        assert output == 10
        assert state["step"] == 1

        # Loop
        state, continue_flag, reason = loop_node.run(state, 100)
        assert continue_flag is True
        assert reason == "has_processed_input"

        # Second update
        state, output = update_node.run(state, 20)
        assert output == 30
        assert state["step"] == 2

    def test_large_numeric_values(self):
        node = PSN_Live_State_Update()
        state = _make_initial_state(1e15)
        updated_state, output = node.run(state, 1e15)
        assert output == 2e15

    def test_empty_string_update(self):
        node = PSN_Live_State_Update()
        state = _make_initial_state("hello")
        updated_state, output = node.run(state, "")
        assert output == "hello"

    def test_zero_wait_ms_always_continues(self):
        node = PSN_Live_State_Loop()
        state = _make_initial_state(None)
        state["step"] = 0
        _, continue_flag, _ = node.run(state, 0)
        assert continue_flag is True

    def test_negative_wait_ms_treated_as_immediate(self):
        node = PSN_Live_State_Loop()
        state = _make_initial_state(None)
        state["step"] = 0
        _, continue_flag, reason = node.run(state, -1)
        assert continue_flag is True
        assert reason == "immediate_poll"

    def test_state_dict_not_mutated_in_place(self):
        """Ensure that update creates a new dict, not mutating the original."""
        node = PSN_Live_State_Update()
        original_state = _make_initial_state(10)
        original_copy = dict(original_state)
        original_copy["history"] = list(original_state["history"])

        updated_state, _ = node.run(original_state, 5)
        # Original should be unchanged
        assert original_state["value"] == 10
        assert original_state["step"] == 0
        assert original_state["history"] == original_copy["history"]
        # Updated should be different
        assert updated_state["value"] == 15
        assert updated_state["step"] == 1
