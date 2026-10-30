"""Programmatic ComfyUI graph builder (original design). Builds API-format prompts ({id: {class_type, inputs}}) from code or from an LLM plan, and validates them against a server's /object_info
BEFORE anything is queued: unknown nodes, missing required inputs, bad link targets, type mismatches, combo values, cycles."""
import json

class Ref:
    def __init__(self, node_id, index=0): self.node_id, self.index = str(node_id), int(index)
    def link(self): return [self.node_id, self.index]
    def __repr__(self): return f"Ref({self.node_id},{self.index})"

class GraphBuilder:
    def __init__(self): self.nodes = {}; self._n = 0
    def add(self, class_type, **inputs):
        """Add a node; any input that is a Ref becomes a link. Returns a Ref to output 0 (use .out(i) for others)."""
        self._n += 1; nid = str(self._n); self.nodes[nid] = {"class_type": class_type, "inputs": {k: (v.link() if isinstance(v, Ref) else v) for k, v in inputs.items()}}
        r = Ref(nid, 0); r.out = lambda i, _id=nid: Ref(_id, i); return r
    def to_prompt(self): return json.loads(json.dumps(self.nodes))
    def to_json(self, **kw): return json.dumps(self.nodes, **kw)
    @classmethod
    def from_prompt(cls, prompt):
        g = cls(); g.nodes = json.loads(json.dumps(prompt)); g._n = max([int(k) for k in g.nodes if str(k).isdigit()] or [0]); return g
    def topo_order(self):
        """Node ids in execution order; raises ValueError on a cycle."""
        deps = {k: {v[0] for v in n["inputs"].values() if isinstance(v, list) and len(v) == 2 and str(v[0]) in self.nodes} for k, n in self.nodes.items()}
        out, state = [], {}
        def visit(k):
            if state.get(k) == 1: raise ValueError(f"cycle through node {k}")
            if state.get(k) == 2: return
            state[k] = 1
            for d in sorted(deps[k]): visit(str(d))
            state[k] = 2; out.append(k)
        for k in sorted(self.nodes, key=lambda x: int(x) if str(x).isdigit() else 0): visit(k)
        return out
    def validate(self, object_info):
        """-> list of human-readable problems (empty = OK)."""
        errs = []
        try: self.topo_order()
        except ValueError as e: errs.append(str(e))
        for nid, n in self.nodes.items():
            info = object_info.get(n["class_type"])
            if not info: errs.append(f"node {nid}: unknown class '{n['class_type']}'"); continue
            req, opt = info.get("input", {}).get("required", {}), info.get("input", {}).get("optional", {})
            for name in req:
                if name not in n["inputs"]: errs.append(f"node {nid} ({n['class_type']}): missing required input '{name}'")
            for name, val in n["inputs"].items():
                spec = req.get(name) or opt.get(name)
                if spec is None: errs.append(f"node {nid} ({n['class_type']}): unknown input '{name}'"); continue
                want = spec[0]
                if isinstance(val, list) and len(val) == 2 and str(val[0]) in self.nodes:
                    src = self.nodes[str(val[0])]; sinfo = object_info.get(src["class_type"])
                    if not sinfo: continue
                    outs = sinfo.get("output", [])
                    if not (0 <= val[1] < len(outs)): errs.append(f"node {nid}.{name}: node {val[0]} has no output {val[1]}"); continue
                    got = outs[val[1]]
                    if isinstance(want, str) and want != "*" and got != "*" and got not in want.split(","): errs.append(f"node {nid}.{name}: expects {want}, node {val[0]} output {val[1]} is {got}")
                elif isinstance(want, list):
                    if val not in want: errs.append(f"node {nid}.{name}: '{val}' is not one of the {len(want)} allowed values")
                elif want in ("INT", "FLOAT"):
                    if isinstance(val, bool) or not isinstance(val, (int, float)): errs.append(f"node {nid}.{name}: {want} expected")
                    elif want == "INT" and isinstance(val, float) and val != int(val): errs.append(f"node {nid}.{name}: INT expected")
                elif want == "STRING" and not isinstance(val, str): errs.append(f"node {nid}.{name}: STRING expected")
                elif want == "BOOLEAN" and not isinstance(val, bool): errs.append(f"node {nid}.{name}: BOOLEAN expected")
        return errs
