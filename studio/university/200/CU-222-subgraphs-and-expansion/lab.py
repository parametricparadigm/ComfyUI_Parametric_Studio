# CU-222 lab: flatten a front-end sub-graph into a prompt, then run a node that expands into new nodes at execution time.
# Run: python lab.py  (standard library only, under a second).
import json
# 1. A workflow with one sub-graph instance (node 5) whose definition holds two inner nodes. Same shape as the "definitions.subgraphs" block in a saved workflow, reduced to what matters here.
workflow = {"nodes": [{"id": 1, "type": "Loader", "widgets": {"name": "m"}},
                      {"id": 5, "type": "sub-abc", "inputs_from": {"model": [1, 0]}},
                      {"id": 7, "type": "Save", "inputs_from": {"latent": [5, 0]}}],
            "definitions": {"subgraphs": [{"id": "sub-abc", "name": "Two pass", "inputs": ["model"], "outputs": [[3, 0]],
                                           "nodes": [{"id": 2, "type": "Sample", "widgets": {"steps": 20}, "inputs_from": {"model": ["input", "model"]}},
                                                     {"id": 3, "type": "Sample", "widgets": {"steps": 8}, "inputs_from": {"model": ["input", "model"], "latent": [2, 0]}}]}]}}
def flatten(wf):
    """Turn the visual hierarchy into a flat API prompt. The inner node ids become compound, parent:child."""
    defs = {d["id"]: d for d in wf["definitions"]["subgraphs"]}; prompt = {}; outs = {}
    for n in wf["nodes"]:
        if n["type"] in defs:
            d = defs[n["type"]]; p = str(n["id"]); outs[p] = [f"{p}:{o[0]}" for o in d["outputs"]]
    def res(ref, parent, ins):
        if ref[0] == "input": return ins[ref[1]]
        if parent: return [f"{parent}:{ref[0]}", ref[1]]
        if str(ref[0]) in outs: return [outs[str(ref[0])][ref[1]], 0]
        return [str(ref[0]), ref[1]]
    for n in wf["nodes"]:
        ins = {k: res(v, None, {}) for k, v in n.get("inputs_from", {}).items()}
        if n["type"] in defs:
            for m in defs[n["type"]]["nodes"]:
                prompt[f"{n['id']}:{m['id']}"] = {"class_type": m["type"], "inputs": {**m.get("widgets", {}), **{k: res(v, str(n["id"]), ins) for k, v in m.get("inputs_from", {}).items()}}}
        else: prompt[str(n["id"])] = {"class_type": n["type"], "inputs": {**n.get("widgets", {}), **ins}}
    return prompt
p = flatten(workflow); print("what the server receives:"); print(json.dumps(p, indent=None))
assert "5" not in p and "5:2" in p and p["7"]["inputs"]["latent"] == ["5:3", 0] and p["5:3"]["inputs"]["model"] == ["1", 0]
print("the server sees", len(p), "nodes and no sub-graph node at all")

# 2. Expansion. A node returns {"result": ..., "expand": graph}: new nodes appear while the prompt runs. This is how a loop can be written.
RAN = []
class GraphBuilder:
    def __init__(self, prefix): self.prefix, self.nodes, self.n = prefix, {}, 0
    def node(self, cls, **inputs): self.n += 1; i = f"{self.prefix}.{self.n}"; self.nodes[i] = {"class_type": cls, "inputs": inputs}; return i
    def finalize(self): return self.nodes
def AddOne(x): RAN.append("AddOne"); return x + 1
def Const(v): RAN.append("Const"); return v
def Repeat(_id, x, times):
    """Expands into a chain of `times` AddOne nodes, and says the last output is its own result."""
    g = GraphBuilder(_id); last = x
    for _ in range(times): last = [g.node("AddOne", x=last), 0]
    return {"result": (last,), "expand": g.finalize()}
FN = {"AddOne": AddOne, "Const": Const, "Repeat": Repeat}
def run(prompt, want):
    dyn = dict(prompt); results = {}; parents = {}
    def ev(i):
        if i in results: return results[i]
        n = dyn[i]; args = {k: ev(v[0]) if isinstance(v, list) else v for k, v in n["inputs"].items()}
        out = FN[n["class_type"]](_id=i, **args) if n["class_type"] == "Repeat" else FN[n["class_type"]](**args)
        if isinstance(out, dict) and "expand" in out:
            dyn.update(out["expand"]); parents.update({k: i for k in out["expand"]}); link = out["result"][0]
            results[i] = ev(link[0]) if isinstance(link, list) else link
        else: results[i] = out
        return results[i]
    return ev(want), dyn, parents
val, dyn, par = run({"a": {"class_type": "Const", "inputs": {"v": 10}}, "r": {"class_type": "Repeat", "inputs": {"x": ["a", 0], "times": 3}}}, "r")
print("\nexpansion: result", val, " nodes after running:", sorted(dyn), " parents:", par); print("functions that ran:", RAN)
assert val == 13 and len(dyn) == 5 and RAN.count("AddOne") == 3
val2, dyn2, _ = run({"a": {"class_type": "Const", "inputs": {"v": 0}}, "r": {"class_type": "Repeat", "inputs": {"x": ["a", 0], "times": 50}}}, "r"); print("the same node with times=50: result", val2, ", graph grew to", len(dyn2), "nodes"); assert val2 == 50
