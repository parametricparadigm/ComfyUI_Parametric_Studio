"""Tests for h_cycle_detection_for_dependency_gra."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from h_cycle_detection_for_dependency_gra import (
    PSN_DependencyGraphCycleCheck,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_edges,
    _detect_cycle,
    _topo_sort,
)

node = PSN_DependencyGraphCycleCheck()

# 1. Simple acyclic graph: A -> B -> C
is_acyclic, topo, diag = node.run("A -> B\nB -> C")
assert is_acyclic is True, f"Expected acyclic, got {is_acyclic}"
assert "A" in topo and "B" in topo and "C" in topo, f"Topo missing nodes: {topo}"
# A must come before B, B before C
assert topo.index("A") < topo.index("B") < topo.index("C"), f"Bad topo order: {topo}"

# 2. Simple cycle: A -> B -> C -> A
is_acyclic, topo, diag = node.run("A -> B\nB -> C\nC -> A")
assert is_acyclic is False, f"Expected cycle detected, got {is_acyclic}"
assert "CYCLE DETECTED" in diag, f"Expected cycle in diagnostics: {diag}"

# 3. Self-loop: A -> A
is_acyclic, topo, diag = node.run("A -> A")
assert is_acyclic is False, f"Self-loop should be a cycle, got {is_acyclic}"
assert "CYCLE DETECTED" in diag, f"Expected cycle in diagnostics: {diag}"

# 4. Empty graph
is_acyclic, topo, diag = node.run("")
assert is_acyclic is True, f"Empty graph should be acyclic, got {is_acyclic}"

# 5. Graph with no edges but nodes mentioned (single line with no arrow is invalid,
#    so test with just comments)
is_acyclic, topo, diag = node.run("# just a comment")
assert is_acyclic is True, f"Comment-only should be acyclic, got {is_acyclic}"

# 6. Invalid edge line (no arrow)
try:
    node.run("A B")
    assert False, "Expected ValueError for invalid edge line"
except ValueError as e:
    assert "Invalid edge line" in str(e), f"Wrong error: {e}"

# 7. Invalid edge line (empty node name)
try:
    node.run(" -> B")
    assert False, "Expected ValueError for empty node name"
except ValueError as e:
    assert "empty node name" in str(e), f"Wrong error: {e}"

# 8. Non-string input
try:
    node.run(12345)
    assert False, "Expected TypeError for non-string input"
except TypeError as e:
    assert "string" in str(e), f"Wrong error: {e}"

# 9. Diamond graph (acyclic): A -> B, A -> C, B -> D, C -> D
is_acyclic, topo, diag = node.run("A -> B\nA -> C\nB -> D\nC -> D")
assert is_acyclic is True, f"Diamond should be acyclic, got {is_acyclic}"
assert topo.index("A") < topo.index("B") < topo.index("D"), f"Bad topo: {topo}"
assert topo.index("A") < topo.index("C") < topo.index("D"), f"Bad topo: {topo}"

# 10. Larger cycle: A -> B -> C -> D -> B (cycle B->C->D->B)
is_acyclic, topo, diag = node.run("A -> B\nB -> C\nC -> D\nD -> B")
assert is_acyclic is False, f"Expected cycle, got {is_acyclic}"
assert "CYCLE DETECTED" in diag, f"Expected cycle in diagnostics: {diag}"

# 11. Module-level mappings exist and are correct
assert "PSN_DependencyGraphCycleCheck" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_DependencyGraphCycleCheck"] is PSN_DependencyGraphCycleCheck
assert "PSN_DependencyGraphCycleCheck" in NODE_DISPLAY_NAME_MAPPINGS

# 12. INPUT_TYPES classmethod works
it = PSN_DependencyGraphCycleCheck.INPUT_TYPES()
assert "required" in it
assert "edges" in it["required"]

# 13. RETURN_TYPES and FUNCTION
assert PSN_DependencyGraphCycleCheck.RETURN_TYPES == ("BOOLEAN", "STRING", "STRING")
assert PSN_DependencyGraphCycleCheck.FUNCTION == "run"
assert PSN_DependencyGraphCycleCheck.CATEGORY == "ParametricStudio/Pipeline"

# 14. Whitespace tolerance in edges
is_acyclic, topo, diag = node.run("  A   ->   B  \n  B   ->   C  ")
assert is_acyclic is True, f"Whitespace-tolerant edges should work, got {is_acyclic}"
assert topo.index("A") < topo.index("B") < topo.index("C"), f"Bad topo: {topo}"

# 15. _parse_edges returns correct structure
edges, nodes = _parse_edges("X -> Y\nY -> Z")
assert edges == [("X", "Y"), ("Y", "Z")], f"Wrong edges: {edges}"
assert nodes == ["X", "Y", "Z"], f"Wrong nodes: {nodes}"

# 16. _topo_sort on a DAG
order, is_dag = _topo_sort([("A", "B"), ("B", "C")], ["A", "B", "C"])
assert is_dag is True
assert order == ["A", "B", "C"], f"Wrong topo: {order}"

# 17. _topo_sort on a cycle
order, is_dag = _topo_sort([("A", "B"), ("B", "C"), ("C", "A")], ["A", "B", "C"])
assert is_dag is False, f"Cycle should not be a DAG"

# 18. Two disconnected components, both acyclic
is_acyclic, topo, diag = node.run("A -> B\nX -> Y")
assert is_acyclic is True, f"Disconnected acyclic should be acyclic, got {is_acyclic}"
assert "A" in topo and "B" in topo and "X" in topo and "Y" in topo

print("ok")
