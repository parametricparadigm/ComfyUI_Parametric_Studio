"""Cycle detection for dependency graphs in pipeline definitions.

ComfyUI custom node that validates a dependency graph (given as a
newline-separated list of "source -> target" edges) is acyclic before
execution, preventing infinite loops in pipeline stage ordering.
"""

import torch

CAT = "ParametricStudio/Pipeline"


def _parse_edges(edges_text):
    """Parse a string of edges into a list of (src, dst) tuples.

    Each non-empty line must be of the form 'A -> B' (whitespace tolerant).
    Returns (edges, nodes) where edges is a list of tuples and nodes is a
    sorted list of all node names seen.
    """
    edges = []
    nodes = set()
    for raw in edges_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "->" not in line:
            raise ValueError(f"Invalid edge line (expected 'A -> B'): {line!r}")
        parts = line.split("->")
        if len(parts) != 2:
            raise ValueError(f"Invalid edge line (too many arrows): {line!r}")
        src = parts[0].strip()
        dst = parts[1].strip()
        if not src or not dst:
            raise ValueError(f"Invalid edge line (empty node name): {line!r}")
        edges.append((src, dst))
        nodes.add(src)
        nodes.add(dst)
    return edges, sorted(nodes)


def _detect_cycle(edges, nodes):
    """Detect a cycle in a directed graph using iterative DFS (white/gray/black).

    Returns (has_cycle, cycle_path) where cycle_path is a list of node names
    forming the cycle (first == last) if a cycle exists, else [].
    """
    adj = {n: [] for n in nodes}
    for src, dst in edges:
        adj[src].append(dst)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    parent = {}

    for start in nodes:
        if color[start] != WHITE:
            continue
        # Iterative DFS with explicit stack of (node, child_index)
        stack = [(start, 0)]
        color[start] = GRAY
        while stack:
            node, idx = stack[-1]
            children = adj[node]
            if idx < len(children):
                stack[-1] = (node, idx + 1)
                child = children[idx]
                if color[child] == GRAY:
                    # Found a back edge -> cycle
                    # Reconstruct cycle from child back to node
                    cycle = [child]
                    cur = node
                    while cur != child:
                        cycle.append(cur)
                        cur = parent.get(cur, cur)
                    cycle.append(child)
                    cycle.reverse()
                    return True, cycle
                elif color[child] == WHITE:
                    color[child] = GRAY
                    parent[child] = node
                    stack.append((child, 0))
            else:
                color[node] = BLACK
                stack.pop()

    return False, []


def _topo_sort(edges, nodes):
    """Kahn's algorithm for topological sort. Returns (sorted_list, is_dag).

    If the graph has a cycle, is_dag is False and sorted_list contains only
    the nodes that could be ordered.
    """
    adj = {n: [] for n in nodes}
    in_deg = {n: 0 for n in nodes}
    for src, dst in edges:
        adj[src].append(dst)
        in_deg[dst] += 1

    from collections import deque
    queue = deque(n for n in nodes if in_deg[n] == 0)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for child in adj[node]:
            in_deg[child] -= 1
            if in_deg[child] == 0:
                queue.append(child)

    is_dag = len(order) == len(nodes)
    return order, is_dag


class PSN_DependencyGraphCycleCheck:
    """Validate that a pipeline dependency graph is acyclic.

    Input: a text string with one edge per line in the form 'A -> B'.
    Output: a boolean (True = acyclic / safe to execute), the topological
    order as a string, and a diagnostic message.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "edges": (
                    "STRING",
                    {"multiline": True, "default": ""},
                ),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("is_acyclic", "topo_order", "diagnostics")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, edges):
        if not isinstance(edges, str):
            raise TypeError("edges must be a string")

        if not edges.strip():
            return (True, "", "Empty graph: trivially acyclic.")

        parsed_edges, nodes = _parse_edges(edges)

        if not parsed_edges:
            return (True, ", ".join(nodes), "No edges: trivially acyclic.")

        has_cycle, cycle_path = _detect_cycle(parsed_edges, nodes)
        topo, is_dag = _topo_sort(parsed_edges, nodes)

        if has_cycle:
            diag = "CYCLE DETECTED: " + " -> ".join(cycle_path)
            return (False, ", ".join(topo), diag)
        else:
            diag = f"Acyclic. {len(nodes)} nodes, {len(parsed_edges)} edges."
            return (True, ", ".join(topo), diag)


NODE_CLASS_MAPPINGS = {
    "PSN_DependencyGraphCycleCheck": PSN_DependencyGraphCycleCheck,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_DependencyGraphCycleCheck": "Dependency Graph Cycle Check",
}
