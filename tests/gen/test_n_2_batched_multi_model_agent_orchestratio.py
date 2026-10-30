"""
Tests for Batched Multi-Model Agent Orchestration nodes.
"""

import pytest
from psn_nodes.gen.n_2_batched_multi_model_agent_orchestratio import (
    PSN_Agent_Loop_Init,
    PSN_Agent_Executor,
    PSN_Agent_Aggregator,
    _validate_agent_config,
    _execute_agent,
)


class TestPSN_Agent_Loop_Init:
    def test_valid_init(self):
        node = PSN_Agent_Loop_Init()
        model_ids = "model_a\nmodel_b"
        agent_config = '{"agents": {"model_a": "identity", "model_b": "uppercase"}}'
        loop_state, current_index = node.run(model_ids, agent_config)
        assert current_index == 0
        assert loop_state["model_ids"] == ["model_a", "model_b"]
        assert loop_state["agents"] == {"model_a": "identity", "model_b": "uppercase"}
        assert loop_state["results"] == []

    def test_empty_model_ids(self):
        node = PSN_Agent_Loop_Init()
        with pytest.raises(ValueError, match="at least one model ID"):
            node.run("", '{"agents": {}}')

    def test_missing_agent_config(self):
        node = PSN_Agent_Loop_Init()
        model_ids = "model_a"
        agent_config = '{"agents": {}}'
        with pytest.raises(ValueError, match="Missing agent configuration"):
            node.run(model_ids, agent_config)

    def test_invalid_json(self):
        node = PSN_Agent_Loop_Init()
        with pytest.raises(ValueError, match="Invalid JSON"):
            node.run("model_a", "not valid json")

    def test_unknown_agent_type(self):
        node = PSN_Agent_Loop_Init()
        model_ids = "model_a"
        agent_config = '{"agents": {"model_a": "unknown_type"}}'
        with pytest.raises(ValueError, match="Unknown agent type"):
            node.run(model_ids, agent_config)


class TestPSN_Agent_Executor:
    def test_single_iteration(self):
        init_node = PSN_Agent_Loop_Init()
        exec_node = PSN_Agent_Executor()
        model_ids = "model_a"
        agent_config = '{"agents": {"model_a": "uppercase"}}'
        loop_state, idx = init_node.run(model_ids, agent_config)
        result, next_idx, done = exec_node.run(loop_state, idx, "model_a")
        assert result == "INPUT_FOR_MODEL_A"
        assert next_idx == 1
        assert done is True

    def test_two_iterations(self):
        init_node = PSN_Agent_Loop_Init()
        exec_node = PSN_Agent_Executor()
        model_ids = "model_a\nmodel_b"
        agent_config = '{"agents": {"model_a": "identity", "model_b": "reverse"}}'
        loop_state, idx = init_node.run(model_ids, agent_config)

        result1, next_idx1, done1 = exec_node.run(loop_state, idx, "model_a")
        assert result1 == "input_for_model_a"
        assert next_idx1 == 1
        assert done1 is False

        result2, next_idx2, done2 = exec_node.run(loop_state, next_idx1, "model_b")
        # input_for_model_b reversed is b_ledom_rof_tupni
        assert result2 == "b_ledom_rof_tupni"
        assert next_idx2 == 2
        assert done2 is True

        assert loop_state["results"] == ["input_for_model_a", "b_ledom_rof_tupni"]

    def test_index_out_of_range(self):
        init_node = PSN_Agent_Loop_Init()
        exec_node = PSN_Agent_Executor()
        model_ids = "model_a"
        agent_config = '{"agents": {"model_a": "identity"}}'
        loop_state, idx = init_node.run(model_ids, agent_config)
        result, next_idx, done = exec_node.run(loop_state, 5, "model_a")
        assert result is None
        assert next_idx == 5
        assert done is True

    def test_model_id_mismatch(self):
        init_node = PSN_Agent_Loop_Init()
        exec_node = PSN_Agent_Executor()
        model_ids = "model_a"
        agent_config = '{"agents": {"model_a": "identity"}}'
        loop_state, idx = init_node.run(model_ids, agent_config)
        with pytest.raises(ValueError, match="model_id mismatch"):
            exec_node.run(loop_state, idx, "model_b")

    def test_negative_index(self):
        init_node = PSN_Agent_Loop_Init()
        exec_node = PSN_Agent_Executor()
        model_ids = "model_a"
        agent_config = '{"agents": {"model_a": "identity"}}'
        loop_state, idx = init_node.run(model_ids, agent_config)
        with pytest.raises(ValueError, match="non-negative"):
            exec_node.run(loop_state, -1, "model_a")


class TestPSN_Agent_Aggregator:
    def test_aggregate_results(self):
        node = PSN_Agent_Aggregator()
        results = ["result_a", "result_b", "result_c"]
        final_output = node.run(results)[0]
        assert final_output["count"] == 3
        assert final_output["results"] == ["result_a", "result_b", "result_c"]

    def test_empty_results(self):
        node = PSN_Agent_Aggregator()
        final_output = node.run([])[0]
        assert final_output["count"] == 0
        assert final_output["results"] == []

    def test_non_list_input(self):
        node = PSN_Agent_Aggregator()
        with pytest.raises(ValueError, match="must be a list"):
            node.run("not a list")


class TestHelperFunctions:
    def test_validate_agent_config_valid(self):
        config = _validate_agent_config('{"agents": {"m1": "identity"}}')
        assert config["agents"] == {"m1": "identity"}

    def test_validate_agent_config_non_dict(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            _validate_agent_config('[1, 2, 3]')

    def test_execute_agent_identity(self):
        assert _execute_agent("m1", "identity", "hello") == "hello"

    def test_execute_agent_uppercase(self):
        assert _execute_agent("m1", "uppercase", "hello") == "HELLO"

    def test_execute_agent_reverse(self):
        assert _execute_agent("m1", "reverse", "hello") == "olleh"

    def test_execute_agent_unknown(self):
        with pytest.raises(ValueError, match="Unknown agent type"):
            _execute_agent("m1", "unknown", "hello")
