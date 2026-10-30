"""Tests for h_use_a_read_only_fetch_info_pattern."""

import json
import sys

sys.path.insert(0, ".")

from h_use_a_read_only_fetch_info_pattern import (
    PSN_FetchInfoIntrospect,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _spec_of,
    _check_graph,
)

# --- 1. Module-level mappings exist and are consistent ---
assert "PSN_FetchInfoIntrospect" in NODE_CLASS_MAPPINGS, "node missing from mappings"
assert "PSN_FetchInfoIntrospect" in NODE_DISPLAY_NAME_MAPPINGS, "display name missing"
assert NODE_CLASS_MAPPINGS["PSN_FetchInfoIntrospect"] is PSN_FetchInfoIntrospect

# --- 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY ---
it = PSN_FetchInfoIntrospect.INPUT_TYPES()
assert "required" in it and "optional" in it
assert "object_info_json" in it["required"]
assert "classes" in it["required"]
assert PSN_FetchInfoIntrospect.RETURN_TYPES == ("STRING", "STRING")
assert PSN_FetchInfoIntrospect.RETURN_NAMES == ("report_json", "problems")
assert PSN_FetchInfoIntrospect.FUNCTION == "run"
assert PSN_FetchInfoIntrospect.CATEGORY.startswith("ParametricStudio/")

# --- 3. _spec_of extracts type, options, config correctly ---
t, opts, cfg = _spec_of(["FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}])
assert t == "FLOAT"
assert opts == ["default", "max", "min"]
assert cfg["default"] == 1.0

t2, opts2, cfg2 = _spec_of(["INT"])
assert t2 == "INT" and opts2 == [] and cfg2 == {}

t3, _, _ = _spec_of(["CLIP", "CONDITIONING"])
assert t3 == "CLIP,CONDITIONING"

# --- 4. _check_graph finds missing class and unknown input ---
info = {
    "KSampler": {
        "input": {
            "required": {
                "seed": ["INT", {"default": 0}],
                "steps": ["INT", {"default": 20}],
            },
            "optional": {"cfg": ["FLOAT", {"default": 7.0}]},
        }
    }
}
graph_ok = {"1": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 20}}}
assert _check_graph(graph_ok, info) == [], "clean graph should have no problems"

graph_bad = {"1": {"class_type": "KSampler", "inputs": {"seed": 42, "bogus": 1}}}
probs = _check_graph(graph_bad, info)
assert len(probs) == 1 and "bogus" in probs[0], "should flag unknown input"

graph_missing = {"2": {"class_type": "NonExistent", "inputs": {}}}
probs2 = _check_graph(graph_missing, info)
assert len(probs2) == 1 and "NonExistent" in probs2[0], "should flag missing class"

# --- 5. Node run: happy path with valid object_info and classes ---
node = PSN_FetchInfoIntrospect()
info_payload = json.dumps(info)
report_json, problems = node.run(info_payload, "KSampler")
report = json.loads(report_json)
assert "KSampler" in report
assert report["KSampler"]["found"] is True
assert "seed" in report["KSampler"]["inputs"]
assert report["KSampler"]["inputs"]["seed"]["type"] == "INT"
assert report["KSampler"]["inputs"]["seed"]["section"] == "required"
assert report["KSampler"]["inputs"]["cfg"]["section"] == "optional"
assert problems == ""

# --- 6. Node run: class not found in object_info ---
report_json2, _ = node.run(info_payload, "KSampler,MissingClass")
report2 = json.loads(report_json2)
assert report2["MissingClass"]["found"] is False

# --- 7. Node run: bad JSON raises ValueError ---
try:
    node.run("not valid json {{{", "KSampler")
    assert False, "should have raised ValueError"
except ValueError:
    pass

# --- 8. Node run: graph check integration ---
graph_str = json.dumps(graph_bad)
report_json3, problems3 = node.run(info_payload, "KSampler", graph_json=graph_str)
assert "bogus" in problems3, "graph problems should be surfaced"

# --- 9. Input payload is never mutated (read-only guarantee) ---
original = json.dumps(info)
node.run(original, "KSampler")
assert json.dumps(info) == original, "input dict must not be mutated"

# --- 10. Empty classes string produces empty report ---
report_json4, problems4 = node.run(info_payload, "")
report4 = json.loads(report_json4)
assert report4 == {}
assert problems4 == ""

print("ok")
