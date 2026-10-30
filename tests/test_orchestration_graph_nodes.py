import pytest, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn import orchestration as O
from psn.graph import GraphBuilder
from psn.expr import ExprError
from psn_nodes import logic as L

def test_gate_modes():
    assert O.gate(0.8, 0.5)[0] and not O.gate(0.2, 0.5)[0] and O.gate(1, 1, "==")[0] and not O.gate(float("nan"), 0.5)[0] and not O.gate("x", 0.5)[0]
    with pytest.raises(ValueError): O.gate(1, 1, "~")

def test_plan_attempts_deterministic():
    a = O.plan_attempts(3, 100, cfg=4.0, cfg_step=0.5, steps=20, steps_step=2); assert a == O.plan_attempts(3, 100, cfg=4.0, cfg_step=0.5, steps=20, steps_step=2)
    assert [x["cfg"] for x in a] == [4.0, 4.5, 5.0] and [x["steps"] for x in a] == [20, 22, 24] and len({x["seed"] for x in a}) == 3

def test_retry_stops_on_pass_and_keeps_best():
    scores = iter([0.2, 0.6, 0.9]); r = O.retry(lambda att: att["attempt"], lambda res: next(scores), max_tries=3, threshold=0.5); assert r["passed"] and r["best"] == 1 and len(r["history"]) == 2
    r = O.retry(lambda att: att["attempt"], lambda res: [0.1, 0.3, 0.2][res], max_tries=3, threshold=0.9); assert not r["passed"] and r["best"] == 1 and len(r["history"]) == 3

def test_retry_survives_exceptions():
    def boom(att): raise RuntimeError("gpu oom")
    r = O.retry(boom, lambda x: 1.0, max_tries=2); assert not r["passed"] and r["best"] is None and "gpu oom" in r["history"][0]["error"]

def test_route_uses_safe_expressions():
    assert O.route({"w": 1920, "h": 1080}, [("w >= 3840", "4k"), ("w >= 1920", "hd")], "sd") == "hd"
    with pytest.raises(ExprError): O.route({"w": 1}, [("__import__('os')", "x")])

OI = {"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["a.safetensors", "b.safetensors"]]}}, "output": ["MODEL", "CLIP", "VAE"]},
      "CLIPTextEncode": {"input": {"required": {"text": ["STRING", {}], "clip": ["CLIP"]}}, "output": ["CONDITIONING"]},
      "KSampler": {"input": {"required": {"model": ["MODEL"], "positive": ["CONDITIONING"], "steps": ["INT", {}], "cfg": ["FLOAT", {}]}}, "output": ["LATENT"]}}
def test_graph_builder_and_validation():
    g = GraphBuilder(); ck = g.add("CheckpointLoaderSimple", ckpt_name="a.safetensors"); t = g.add("CLIPTextEncode", text="hi", clip=ck.out(1)); s = g.add("KSampler", model=ck, positive=t, steps=20, cfg=7.0)
    assert g.validate(OI) == [] and g.topo_order() == ["1", "2", "3"] and g.to_prompt()["3"]["inputs"]["model"] == ["1", 0]
    bad = GraphBuilder.from_prompt(g.to_prompt()); bad.nodes["3"]["inputs"]["positive"] = ["1", 0]; bad.nodes["2"]["inputs"]["clip"] = ["1", 0]; bad.nodes["1"]["inputs"]["ckpt_name"] = "zzz"; del bad.nodes["3"]["inputs"]["steps"]; bad.nodes["3"]["inputs"]["cfg"] = "x"
    e = " | ".join(bad.validate(OI)); assert "expects CONDITIONING" in e and "expects CLIP" in e and "not one of" in e and "missing required input 'steps'" in e and "FLOAT expected" in e

def test_graph_cycle_and_unknown_class():
    g = GraphBuilder.from_prompt({"1": {"class_type": "KSampler", "inputs": {"model": ["2", 0]}}, "2": {"class_type": "Nope", "inputs": {"x": ["1", 0]}}}); e = " | ".join(g.validate(OI)); assert "cycle" in e and "unknown class" in e

def test_nodes_expression_and_gate_and_branch():
    r = L.PSN_Expression().run("a * 2 + b", a=3, b=1); assert r[0] == 7 and r[2] == 7 and r[4] is True
    with pytest.raises(ExprError): L.PSN_Expression().run("a.__class__", a=1)
    assert L.PSN_QualityGate().run(0.9, 0.5, ">=", "img", "fallback") == (True, "img", "score 0.9 >= 0.5: pass") and L.PSN_QualityGate().run(0.1, 0.5, ">=", "img", "fb")[1] == "fb"
    b = L.PSN_Branch(); assert b.check_lazy_status(True) == ["on_true"] and b.check_lazy_status(False) == ["on_false"] and b.run(True, "x", None) == ("x",)
    p = L.PSN_AttemptPlanner().run(1, 3, 10, 4.0, 0.5, 20, 1); assert p[1] == 4.5 and p[2] == 21

def test_sandbox_node_and_registration():
    r = L.PSN_SandboxScript().run("def run(inputs):\n    return inputs['n'] * 2", '{"n": 21}', 5, 256); assert r[:2] == ("42", True)
    assert L.PSN_SandboxScript().run("import os", "{}", 5, 256)[1] is False and L.PSN_SandboxScript().run("x=1", "{bad", 5, 256)[1] is False
    import importlib.util
    spec = importlib.util.spec_from_file_location("psn_pkg", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__init__.py"), submodule_search_locations=[os.path.dirname(os.path.dirname(os.path.abspath(__file__)))])
    m = importlib.util.module_from_spec(spec); sys.modules["psn_pkg"] = m; spec.loader.exec_module(m); assert {"PSN_Expression", "PSN_SandboxScript", "PSN_Branch", "PSN_QualityGate", "PSN_AttemptPlanner"} <= set(m.NODE_CLASS_MAPPINGS) and all(k.startswith("PSN_") for k in m.NODE_CLASS_MAPPINGS)
    for name, cls in m.NODE_CLASS_MAPPINGS.items(): assert isinstance(cls.INPUT_TYPES(), dict) and len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES) and hasattr(cls, cls.FUNCTION)
