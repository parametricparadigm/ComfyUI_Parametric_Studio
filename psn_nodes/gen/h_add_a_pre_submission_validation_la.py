"""Pre-submission validation layer for dynamically generated ComfyUI graphs.

Enforces 'never-wire' rules before a graph is submitted to the backend.
This prevents invalid or dangerous node connections from reaching ComfyUI
when graphs are constructed by LLMs or other automated systems.
"""

import torch

CAT = "ParametricStudio/Validation"

# Default never-wire rules: pairs of (source_class, target_class) that must never be connected.
# These represent dangerous or invalid connections in ComfyUI graphs.
DEFAULT_NEVER_WIRE_RULES = [
    # Never wire a model output directly to another model input (prevents model chaining errors)
    ("KSampler", "KSampler"),
    # Never wire a latent output to an image input (type mismatch)
    ("VAEDecode", "VAEEncode"),
    # Never wire a mask to a model input
    ("MaskToImage", "KSampler"),
    # Never wire an image to a latent input without proper conversion
    ("ImageToLatent", "KSampler"),
]


def _validate_graph_structure(graph):
    """Validate basic graph structure: nodes must be dicts with required fields."""
    errors = []
    if not isinstance(graph, dict):
        errors.append("Graph must be a dictionary")
        return errors

    nodes = graph.get("nodes", {})
    if not isinstance(nodes, dict):
        errors.append("'nodes' must be a dictionary")
        return errors

    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            errors.append(f"Node {node_id} must be a dictionary")
            continue
        if "class_type" not in node:
            errors.append(f"Node {node_id} missing 'class_type'")
        if "inputs" not in node or not isinstance(node.get("inputs"), dict):
            errors.append(f"Node {node_id} missing or invalid 'inputs'")
    return errors


def _check_never_wire_rules(graph, rules):
    """Check for never-wire rule violations in the graph."""
    violations = []
    nodes = graph.get("nodes", {})

    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            continue
        target_class = node.get("class_type", "")
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            continue

        for input_name, input_val in inputs.items():
            # Input links are represented as [source_node_id, output_index]
            if isinstance(input_val, list) and len(input_val) == 2:
                source_node_id = input_val[0]
                source_node = nodes.get(source_node_id)
                if source_node is None:
                    violations.append(
                        f"Node {node_id} input '{input_name}' references non-existent node {source_node_id}"
                    )
                    continue
                source_class = source_node.get("class_type", "")
                for src_cls, tgt_cls in rules:
                    if source_class == src_cls and target_class == tgt_cls:
                        violations.append(
                            f"Never-wire violation: {source_class} ({source_node_id}) -> "
                            f"{target_class} ({node_id}) input '{input_name}'"
                        )
    return violations


def _check_dangling_inputs(graph):
    """Check for inputs that reference non-existent nodes."""
    errors = []
    nodes = graph.get("nodes", {})
    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        for input_name, input_val in inputs.items():
            if isinstance(input_val, list) and len(input_val) == 2:
                source_node_id = input_val[0]
                if source_node_id not in nodes:
                    errors.append(
                        f"Node {node_id} input '{input_name}' references non-existent node {source_node_id}"
                    )
    return errors


def _check_cycle(graph):
    """Check for cycles in the graph (should be a DAG)."""
    nodes = graph.get("nodes", {})
    # Build adjacency list
    adj = {node_id: [] for node_id in nodes}
    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        for input_name, input_val in inputs.items():
            if isinstance(input_val, list) and len(input_val) == 2:
                source_node_id = input_val[0]
                if source_node_id in adj:
                    adj[source_node_id].append(node_id)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in nodes}

    def dfs(node_id):
        color[node_id] = GRAY
        for neighbor in adj.get(node_id, []):
            if color.get(neighbor, WHITE) == GRAY:
                return True
            if color.get(neighbor, WHITE) == WHITE:
                if dfs(neighbor):
                    return True
        color[node_id] = BLACK
        return False

    for node_id in nodes:
        if color.get(node_id, WHITE) == WHITE:
            if dfs(node_id):
                return [f"Cycle detected in graph involving node {node_id}"]
    return []


