"""Tests for h_implement_a_check_graph_function_t.check_graph and PSN_CheckGraph."""

import json

import torch

from h_implement_a_check_graph_function_t import (
    PSN_CheckGraph,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    check_graph,
    _spec_of,
)


# ---------------------------------------------------------------------------
# fixture: a small object_info with two node classes
# ---------------------------------------------------------------------------

INFO = {
    "KSampler": {
        "input": {
            "required": {
                "model": ["MODEL"],
                "seed": ["INT", {"default": 0, "min": 0, "max": 2**32 - 1}],
                "steps": ["INT", {"default": 20, "min": 1, "max": 100}],
                "cfg": ["FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0}],
            },
            "optional": {
                "negative": ["CONDITIONING"],
            },
        }
    },
    "CLIPTextEncode": {
        "input": {
            "required": {
                "clip": ["CLIP"],
                "text": ["STRING", {"multiline": True, "default": ""}],
            },
            "optional": {},
        }
    },
}


# a valid graph: CLIPTextEncode -> KSampler (via link)
VALID_GRAPH = {
    "nodes": {
        "0": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": [0, 0], "text": "a cat"},
        },
        "1": {
            "class_type": "KSampler",
            "inputs": {
                "model": [0, 1],
                "seed": 42,
                "steps": 20,
                "cfg": 8.0,
            },
        },
    }
}


# ---------------------------------------------------------------------------
# 1) valid graph -> no problems
# ---------------------------------------------------------------------------
probs = check_graph(VALID_GRAPH, INFO)
assert probs == [], f"expected no problems, got {probs}"

# ---------------------------------------------------------------------------
# 2) missing required input -> problem reported
# ---------------------------------------------------------------------------
bad = {
    "nodes": {
        "2": {
            "class_type": "KSampler",
            "inputs": {"model": [0, 1], "seed": 42, "cfg": 8.0},  # missing steps
        }
    }
}
probs = check_graph(bad, INFO)
assert any("steps" in p for p in probs), f"expected missing 'steps' problem, got {probs}"

# ---------------------------------------------------------------------------
# 3) unknown class_type -> problem reported
# ---------------------------------------------------------------------------
bad = {
    "nodes": {
        "9": {"class_type": "NoSuchNode", "inputs": {}}
    }
}
probs = check_graph(bad, INFO)
assert any("NoSuchNode" in p for p in probs), f"expected unknown class problem, got {probs}"

# ---------------------------------------------------------------------------
# 4) out-of-range scalar -> problem reported
# ---------------------------------------------------------------------------
bad = {
    "nodes": {
        "2": {
            "class_type": "KSampler",
            "inputs": {"model": [0, 1], "seed": 42, "steps": 999, "cfg": 8.0},
        }
    }
}
probs = check_graph(bad, INFO)
assert any("steps" in p and ("max" in p or "above" in p) for p in probs), \
    f"expected steps out-of-range problem, got {probs}"

# ---------------------------------------------------------------------------
# 5) wrong type for an input (string where INT expected)
# ---------------------------------------------------------------------------
bad = {
    "nodes": {
        "2": {
            "class_type": "KSampler",
            "inputs": {"model": [0, 1], "seed": "not_a_number", "steps": 20, "cfg": 8.0},
        }
    }
}
probs = check_graph(bad, INFO)
assert any("seed" in p for p in probs), f"expected seed type problem, got {probs}"

# ---------------------------------------------------------------------------
# 6) link to a non-existent node
# ---------------------------------------------------------------------------
bad = {
    "nodes": {
        "2": {
            "class_type": "KSampler",
            "inputs": {"model": [99, 0], "seed": 42, "steps": 20, "cfg": 8.0},
        }
    }
}
probs = check_graph(bad, INFO)
assert any("99" in p for p in probs), f"expected missing-link problem, got {probs}"

# ---------------------------------------------------------------------------
# 7) unknown input name
# ---------------------------------------------------------------------------
bad = {
    "nodes": {
        "2": {
            "class_type": "KSampler",
            "inputs": {"model": [0, 1], "seed": 42, "steps": 20, "cfg": 8.0, "bogus": 1},
        }
    }
}
probs = check_graph(bad, INFO)
assert any("bogus" in p for p in probs), f"expected unknown-input problem, got {probs}"

# ---------------------------------------------------------------------------
# 8) _spec_of helper
# ---------------------------------------------------------------------------
tn, opts, cfg = _spec_of(["INT", {"default": 5, "min": 1, "max": 10}])
assert tn == "INT" and opts == ["INT"] and cfg["min"] == 1 and cfg["max"] == 10

