import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# --- Step 1: Define a toy dependency graph ---
# Each node has:
#   - 'inputs': list of node names (strings) that this node depends on
#   - 'fn': a function that takes tensors (in input order) and returns a tensor
# We'll build a small graph:
#   A = constant tensor [1.0]
#   B = constant tensor [2.0]
#   C = A + B
#   D = C * 2
#   E = D + 1
#   F = E * 3
#   G = F + B  (B is reused)

# Define nodes as a dictionary
nodes = {
    'A': {
        'inputs': [],
        'fn': lambda: torch.tensor([1.0], dtype=torch.float32)
    },
    'B': {
        'inputs': [],
        'fn': lambda: torch.tensor([2.0], dtype=torch.float32)
    },
    'C': {
        'inputs': ['A', 'B'],
        'fn': lambda a, b: a + b
    },
    'D': {
        'inputs': ['C'],
        'fn': lambda c: c * 2
    },
    'E': {
        'inputs': ['D'],
        'fn': lambda d: d + 1
    },
    'F': {
        'inputs': ['E'],
        'fn': lambda e: e * 3
    },
    'G': {
        'inputs': ['F', 'B'],
        'fn': lambda f, b: f + b
    }
}

# --- Step 2: Compute topological execution order ---
# Use Kahn's algorithm to get a valid execution order
def topological_sort(nodes):
    # Build in-degree count and adjacency list
    in_degree = {name: 0 for name in nodes}
    dependents = collections.defaultdict(list)  # node -> list of nodes that depend on it
    
    for name, node in nodes.items():
        for input_name in node['inputs']:
            in_degree[name] += 1
            dependents[input_name].append(name)
    
    # Start with nodes that have no dependencies
    queue = collections.deque([name for name, deg in in_degree.items() if deg == 0])
    order = []
    
    while queue:
        node = queue.popleft()
        order.append(node)
        for dependent in dependents[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    if len(order) != len(nodes):
        raise ValueError("Cycle detected in graph")
    
    return order

execution_order = topological_sort(nodes)
print(f"RESULT execution_order = {execution_order}")

# --- Step 3: Implement cached execution ---
# Cache is keyed by (node_name, input_hash)
# input_hash is computed from the actual tensor values of inputs

def compute_input_hash(input_tensors):
    """Compute a hash from input tensors for caching."""
    # Convert tensors to tuples of floats for hashing
    hash_parts = []
    for tensor in input_tensors:
        if tensor is not None:
            hash_parts.extend(tensor.tolist())
    return tuple(hash_parts)

def get_descendants(nodes, start_node):
    """Get all descendants of start_node (including itself)."""
    # Build reverse dependency graph
    dependents = collections.defaultdict(list)
    for name, node in nodes.items():
        for input_name in node['inputs']:
            dependents[input_name].append(name)
    
    # BFS from start_node to find all descendants
    descendants = set()
    queue = collections.deque([start_node])
    while queue:
        node = queue.popleft()
        if node not in descendants:
            descendants.add(node)
            for dependent in dependents[node]:
                queue.append(dependent)
    
    return descendants

def execute_graph(nodes, execution_order, results_cache=None, changed_node=None):
    """
    Execute the graph, optionally re-running only descendants of changed_node.
    
    Args:
        nodes: dict of node definitions
        execution_order: topological order of nodes
        results_cache: dict of node_name -> tensor (previous results)
        changed_node: if set, only recompute this node and its descendants
    
    Returns:
        - results: dict of node_name -> tensor
        - recompute_count: number of nodes recomputed
    """
    results = {}
    recompute_count = 0
    
    # Determine which nodes to recompute
    if changed_node is None:
        # Full execution: compute all nodes
        nodes_to_compute = set(execution_order)
    else:
        # Only recompute changed_node and its descendants
        nodes_to_compute = get_descendants(nodes, changed_node)
    
    # Execute in topological order
    for node_name in execution_order:
        if node_name not in nodes_to_compute:
            # Skip this node, use cached result if available
            if results_cache is not None and node_name in results_cache:
                results[node_name] = results_cache[node_name]
            continue
        
        node = nodes[node_name]
        
        # Gather input tensors from results
        input_tensors = []
        for input_name in node['inputs']:
            if input_name not in results:
                raise ValueError(f"Input {input_name} not computed before {node_name}")
            input_tensors.append(results[input_name])
        
        # Compute the node
        if node['inputs']:
            result = node['fn'](*input_tensors)
        else:
            result = node['fn']()
        
        results[node_name] = result
        recompute_count += 1
    
    return results, recompute_count

# --- Step 4: First full execution ---
results1, recompute1 = execute_graph(nodes, execution_order)
print(f"RESULT recompute_count_full = {recompute1}")
print(f"RESULT G_value = {results1['G'].item():.6g}")

# --- Step 5: Change node B and re-execute ---
# Modify B's value
nodes['B']['fn'] = lambda: torch.tensor([5.0], dtype=torch.float32)

# Re-execute with changed_node='B', using previous results as cache
results2, recompute2 = execute_graph(nodes, execution_order, results_cache=results1, changed_node='B')
print(f"RESULT recompute_count_changed_B = {recompute2}")
print(f"RESULT G_value_after_B_change = {results2['G'].item():.6g}")

# --- Step 6: Verify that only descendants of B were recomputed ---
# B's descendants: B, C, D, E, F, G (A is not a descendant)
# So we should recompute 6 nodes: B, C, D, E, F, G

# A should not be recomputed, so its result should be the same
assert results1['A'].item() == results2['A'].item(), "A should not be recomputed when B changes"

# G should have a different value because B changed
# Original: A=1, B=2, C=3, D=6, E=7, F=21, G=21+2=23
# New: A=1, B=5, C=6, D=12, E=13, F=39, G=39+5=44
assert abs(results2['G'].item() - 44.0) < 1e-6, f"G should be 44, got {results2['G'].item()}"

# The number of recomputations should be 6 (B, C, D, E, F, G)
assert recompute2 == 6, f"Expected 6 recomputations, got {recompute2}"

print("RESULT all_asserts_passed = True")