def validate_graph(graph, never_wire_rules=None):
    """Validate a ComfyUI graph before submission.

    Args:
        graph: Dictionary representing the ComfyUI API graph.
        never_wire_rules: Optional list of (source_class, target_class) tuples.

    Returns:
        Tuple of (is_valid: bool, errors: list[str])
    """
    if never_wire_rules is None:
        never_wire_rules = DEFAULT_NEVER_WIRE_RULES

    all_errors = []

    # 1. Structure validation
    all_errors.extend(_validate_graph_structure(graph))
    if all_errors:
        return (False, all_errors)

    # 2. Dangling input check
    all_errors.extend(_check_dangling_inputs(graph))

    # 3. Never-wire rule check
    all_errors.extend(_check_never_wire_rules(graph, never_wire_rules))

    # 4. Cycle detection
    all_errors.extend(_check_cycle(graph))

    return (len(all_errors) == 0, all_errors)


class PSN_PreSubmissionValidator:
    """Validate a ComfyUI graph before submission, enforcing never-wire rules.

    Takes a graph (as a JSON-serializable dict) and returns validation results.
    The graph is passed as a string (JSON) since ComfyUI nodes don't have a native
    'graph' input type. The output is a string with validation status and errors.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"default": "{}", "multiline": True}),
                "strict_mode": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "extra_rules_json": ("STRING", {"default": "[]", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("validation_report", "is_valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph_json, strict_mode, extra_rules_json=None):
        import json

        # Parse graph
        try:
            graph = json.loads(graph_json)
        except json.JSONDecodeError as e:
            report = f"ERROR: Invalid JSON in graph: {e}"
            return (report, False)

        # Parse extra rules if provided
        rules = list(DEFAULT_NEVER_WIRE_RULES)
        if extra_rules_json and extra_rules_json.strip():
            try:
                extra_rules = json.loads(extra_rules_json)
                if isinstance(extra_rules, list):
                    for rule in extra_rules:
                        if isinstance(rule, list) and len(rule) == 2:
                            rules.append((str(rule[0]), str(rule[1])))
            except json.JSONDecodeError:
                pass  # Ignore invalid extra rules

        # Validate
        is_valid, errors = validate_graph(graph, rules)

        # Build report
        if is_valid:
            report = "VALID: Graph passed all pre-submission checks."
        else:
            lines = ["INVALID: Graph failed pre-submission validation:"]
            for err in errors:
                lines.append(f"  - {err}")
            report = "\n".join(lines)

        # In strict mode, invalid graphs are flagged clearly
        if strict_mode and not is_valid:
            report = "[STRICT] " + report

        return (report, is_valid)


class PSN_NeverWireRuleChecker:
    """Check a specific connection against never-wire rules.

    Takes source and target node class types and checks if the connection
    is allowed. Returns whether the connection is valid and a description.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_class": ("STRING", {"default": "KSampler"}),
                "target_class": ("STRING", {"default": "KSampler"}),
            },
            "optional": {
                "extra_rules_json": ("STRING", {"default": "[]", "multiline": True}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_allowed", "description")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, source_class, target_class, extra_rules_json=None):
        import json

        rules = list(DEFAULT_NEVER_WIRE_RULES)
        if extra_rules_json and extra_rules_json.strip():
            try:
                extra_rules = json.loads(extra_rules_json)
                if isinstance(extra_rules, list):
                    for rule in extra_rules:
                        if isinstance(rule, list) and len(rule) == 2:
                            rules.append((str(rule[0]), str(rule[1])))
            except json.JSONDecodeError:
                pass

        for src_cls, tgt_cls in rules:
            if source_class == src_cls and target_class == tgt_cls:
                return (False, f"Connection {source_class} -> {target_class} is forbidden by never-wire rules.")

        return (True, f"Connection {source_class} -> {target_class} is allowed.")


NODE_CLASS_MAPPINGS = {
    "PSN_PreSubmissionValidator": PSN_PreSubmissionValidator,
    "PSN_NeverWireRuleChecker": PSN_NeverWireRuleChecker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PreSubmissionValidator": "Pre-Submission Graph Validator",
    "PSN_NeverWireRuleChecker": "Never-Wire Rule Checker",
}
