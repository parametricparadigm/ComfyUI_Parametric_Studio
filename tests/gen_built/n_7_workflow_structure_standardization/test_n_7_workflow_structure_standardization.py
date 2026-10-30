"""Tests for n_7_workflow_structure_standardization (plain asserts, no pytest)."""

import json

from n_7_workflow_structure_standardization import (
    PSN_Graph_Standardizer,
    PSN_Node_Inspector,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _classify,
)


def _graph():
    return json.dumps({
        "prompt": {
            "1": {"class_type": "LoadImage", "inputs": {}},
            "2": {"class_type": "KSampler", "inputs": {"model": ["3", 0, 0]}},
            "3": {"class_type": "CheckpointLoaderSimple", "inputs": {}},
            "4": {"class_type": "VAEDecode", "inputs": {"samples": ["2", 0, 0]}},
        }
    })


def test_module_mappings():
    assert "PSN_Graph_Standardizer" in NODE_CLASS_MAPPINGS
    assert "PSN_Node_Inspector" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Graph_Standardizer"] == "PSN Graph Standardizer"
    for cls in (PSN_Graph_Standardizer, PSN_Node_Inspector):
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES) == 2
        it = cls.INPUT_TYPES()
        assert "graph_json" in it["required"]


def test_classify():
    assert _classify("LoadImage") == "LDR"
    assert _classify("KSampler") == "SMP"
    assert _classify("CheckpointLoaderSimple") == "LDR"
    assert _classify("VAEDecode") == "CTL"
    assert _classify("") == "CTL"


def test_standardizer_renames_and_report():
    node = PSN_Graph_Standardizer()
    std, report = node.run(_graph())
    data = json.loads(std)
    prompt = data["prompt"]
    assert set(prompt) == {"1", "2", "3", "4"}
    assert prompt["1"]["title"].startswith("LDR_")
    assert prompt["2"]["title"].startswith("SMP_")
    assert prompt["3"]["title"].startswith("LDR_")
    assert prompt["4"]["title"].startswith("CTL_")
    # links preserved
    assert prompt["2"]["inputs"]["model"] == ["3", 0, 0]
    assert "nodes: 4" in report
    assert "acyclic: yes" in report
    assert "dangling inputs: none" in report


def test_standardizer_bad_json():
    node = PSN_Graph_Standardizer()
    std, report = node.run("{not json")
    assert report.startswith("FAILED:")
    assert "invalid JSON" in report


def test_standardizer_dangling_and_cycle():
    g = json.dumps({
        "prompt": {
            "a": {"class_type": "LoadImage", "inputs": {"x": ["ghost", 0, 0]}},
            "b": {"class_type": "KSampler", "inputs": {"y": ["c", 0, 0]}},
            "c": {"class_type": "VAEDecode", "inputs": {"z": ["b", 0, 0]}},
        }
    })
    node = PSN_Graph_Standardizer()
    std, report = node.run(g)
    assert "dangling inputs" in report and "ghost" in report
    assert "CYCLE detected" in report
    data = json.loads(std)
    assert set(data["prompt"]) == {"a", "b", "c"}


def test_inspector_tree_and_dot():
    node = PSN_Node_Inspector()
    tree, dot = node.run(_graph())
    assert "LoadImage" in tree
    assert "KSampler" in tree
    assert "VAEDecode" in tree
    assert dot.startswith("digraph G {")
    assert '"3" -> "2";' in dot
    assert '"2" -> "4";' in dot
    assert dot.rstrip().endswith("}")


def test_inspector_empty_and_bad():
    node = PSN_Node_Inspector()
    tree, dot = node.run("{\"prompt\": {}}")
    assert "empty graph" in tree
    assert dot == "digraph G { }\n"
    tree2, dot2 = node.run("nope")
    assert "invalid JSON" in tree2
    assert dot2 == "digraph G { }\n"


def test_no_in_place_mutation():
    raw = _graph()
    node = PSN_Graph_Standardizer()
    node.run(raw)
    # input string unchanged (strings are immutable, but ensure we did not
    # return the same object mutated)
    assert raw == _graph()
    data = json.loads(raw)
    assert "title" not in data["prompt"]["1"]


if __name__ == "__main__":
    test_module_mappings()
    test_classify()
    test_standardizer_renames_and_report()
    test_standardizer_bad_json()
    test_standardizer_dangling_and_cycle()
    test_inspector_tree_and_dot()
    test_inspector_empty_and_bad()
    test_no_in_place_mutation()
    print("ok")