tn2, opts2, cfg2 = _spec_of([["VAE", "CLIP_VAE"], {"default": "VAE"}])
assert tn2 == "VAE,CLIP_VAE" and opts2 == ["VAE", "CLIP_VAE"]

tn3, opts3, cfg3 = _spec_of(["MODEL"])
assert tn3 == "MODEL" and opts3 == ["MODEL"] and cfg3 == {}

# ---------------------------------------------------------------------------
# 9) PSN_CheckGraph node: valid graph
# ---------------------------------------------------------------------------
node = PSN_CheckGraph()
text, is_valid = node.run(json.dumps(VALID_GRAPH), json.dumps(INFO))
assert is_valid is True, f"expected valid, got {text!r}"
assert text == "", f"expected empty text, got {text!r}"

# ---------------------------------------------------------------------------
# 10) PSN_CheckGraph node: invalid graph
# ---------------------------------------------------------------------------
bad_graph = {
    "nodes": {
        "2": {
            "class_type": "KSampler",
            "inputs": {"model": [0, 1], "seed": 42, "steps": 999, "cfg": 8.0},
        }
    }
}
text, is_valid = node.run(json.dumps(bad_graph), json.dumps(INFO))
assert is_valid is False, f"expected invalid, got {text!r}"
assert "steps" in text, f"expected 'steps' in problems, got {text!r}"

# ---------------------------------------------------------------------------
# 11) PSN_CheckGraph node: bad JSON input
# ---------------------------------------------------------------------------
text, is_valid = node.run("not json", json.dumps(INFO))
assert is_valid is False
assert "not valid JSON" in text

text, is_valid = node.run(json.dumps(VALID_GRAPH), "also not json")
assert is_valid is False
assert "not valid JSON" in text

# ---------------------------------------------------------------------------
# 12) module-level mappings exist and are correct
# ---------------------------------------------------------------------------
assert "PSN_CheckGraph" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_CheckGraph"] is PSN_CheckGraph
assert "PSN_CheckGraph" in NODE_DISPLAY_NAME_MAPPINGS

# INPUT_TYPES classmethod
it = PSN_CheckGraph.INPUT_TYPES()
assert "required" in it
assert "graph_json" in it["required"]
assert "object_info_json" in it["required"]

# RETURN_TYPES / RETURN_NAMES / FUNCTION / CATEGORY
assert PSN_CheckGraph.RETURN_TYPES == ("STRING", "BOOLEAN")
assert PSN_CheckGraph.RETURN_NAMES == ("problems", "is_valid")
assert PSN_CheckGraph.FUNCTION == "run"
assert PSN_CheckGraph.CATEGORY == "ParametricStudio/Graph"

# ---------------------------------------------------------------------------
# 13) empty graph / empty info edge cases
# ---------------------------------------------------------------------------
probs = check_graph({"nodes": {}}, INFO)
assert probs == [], f"empty nodes should be valid, got {probs}"

probs = check_graph(VALID_GRAPH, {})
assert len(probs) >= 2, f"expected problems for empty info, got {probs}"

# non-dict graph
probs = check_graph("not a dict", INFO)
assert probs == ["graph must be a dict"]

# non-dict info
probs = check_graph(VALID_GRAPH, "not a dict")
assert probs == ["object_info must be a dict"]

# missing 'nodes' key
probs = check_graph({}, INFO)
assert probs == ["graph['nodes'] must be a dict"]

# ---------------------------------------------------------------------------
# 14) FLOAT input with step check
# ---------------------------------------------------------------------------
INFO_STEP = {
    "MyNode": {
        "input": {
            "required": {
                "val": ["FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.25}],
            },
            "optional": {},
        }
    }
}
bad = {"nodes": {"1": {"class_type": "MyNode", "inputs": {"val": 0.3}}}}
probs = check_graph(bad, INFO_STEP)
assert any("step" in p for p in probs), f"expected step problem, got {probs}"

ok = {"nodes": {"1": {"class_type": "MyNode", "inputs": {"val": 0.5}}}}
probs = check_graph(ok, INFO_STEP)
assert probs == [], f"expected valid, got {probs}"

# ---------------------------------------------------------------------------
# 15) optional input present is fine; absent is fine
# ---------------------------------------------------------------------------
bad = {
    "nodes": {
        "0": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": [0, 0], "text": "hi"},
        },
        "1": {
            "class_type": "KSampler",
            "inputs": {"model": [0, 1], "seed": 42, "steps": 20, "cfg": 8.0, "negative": [0, 0]},
        },
    }
}
probs = check_graph(bad, INFO)
assert probs == [], f"optional input present should be fine, got {probs}"

print("ok")
