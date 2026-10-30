"""Tests for h_create_a_per_model_family_validati.py"""

import json
import sys

import torch

from h_create_a_per_model_family_validati import (
    PSN_FamilyWorkflowValidator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    check_graph,
    spec_of,
    build_live_request,
    validate_family,
)

# --- Test 1: module-level mappings exist and are correct ---
assert "PSN_FamilyWorkflowValidator" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_FamilyWorkflowValidator"] is PSN_FamilyWorkflowValidator
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_FamilyWorkflowValidator"] == "Family Workflow Validator"

# --- Test 2: INPUT_TYPES classmethod returns proper structure ---
it = PSN_FamilyWorkflowValidator.INPUT_TYPES()
assert "required" in it
assert "graph_json" in it["required"]
assert "object_info_json" in it["required"]
assert "family_name" in it["required"]
assert "mode" in it["required"]
assert PSN_FamilyWorkflowValidator.FUNCTION == "run"
assert PSN_FamilyWorkflowValidator.CATEGORY == "ParametricStudio/Validation"
assert PSN_FamilyWorkflowValidator.RETURN_TYPES == ("STRING", "STRING", "BOOLEAN", "STRING")

# --- Test 3: valid graph passes offline validation ---
object_info = {
    "KSampler": {
        "input": {
            "required": {
                "model": ["MODEL", {}],
                "seed": ["INT", {"default": 0, "min": 0, "max": 2**32}],
                "steps": ["INT", {"default": 20, "min": 1}],
            },
            "optional": {
                "cfg": ["FLOAT", {"default": 7.5}],
            },
        }
    },
    "CheckpointLoaderSimple": {
        "input": {
            "required": {
                "ckpt_name": ["COMBO", {"options": ["flux.safetensors"]}],
            },
            "optional": {},
        }
    },
}

valid_graph = {
    "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "flux.safetensors"},
    },
    "2": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "seed": 42,
            "steps": 25,
            "cfg": 7.0,
        },
    },
}

problems = check_graph(valid_graph, object_info)
assert problems == [], "valid graph should have no problems, got: %s" % problems

# --- Test 4: graph with missing required input is flagged ---
bad_graph_missing = {
    "2": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "seed": 42,
            # "steps" is missing
        },
    },
}
problems = check_graph(bad_graph_missing, object_info)
assert len(problems) == 1
assert "missing required input steps" in problems[0]

# --- Test 5: graph with unknown class is flagged ---
bad_graph_unknown = {
    "9": {
        "class_type": "NonExistentNode",
        "inputs": {},
    },
}
problems = check_graph(bad_graph_unknown, object_info)
assert len(problems) == 1
assert "unknown class NonExistentNode" in problems[0]

# --- Test 6: graph with wrong type is flagged ---
bad_graph_type = {
    "2": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "seed": "not_an_int",  # should be INT
            "steps": 25,
        },
    },
}
problems = check_graph(bad_graph_type, object_info)
assert len(problems) == 1
assert "wrong type" in problems[0]

# --- Test 7: spec_of handles various formats ---
t, opts, cfg = spec_of(["INT", {"default": 5, "min": 1, "max": 100}])
assert t == "INT"
assert "default" in opts
assert "min" in opts
assert "max" in opts
assert cfg["default"] == 5

t2, opts2, cfg2 = spec_of("STRING")
assert t2 == "STRING"
assert opts2 == []
assert cfg2 == {}

t3, opts3, cfg3 = spec_of([])
assert t3 == ""
assert opts3 == []
assert cfg3 == {}

# --- Test 8: build_live_request returns correct URLs ---
urls = build_live_request(8188, ["KSampler", "CheckpointLoaderSimple"])
assert urls[0] == "http://127.0.0.1:8188/object_info"
assert "http://127.0.0.1:8188/object_info/KSampler" in urls
assert "http://127.0.0.1:8188/object_info/CheckpointLoaderSimple" in urls
assert len(urls) == 3

# --- Test 9: build_live_request rejects bad port ---
try:
    build_live_request(0, ["KSampler"])
    assert False, "should have raised ValueError"
except ValueError:
    pass

try:
    build_live_request(70000, ["KSampler"])
    assert False, "should have raised ValueError"
except ValueError:
    pass

try:
    build_live_request("8188", ["KSampler"])
    assert False, "should have raised TypeError"
except TypeError:
    pass

# --- Test 10: node run with valid inputs ---
node = PSN_FamilyWorkflowValidator()
graph_json = json.dumps(valid_graph)
info_json = json.dumps(object_info)
problems_str, summary_str, valid, urls_str = node.run(graph_json, info_json, "FLUX", "offline")
assert valid is True
assert problems_str == ""
summary = json.loads(summary_str)
assert summary["family"] == "FLUX"
assert summary["graphs_checked"] == 1
assert summary["graphs_ok"] == 1
assert summary["total_problems"] == 0
assert urls_str == "[]"

# --- Test 11: node run with invalid JSON ---
problems_str, summary_str, valid, urls_str = node.run("not json", info_json, "FLUX", "offline")
assert valid is False
assert "not valid JSON" in problems_str

# --- Test 12: node run with bad graph (not a dict) ---
problems_str, summary_str, valid, urls_str = node.run("[1,2,3]", info_json, "FLUX", "offline")
assert valid is False
assert "graph must be a JSON object" in problems_str

# --- Test 13: node run in live mode returns URLs ---
problems_str, summary_str, valid, urls_str = node.run(graph_json, info_json, "FLUX", "live", port=9999)
assert valid is True
urls = json.loads(urls_str)
assert urls[0] == "http://127.0.0.1:9999/object_info"
assert len(urls) >= 2  # at least the base URL + one class

# --- Test 14: validate_family with multiple graphs ---
graphs = {
    "good": valid_graph,
    "bad": bad_graph_unknown,
}
problems, summary = validate_family(graphs, object_info, "HunyuanVideo")
assert summary["family"] == "HunyuanVideo"
assert summary["graphs_checked"] == 2
assert summary["graphs_ok"] == 1
assert summary["total_problems"] == 1
assert len(problems) == 1
assert "[HunyuanVideo] bad:" in problems[0]

# --- Test 15: check_graph with non-dict inputs ---
problems = check_graph("not a dict", object_info)
assert problems == ["graph is not a dict"]

problems = check_graph(valid_graph, "not a dict")
assert problems == ["object_info is not a dict"]

# --- Test 16: node with unknown input is flagged ---
bad_graph_unknown_input = {
    "2": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "seed": 42,
            "steps": 25,
            "bogus_input": "hello",
        },
    },
}
problems = check_graph(bad_graph_unknown_input, object_info)
assert len(problems) == 1
assert "unknown input bogus_input" in problems[0]

# --- Test 17: empty graph is valid ---
problems = check_graph({}, object_info)
assert problems == []

# --- Test 18: node with missing class_type is flagged ---
bad_graph_no_class = {
    "5": {
        "inputs": {"seed": 42},
    },
}
problems = check_graph(bad_graph_no_class, object_info)
assert len(problems) == 1
assert "missing class_type" in problems[0]

print("ok")
