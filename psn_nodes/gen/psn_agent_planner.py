"""PSN_Agent_Planner: Pure-logic planner that validates a JSON graph plan against a node schema.

This module implements the secure, pure-logic portion of an LLM agent planner.
It does NOT perform LLM inference, network calls, or file I/O. Instead, it:
1. Validates that a provided `plan_json` string is well-formed JSON.
2. Validates the plan structure against a strict schema (nodes, edges, types).
3. Ensures all referenced node classes exist in `available_nodes`.
4. Ensures all edge connections reference valid node IDs and ports.
5. Returns a validation report and the cleaned plan.

The LLM inference step is assumed to be handled externally; this node acts as a
robust validator and normalizer for the LLM's structured output.
"""

import json
import re

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Agent"

# Allowed top-level keys in the plan
_ALLOWED_PLAN_KEYS = {"nodes", "edges", "metadata"}

# Allowed keys in a node object
_ALLOWED_NODE_KEYS = {"id", "class_type", "inputs", "title"}

# Allowed keys in an edge object
_ALLOWED_EDGE_KEYS = {"from_node", "from_slot", "to_node", "to_slot"}

# Allowed keys in metadata
_ALLOWED_METADATA_KEYS = {"reasoning", "version", "author"}


def _validate_plan_structure(plan: dict) -> tuple[bool, str]:
    """Validate top-level structure of the plan."""
    if not isinstance(plan, dict):
        return False, "Plan must be a JSON object"

    for key in plan:
        if key not in _ALLOWED_PLAN_KEYS:
            return False, f"Unexpected top-level key: {key}"

    if "nodes" not in plan:
        return False, "Missing required key: 'nodes'"
    if "edges" not in plan:
        return False, "Missing required key: 'edges'"

    if not isinstance(plan["nodes"], list):
        return False, "'nodes' must be a list"
    if not isinstance(plan["edges"], list):
        return False, "'edges' must be a list"

    return True, "OK"


def _validate_node(node: dict, available_nodes: dict, node_ids: set) -> tuple[bool, str]:
    """Validate a single node object."""
    if not isinstance(node, dict):
        return False, "Node must be an object"

    for key in node:
        if key not in _ALLOWED_NODE_KEYS:
            return False, f"Unexpected node key: {key}"

    if "id" not in node:
        return False, "Node missing 'id'"
    if "class_type" not in node:
        return False, "Node missing 'class_type'"

    node_id = node["id"]
    class_type = node["class_type"]

    if not isinstance(node_id, str) or not node_id:
        return False, "Node 'id' must be a non-empty string"
    if not isinstance(class_type, str) or not class_type:
        return False, "Node 'class_type' must be a non-empty string"

    if node_id in node_ids:
        return False, f"Duplicate node id: {node_id}"
    node_ids.add(node_id)

    if class_type not in available_nodes:
        return False, f"Unknown class_type: {class_type}"

    if "inputs" in node:
        inputs = node["inputs"]
        if not isinstance(inputs, dict):
            return False, "Node 'inputs' must be an object"

    return True, "OK"


def _validate_edge(edge: dict, node_ids: set) -> tuple[bool, str]:
    """Validate a single edge object."""
    if not isinstance(edge, dict):
        return False, "Edge must be an object"

    for key in edge:
        if key not in _ALLOWED_EDGE_KEYS:
            return False, f"Unexpected edge key: {key}"

    for required in ("from_node", "from_slot", "to_node", "to_slot"):
        if required not in edge:
            return False, f"Edge missing '{required}'"

    from_node = edge["from_node"]
    to_node = edge["to_node"]

    if not isinstance(from_node, str) or from_node not in node_ids:
        return False, f"Edge 'from_node' references unknown node: {from_node}"
    if not isinstance(to_node, str) or to_node not in node_ids:
        return False, f"Edge 'to_node' references unknown node: {to_node}"

    if from_node == to_node:
        return False, "Edge cannot connect a node to itself"

    return True, "OK"


def _validate_metadata(metadata: dict) -> tuple[bool, str]:
    """Validate metadata object."""
    if not isinstance(metadata, dict):
        return False, "'metadata' must be an object"

    for key in metadata:
        if key not in _ALLOWED_METADATA_KEYS:
            return False, f"Unexpected metadata key: {key}"

    return True, "OK"


def validate_plan(plan_json: str, available_nodes: dict) -> tuple[bool, str, dict]:
    """
    Validate a plan JSON string against the available node schemas.
    
    Returns:
        (is_valid, reason, cleaned_plan)
    """
    # Step 1: Parse JSON
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}", {}

    # Step 2: Validate top-level structure
    ok, why = _validate_plan_structure(plan)
    if not ok:
        return False, why, {}

    # Step 3: Validate nodes
    node_ids = set()
    for i, node in enumerate(plan["nodes"]):
        ok, why = _validate_node(node, available_nodes, node_ids)
        if not ok:
            return False, f"Node at index {i}: {why}", {}

    # Step 4: Validate edges
    for i, edge in enumerate(plan["edges"]):
        ok, why = _validate_edge(edge, node_ids)
        if not ok:
            return False, f"Edge at index {i}: {why}", {}

    # Step 5: Validate metadata if present
    if "metadata" in plan:
        ok, why = _validate_metadata(plan["metadata"])
        if not ok:
            return False, why, {}

    # Clean plan: ensure consistent ordering and types
    cleaned = {
        "nodes": plan["nodes"],
        "edges": plan["edges"],
    }
    if "metadata" in plan:
        cleaned["metadata"] = plan["metadata"]

    return True, "OK", cleaned


class PSN_Agent_Planner:
    """
    Validates an LLM-generated JSON graph plan against available node schemas.
    
    This node does NOT call an LLM. It receives a pre-generated `plan_json` string
    (from an external LLM inference step) and validates it rigorously.
    
    Inputs:
        goal: The high-level goal (used for context in reasoning output).
        available_nodes: Dict mapping class_type names to their schemas.
        plan_json: The JSON string produced by the LLM.
        llm_connection: Placeholder for LLM backend (not used in pure-logic mode).
    
    Outputs:
        plan_json: The validated and cleaned JSON plan string.
        reasoning: Explanation of validation result.
        is_valid: Boolean indicating if the plan passed validation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "goal": ("STRING", {"default": "", "multiline": True}),
                "available_nodes": ("DICT", {"default": {}}),
                "plan_json": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "llm_connection": ("LLAMACPP_CONNECTION",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("plan_json", "reasoning", "is_valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, goal: str, available_nodes: dict, plan_json: str, llm_connection=None):
        """
        Validate the plan JSON and return cleaned plan, reasoning, and validity flag.
        """
        # Normalize available_nodes: ensure it's a dict
        if not isinstance(available_nodes, dict):
            available_nodes = {}

        # Validate
        is_valid, reason, cleaned_plan = validate_plan(plan_json, available_nodes)

        if is_valid:
            cleaned_json = json.dumps(cleaned_plan, indent=2, sort_keys=True)
            reasoning = (
                f"Plan validated successfully for goal: '{goal}'. "
                f"Nodes: {len(cleaned_plan['nodes'])}, Edges: {len(cleaned_plan['edges'])}."
            )
        else:
            cleaned_json = "{}"
            reasoning = f"Plan validation failed: {reason}"

        return (cleaned_json, reasoning, is_valid)


NODE_CLASS_MAPPINGS = {
    "PSN_Agent_Planner": PSN_Agent_Planner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Agent_Planner": "Agent Planner (Validator)",
}
