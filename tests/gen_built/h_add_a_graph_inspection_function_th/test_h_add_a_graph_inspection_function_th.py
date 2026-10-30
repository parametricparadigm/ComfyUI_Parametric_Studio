"""Tests for h_add_a_graph_inspection_function_th (graph NSFW guard)."""

import json

import h_add_a_graph_inspection_function_th as mod


def _graph(loras):
    """Build a minimal ComfyUI-style graph with the given LoRA names."""
    graph = {
        "3": {"class_type": "KSampler", "inputs": {"seed": 1}},
    }
    for i, name in enumerate(loras):
        graph[str(10 + i)] = {
            "class_type": "LoraLoader",
            "inputs": {"lora_name": name, "strength_model": 1.0},
        }
    return graph


def test_clean_graph_passes():
    report = mod.check_graph(_graph(["style_lora.safetensors", "anime_v2.safetensors"]))
    assert report["checked"] == 2
    assert report["blocked"] == []
    assert len(report["loras"]) == 2


def test_nsfw_lora_raises():
    try:
        mod.check_graph(_graph(["totally_sfw.safetensors", "nsfw_explicit.safetensors"]))
    except ValueError as exc:
        assert "nsfw_explicit.safetensors" in str(exc)
    else:
        raise AssertionError("expected ValueError for NSFW LoRA")


def test_case_insensitive_matching():
    try:
        mod.check_graph(_graph(["MyNSFW_Lora.safetensors"]))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for case-insensitive NSFW match")


def test_custom_markers():
    # With a custom marker list, the default NSFW markers are ignored.
    report = mod.check_graph(_graph(["nsfw_explicit.safetensors"]), markers=["forbidden"])
    assert report["checked"] == 1
    assert report["blocked"] == []
    try:
        mod.check_graph(_graph(["forbidden_lora.safetensors"]), markers=["forbidden"])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for custom marker match")


def test_non_lora_nodes_ignored():
    graph = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a cat"}},
    }
    report = mod.check_graph(graph)
    assert report["checked"] == 0
    assert report["loras"] == []


def test_malformed_graph_entries_skipped():
    graph = {
        "1": "not-a-dict",
        "2": {"class_type": "LoraLoader"},  # missing inputs
        "3": {"class_type": "LoraLoader", "inputs": "not-a-dict"},
        "4": {"class_type": "LoraLoader", "inputs": {}},  # no name key
        "5": {"class_type": "LoraLoader", "inputs": {"lora_name": "ok_lora.safetensors"}},
    }
    report = mod.check_graph(graph)
    assert report["checked"] == 1
    assert report["loras"] == [("5", "ok_lora.safetensors")]


def test_node_run_clean():
    node = mod.PSN_GraphNSFWGuard()
    graph_json = json.dumps(_graph(["style_lora.safetensors"]))
    report, count = node.run(graph_json)
    assert count == 1
    assert "NSFW guard: OK" in report
    assert "style_lora.safetensors" in report


def test_node_run_nsfw_raises():
    node = mod.PSN_GraphNSFWGuard()
    graph_json = json.dumps(_graph(["nude_model.safetensors"]))
    try:
        node.run(graph_json)
    except ValueError as exc:
        assert "nude_model.safetensors" in str(exc)
    else:
        raise AssertionError("expected ValueError from node.run")


def test_node_run_invalid_json():
    node = mod.PSN_GraphNSFWGuard()
    try:
        node.run("this is not json")
    except ValueError as exc:
        assert "invalid JSON" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid JSON")


def test_node_run_empty_graph():
    node = mod.PSN_GraphNSFWGuard()
    report, count = node.run("{}")
    assert count == 0
    assert "NSFW guard: OK" in report


def test_module_mappings():
    assert "PSN_GraphNSFWGuard" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_GraphNSFWGuard" in mod.NODE_DISPLAY_NAME_MAPPINGS
    cls = mod.NODE_CLASS_MAPPINGS["PSN_GraphNSFWGuard"]
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY == "ParametricStudio/Safety"
    assert cls.RETURN_TYPES == ("STRING", "INT")
    assert cls.RETURN_NAMES == ("report", "lora_count")
    it = cls.INPUT_TYPES()
    assert "graph_json" in it["required"]
    assert "nsfw_markers" in it["optional"]


def test_non_dict_graph():
    # check_graph must not crash on a non-dict graph.
    report = mod.check_graph([1, 2, 3])
    assert report["checked"] == 0


if __name__ == "__main__":
    test_clean_graph_passes()
    test_nsfw_lora_raises()
    test_case_insensitive_matching()
    test_custom_markers()
    test_non_lora_nodes_ignored()
    test_malformed_graph_entries_skipped()
    test_node_run_clean()
    test_node_run_nsfw_raises()
    test_node_run_invalid_json()
    test_node_run_empty_graph()
    test_module_mappings()
    test_non_dict_graph()
    print("ok")
