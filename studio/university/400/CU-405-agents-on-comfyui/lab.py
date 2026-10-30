import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define a simple node specification dictionary
# This represents the "schema" of allowed nodes in our ComfyUI-like graph
NODE_SPECS = {
    "KSampler": {
        "required_inputs": ["model", "seed", "steps"],
        "optional_inputs": ["cfg", "sampler_name"]
    },
    "CheckpointLoader": {
        "required_inputs": ["ckpt_name"],
        "optional_inputs": []
    },
    "VAEDecode": {
        "required_inputs": ["samples", "vae"],
        "optional_inputs": []
    },
    "CLIPTextEncode": {
        "required_inputs": ["text", "clip"],
        "optional_inputs": []
    }
}

def verify_graph(graph):
    """
    Verify a JSON graph against NODE_SPECS.
    Returns a list of problem strings. Empty list means valid.
    """
    problems = []
    
    # Step 1: Check that all nodes have a known class_type
    for node_id, node in graph.items():
        class_type = node.get("class_type")
        if class_type not in NODE_SPECS:
            problems.append(f"Node {node_id} has unknown class_type: {class_type}")
    
    # Step 2: Check required inputs are present
    for node_id, node in graph.items():
        class_type = node.get("class_type")
        if class_type in NODE_SPECS:
            required = NODE_SPECS[class_type]["required_inputs"]
            inputs = node.get("inputs", {})
            for req in required:
                if req not in inputs:
                    problems.append(f"Node {node_id} ({class_type}) missing required input: {req}")
    
    # Step 3: Check that link targets exist
    # Links are represented as [source_node_id, source_output_index]
    for node_id, node in graph.items():
        inputs = node.get("inputs", {})
        for input_name, value in inputs.items():
            # If value is a list of length 2, it's a link
            if isinstance(value, list) and len(value) == 2:
                source_id = value[0]
                if source_id not in graph:
                    problems.append(f"Node {node_id} input {input_name} links to non-existent node: {source_id}")
    
    # Step 4: Check for cycles using DFS
    # Build adjacency list
    adj = collections.defaultdict(list)
    for node_id, node in graph.items():
        inputs = node.get("inputs", {})
        for input_name, value in inputs.items():
            if isinstance(value, list) and len(value) == 2:
                source_id = value[0]
                if source_id in graph:
                    adj[node_id].append(source_id)
    
    # DFS to detect cycles
    visited = set()
    rec_stack = set()
    
    def dfs(node_id):
        visited.add(node_id)
        rec_stack.add(node_id)
        for neighbor in adj[node_id]:
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.remove(node_id)
        return False
    
    for node_id in graph:
        if node_id not in visited:
            if dfs(node_id):
                problems.append("Graph contains a cycle")
                break
    
    return problems

# Define five test graphs
# Graph 1: Valid graph
graph_valid = {
    "1": {
        "class_type": "CheckpointLoader",
        "inputs": {"ckpt_name": "sd15.safetensors"}
    },
    "2": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "seed": 42,
            "steps": 20
        }
    },
    "3": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["2", 0],
            "vae": ["1", 1]
        }
    }
}

# Graph 2: Unknown class_type
graph_unknown_class = {
    "1": {
        "class_type": "NonExistentNode",
        "inputs": {}
    }
}

# Graph 3: Missing required input
graph_missing_input = {
    "1": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["2", 0],
            "seed": 42
            # Missing "steps"
        }
    },
    "2": {
        "class_type": "CheckpointLoader",
        "inputs": {"ckpt_name": "sd15.safetensors"}
    }
}

# Graph 4: Link to non-existent node
graph_bad_link = {
    "1": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["99", 0],  # Node 99 doesn't exist
            "seed": 42,
            "steps": 20
        }
    }
}

# Graph 5: Cycle (A -> B -> A)
graph_cycle = {
    "1": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["2", 0],
            "seed": 42,
            "steps": 20
        }
    },
    "2": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],  # Links back to node 1
            "seed": 43,
            "steps": 20
        }
    }
}

# Run verification on all five graphs
graphs = {
    "valid": graph_valid,
    "unknown_class": graph_unknown_class,
    "missing_input": graph_missing_input,
    "bad_link": graph_bad_link,
    "cycle": graph_cycle
}

results = {}
for name, graph in graphs.items():
    problems = verify_graph(graph)
    results[name] = problems
    # Print problems found
    if problems:
        for p in problems:
            print(f"RESULT {name} = {p}")
    else:
        print(f"RESULT {name} = VALID")

# Assert statements to check the concept holds
# 1. The valid graph should have no problems
assert len(results["valid"]) == 0, "Valid graph should have no problems"

# 2. The cycle graph should have exactly one problem (the cycle)
assert len(results["cycle"]) == 1 and "cycle" in results["cycle"][0].lower(), "Cycle graph should have exactly one cycle problem"

# 3. The unknown class graph should have a problem mentioning unknown class_type
assert any("unknown class_type" in p for p in results["unknown_class"]), "Unknown class graph should report unknown class_type"

# 4. The missing input graph should have a problem mentioning missing required input
assert any("missing required input" in p for p in results["missing_input"]), "Missing input graph should report missing required input"

# 5. The bad link graph should have a problem mentioning non-existent node
assert any("non-existent node" in p for p in results["bad_link"]), "Bad link graph should report non-existent node"

# Print a summary as a single line for each graph
for name in graphs:
    if results[name]:
        # Join all problems with semicolons
        summary = "; ".join(results[name])
        print(f"RESULT {name} = {summary}")
    else:
        print(f"RESULT {name} = VALID")
