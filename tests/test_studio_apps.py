import json, os, pytest
from studio import apps as A

OI = {"CLIPTextEncode": {"input": {"required": {"text": ["STRING", {}], "clip": ["CLIP", {}]}}}, "KSampler": {"input": {"required": {"seed": ["INT", {"control_after_generate": True}], "steps": ["INT", {}], "model": ["MODEL", {}]}}},
      "LoadImage": {"input": {"required": {"image": [["a.png"], {}]}}}, "SaveImage": {"output_node": True, "input": {"required": {"images": ["IMAGE", {}]}}}}
APP = {"extra": {"linearMode": True, "linearData": {"inputs": [["1", "text"], ["2", "seed"], ["3", "image"]], "outputs": ["4"]}},
       "nodes": [{"id": 1, "type": "CLIPTextEncode", "title": "Prompt", "widgets_values": ["a fox"], "inputs": []}, {"id": 2, "type": "KSampler", "widgets_values": [5, "fixed", 20], "inputs": [{"name": "model", "link": 2}]},
                 {"id": 3, "type": "LoadImage", "widgets_values": ["a.png"], "inputs": []}, {"id": 4, "type": "SaveImage", "widgets_values": [], "inputs": [{"name": "images", "link": 1}]}], "links": [[1, 2, 0, 4, 0, "IMAGE"], [2, 1, 0, 2, 0, "CLIP"]]}

def test_is_app_and_describe(tmp_path):
    p = tmp_path / "demo.app.json"; p.write_text(json.dumps(APP)); assert A._is_app(APP) and not A._is_app({"extra": {}})
    d = A.describe("demo", str(p), OI); kinds = {i["key"]: i["type"] for i in d["inputs"]}
    assert kinds == {"1|text": "text", "2|seed": "number"} and d["runnable"] and d["outputs"] == 1   # the unused LoadImage feeds nothing, so it is not offered

def test_build_graph_sets_values_and_rejects_unknown(tmp_path):
    p = tmp_path / "demo.app.json"; p.write_text(json.dumps(APP))
    g = A.build_graph(str(p), {"1|text": "a cat", "2|seed": 9}, OI); assert g["1"]["inputs"]["text"] == "a cat" and g["2"]["inputs"]["seed"] == 9
    with pytest.raises(ValueError): A.build_graph(str(p), {"9|zzz": 1}, OI)

def test_find_apps_in_a_folder(tmp_path, monkeypatch):
    d = tmp_path / "comfy_apps"; d.mkdir(); (d / "x.app.json").write_text(json.dumps(APP)); (d / "plain.app.json").write_text(json.dumps({"extra": {}}))
    monkeypatch.setattr(A, "object_info", lambda: {}); monkeypatch.setenv("STUDIO_APPS", str(d)); assert set(A.find_apps()) >= {"x"} and "plain" not in A.find_apps()

def test_model_hints_and_pack_resolution_and_fetch_needs_confirm(tmp_path):
    ui = dict(APP); ui["nodes"] = [dict(n) for n in APP["nodes"]]; ui["nodes"][0]["properties"] = {"models": [{"name": "m.safetensors", "url": "https://huggingface.co/o/r/resolve/main/m.safetensors", "directory": "loras"}, {"name": "x", "url": "http://evil.example/x", "directory": "z"}]}
    assert A.model_hints(ui) == {"m.safetensors": {"url": "https://huggingface.co/o/r/resolve/main/m.safetensors", "directory": "loras"}}
    reg = {"https://github.com/a/pack": [["NodeA", "NodeB"], {}], "https://github.com/b/other": [["NodeC"], {}]}
    assert A.resolve_packs(["NodeB", "Nope"], registry=reg) == {"NodeB": "https://github.com/a/pack", "Nope": None}
    p = tmp_path / "demo.app.json"; p.write_text(json.dumps(APP))
    with pytest.raises(ValueError): A.fetch_models("demo", str(p), OI, confirm=False)
