import json
import torch

from h_add_a_validation_layer_that_checks import (
    PSN_GraphValidationLayer,
    check_graph,
    _parse_rules,
    _node_classes,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# 1. Module-level mappings exist and are correct
assert "PSN_GraphValidationLayer" in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_GraphValidationLayer"] == "Graph Validation Layer"

# 2. INPUT_TYPES classmethod works
it = PSN_GraphValidationLayer.INPUT_TYPES()
assert "required" in it
assert "graph_json" in it["required"]
assert "rules" in it["required"]

# 3. RETURN_TYPES and FUNCTION
assert PSN_GraphValidationLayer.RETURN_TYPES == ("BOOLEAN", "STRING")
assert PSN_GraphValidationLayer.FUNCTION == "run"
assert PSN_GraphValidationLayer.CATEGORY == "ParametricStudio/Validation"

# 4. _parse_rules: valid pairs
rules = _parse_rules("A|B, C|D")
assert rules == [("A", "B"), ("C", "D")], rules

# 5. _parse_rules: single-node rule and empty parts
rules2 = _parse_rules("Solo, ,X|Y")
assert rules2 == [("Solo",), ("X", "Y")], rules2

# 6. _node_classes: dict-format graph
g1 = {"1": {"class_type": "KSampler"}, "2": {"class_type": "CLIPTextEncode"}}
assert _node_classes(g1) == {"KSampler", "CLIPTextEncode"}

# 7. _node_classes: list-format graph
g2 = {"nodes": [{"class_type": "VAEDecode"}, {"class_type": "SaveImage"}]}
assert _node_classes(g2) == {"VAEDecode", "SaveImage"}

# 8. check_graph: no violation
ok, viol = check_graph(g1, [("KSampler", "VAEDecode")])
assert ok is True
assert viol == []

# 9. check_graph: violation detected
ok2, viol2 = check_graph(g1, [("KSampler", "CLIPTextEncode")])
assert ok2 is False
assert len(viol2) == 1
assert viol2[0][0] == ("KSampler", "CLIPTextEncode")

# 10. Node run: valid graph passes
node = PSN_GraphValidationLayer()
graph_ok = json.dumps({"1": {"class_type": "KSampler"}, "2": {"class_type": "SaveImage"}})
ok_out, report = node.run(graph_ok, "KSampler|VAEDecode")
assert ok_out is True
assert "PASS" in report

# 11. Node run: forbidden combination fails
graph_bad = json.dumps({"1": {"class_type": "KSampler"}, "2": {"class_type": "VAEDecode"}})
ok_bad, report_bad = node.run(graph_bad, "KSampler|VAEDecode")
assert ok_bad is False
assert "FAIL" in report_bad
assert "KSampler" in report_bad

# 12. Node run: invalid JSON input
ok_err, report_err = node.run("not json", "A|B")
assert ok_err is False
assert "ERROR" in report_err

# 13. Node run: empty rules string passes
ok_empty, report_empty = node.run(graph_ok, "")
assert ok_empty is True
assert "No rules" in report_empty

# 14. Edge case: graph with no nodes
ok_nonodes, report_nonodes = node.run(json.dumps({}), "A|B")
assert ok_nonodes is True

# 15. Edge case: graph is a list (not dict) -> error
ok_list, report_list = node.run(json.dumps([1, 2, 3]), "A|B")
assert ok_list is False
assert "ERROR" in report_list

# 16. Multiple rules, one violated
multi_graph = json.dumps({
    "1": {"class_type": "A"},
    "2": {"class_type": "B"},
    "3": {"class_type": "C"},
})
ok_multi, report_multi = node.run(multi_graph, "A|B, C|D")
assert ok_multi is False
assert "A" in report_multi
assert "C" not in report_multi or "D" not in report_multi  # C|D not both present

# 17. Torch tensor sanity (ensure torch is available and CPU)
t = torch.zeros(1, 4, 4, 3)
assert t.shape == (1, 4, 4, 3)
assert t.device.type == "cpu"

print("ok")
