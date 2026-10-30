"""
Batched Multi-Model Agent Orchestration (Pure Logic)

This module implements the pure-logic, secure-by-design portion of a batched
multi-model agent orchestration system. It does NOT perform dynamic module
loading, GPU execution, or any I/O. Instead, it provides:

1. PSN_Agent_Loop_Init: Initializes loop state from a list of model IDs and
   a JSON agent configuration.
2. PSN_Agent_Executor: Simulates executing an agent for a given model ID using
   a deterministic, safe transformation (no dynamic code execution). It
   advances the index and reports loop completion.
3. PSN_Agent_Aggregator: Combines a list of results into a single structured
   output.

All functions accept plain values (strings, numbers, lists, dicts) and return
plain values. No network, file, subprocess, or dynamic import is used.
"""

import json
from typing import Any, List, Dict, Tuple

# Module-level constants
CAT = "ParametricStudio/AgentOrchestration"

# Allowed agent "types" for safe, deterministic execution
_ALLOWED_AGENT_TYPES = ("identity", "prefix", "suffix", "uppercase", "lowercase", "reverse")


def _validate_agent_config(config_json: str) -> Dict[str, Any]:
    """
    Validate and parse the agent configuration JSON string.
    Returns a dict with 'agents' mapping model_id -> agent_type.
    Raises ValueError if invalid.
    """
    if not isinstance(config_json, str):
        raise ValueError("agent_config must be a JSON string")
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in agent_config: {e}")

    if not isinstance(config, dict):
        raise ValueError("agent_config must be a JSON object")

    agents = config.get("agents", {})
    if not isinstance(agents, dict):
        raise ValueError("'agents' field must be a JSON object mapping model_id to agent_type")

    for model_id, agent_type in agents.items():
        if not isinstance(model_id, str):
            raise ValueError(f"Model ID keys must be strings, got: {type(model_id)}")
        if not isinstance(agent_type, str):
            raise ValueError(f"Agent type for '{model_id}' must be a string, got: {type(agent_type)}")
        if agent_type not in _ALLOWED_AGENT_TYPES:
            raise ValueError(f"Unknown agent type '{agent_type}' for model '{model_id}'. Allowed: {list(_ALLOWED_AGENT_TYPES)}")

    return {"agents": agents}


def _execute_agent(model_id: str, agent_type: str, input_value: Any) -> Any:
    """
    Safely execute a deterministic agent transformation.
    No dynamic code execution.
    """
    if agent_type == "identity":
        return input_value
    elif agent_type == "prefix":
        return f"[{model_id}] {input_value}" if isinstance(input_value, str) else f"[{model_id}] {input_value}"
    elif agent_type == "suffix":
        return f"{input_value} [{model_id}]" if isinstance(input_value, str) else f"{input_value} [{model_id}]"
    elif agent_type == "uppercase":
        return str(input_value).upper()
    elif agent_type == "lowercase":
        return str(input_value).lower()
    elif agent_type == "reverse":
        return str(input_value)[::-1]
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


class PSN_Agent_Loop_Init:
    """
    Initializes the loop state for batched multi-model agent orchestration.
    Takes a list of model IDs and a JSON agent configuration, and outputs
    the loop state (a dict) and the starting index (0).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_ids": ("STRING", {"multiline": True, "default": "model_a\nmodel_b"}),
                "agent_config": ("STRING", {"multiline": True, "default": '{"agents": {"model_a": "identity", "model_b": "uppercase"}}'}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("ANY", "INT")
    RETURN_NAMES = ("loop_state", "current_index")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_ids: str, agent_config: str) -> Tuple[Dict[str, Any], int]:
        # Parse model_ids: newline-separated list
        if not isinstance(model_ids, str):
            raise ValueError("model_ids must be a string")
        ids = [line.strip() for line in model_ids.splitlines() if line.strip()]
        if not ids:
            raise ValueError("model_ids must contain at least one model ID")

        # Validate and parse agent config
        config = _validate_agent_config(agent_config)

        # Check that all model IDs have a corresponding agent config
        agents = config["agents"]
        missing = [mid for mid in ids if mid not in agents]
        if missing:
            raise ValueError(f"Missing agent configuration for model IDs: {missing}")

        loop_state = {
            "model_ids": ids,
            "agents": agents,
            "results": [],
        }
        return (loop_state, 0)


class PSN_Agent_Executor:
    """
    Executes the agent for the current model ID in the loop.
    Takes the loop state, current index, and model ID, and returns the
    result, next index, and whether the loop is done.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "loop_state": ("ANY",),
                "current_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "model_id": ("STRING", {"default": ""}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("ANY", "INT", "BOOLEAN")
    RETURN_NAMES = ("result", "next_index", "loop_done")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, loop_state: Dict[str, Any], current_index: int, model_id: str) -> Tuple[Any, int, bool]:
        if not isinstance(loop_state, dict):
            raise ValueError("loop_state must be a dict")
        if not isinstance(current_index, int):
            raise ValueError("current_index must be an integer")
        if current_index < 0:
            raise ValueError("current_index must be non-negative")

        model_ids = loop_state.get("model_ids", [])
        agents = loop_state.get("agents", {})
        results = loop_state.get("results", [])

        if current_index >= len(model_ids):
            return (None, current_index, True)

        # Use the model_id from the loop state to ensure consistency
        actual_model_id = model_ids[current_index]
        if model_id and model_id != actual_model_id:
            raise ValueError(f"model_id mismatch: expected '{actual_model_id}', got '{model_id}'")

        agent_type = agents.get(actual_model_id)
        if agent_type is None:
            raise ValueError(f"No agent configured for model '{actual_model_id}'")

        # Execute the agent with a deterministic input derived from the model ID
        input_value = f"input_for_{actual_model_id}"
        result = _execute_agent(actual_model_id, agent_type, input_value)

        # Update results in the loop state
        results.append(result)
        loop_state["results"] = results

        next_index = current_index + 1
        loop_done = next_index >= len(model_ids)

        return (result, next_index, loop_done)


class PSN_Agent_Aggregator:
    """
    Aggregates results from all agents into a single output structure.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "results": ("ANY",),
            },
            "optional": {},
        }

    RETURN_TYPES = ("ANY",)
    RETURN_NAMES = ("final_output",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, results: Any) -> Dict[str, Any]:
        if not isinstance(results, list):
            raise ValueError("results must be a list")

        final_output = {
            "count": len(results),
            "results": results,
        }
        return (final_output,)


# Module-level mappings
NODE_CLASS_MAPPINGS = {
    "PSN_Agent_Loop_Init": PSN_Agent_Loop_Init,
    "PSN_Agent_Executor": PSN_Agent_Executor,
    "PSN_Agent_Aggregator": PSN_Agent_Aggregator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Agent_Loop_Init": "Agent Loop Init",
    "PSN_Agent_Executor": "Agent Executor",
    "PSN_Agent_Aggregator": "Agent Aggregator",
}
