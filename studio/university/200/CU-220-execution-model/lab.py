# CU-220 lab: a small copy of ComfyUI's scheduler. Same ideas as comfy_execution/graph.py: walk back from outputs, count blockers, dissolve.
# Run: python lab.py  (standard library only, under a second).
LOG = []
class Node:
    OUTPUT = False; LAZY = (); TYPES = {}
    def run(self, **k): raise NotImplementedError
    def lazy(self, **k): return []
class Load(Node):
    RET = "MODEL"
    def run(self, name): LOG.append("Load"); return f"model<{name}>"
class Text(Node):
    RET = "COND"; TYPES = {"model": "MODEL"}
    def run(self, model, text): LOG.append(f"Text<{text}>"); return f"cond<{text}>"
class Sample(Node):
    RET = "LATENT"; TYPES = {"model": "MODEL", "cond": "COND"}
    def run(self, model, cond, seed): LOG.append("Sample"); return f"latent<{cond},{seed}>"
class Switch(Node):                                   # a node with lazy inputs: only asks for the branch it needs
    RET = "LATENT"; LAZY = ("a", "b"); TYPES = {"a": "LATENT", "b": "LATENT"}
    def lazy(self, use_a, a=None, b=None): return (["a"] if a is None else []) if use_a else (["b"] if b is None else [])
    def run(self, use_a, a=None, b=None): LOG.append("Switch"); return a if use_a else b
class Save(Node):
    OUTPUT = True; RET = None; TYPES = {"latent": "LATENT"}
    def run(self, latent): LOG.append("Save"); return None
CLASSES = dict(Load=Load, Text=Text, Sample=Sample, Switch=Switch, Save=Save)
def is_link(v): return isinstance(v, list) and len(v) == 2

def validate(prompt):
    """The checks of validate_prompt: known classes, at least one output, types match along links, no cycles. Nodes no output needs are never looked at."""
    for i, n in prompt.items():
        if n["class_type"] not in CLASSES: return f"missing_node_type: {n['class_type']}"
    outs = [i for i, n in prompt.items() if CLASSES[n["class_type"]].OUTPUT]
    if not outs: return "prompt_no_outputs"
    seen = {}
    def visit(i, stack):
        if i in stack: return "dependency_cycle: " + " -> ".join(stack + [i])
        if i in seen: return None
        seen[i] = 1
        for k, v in prompt[i]["inputs"].items():
            if is_link(v):
                want = CLASSES[prompt[i]["class_type"]].TYPES.get(k); got = CLASSES[prompt[v[0]]["class_type"]].RET
                if want != got: return f"return_type_mismatch: node {i} input {k} wants {want}, got {got}"
                e = visit(v[0], stack + [i])
                if e: return e
    for o in outs:
        e = visit(o, [])
        if e: return e
    return None

def execute(prompt):
    """A topological dissolve, re-entrant for lazy inputs, as in ExecutionList."""
    results = {}; pending = {}; blocking = {}; count = {}; order = []
    def strong(a, b):
        if a in results: return
        add(a)
        if b not in blocking[a]: blocking[a].add(b); count[b] += 1
    def add(i):
        if i in pending or i in results: return
        pending[i] = True; count[i] = 0; blocking[i] = set(); cls = CLASSES[prompt[i]["class_type"]]
        for k, v in prompt[i]["inputs"].items():
            if is_link(v) and k not in cls.LAZY: strong(v[0], i)      # lazy inputs make no link yet
    for i, n in prompt.items():
        if CLASSES[n["class_type"]].OUTPUT: add(i)
    def pick(ready):                                                 # ux_friendly_pick_node: outputs first, then what feeds an output
        is_out = lambda i: CLASSES[prompt[i]["class_type"]].OUTPUT
        for i in ready:
            if is_out(i): return i
        for i in ready:
            if any(is_out(b) for b in blocking[i]): return i
        for i in ready:
            if any(is_out(c) for b in blocking[i] for c in blocking[b]): return i
        return ready[0]
    while pending:
        ready = [i for i in pending if count[i] == 0]
        if not ready: raise RuntimeError("cycle")
        i = pick(ready); cls = CLASSES[prompt[i]["class_type"]]; obj = cls()
        args = {k: (results[v[0]] if v[0] in results else None) if is_link(v) else v for k, v in prompt[i]["inputs"].items()}
        need = [k for k in obj.lazy(**args) if is_link(prompt[i]["inputs"].get(k))]
        if need:                                                     # back into the pending list, with new blockers (ExecutionResult.PENDING)
            order.append(f"{i}?"); [strong(prompt[i]["inputs"][k][0], i) for k in need]; continue
        results[i] = obj.run(**args); order.append(i); del pending[i]
        for b in blocking[i]: count[b] -= 1
    return order, results

base = {"1": {"class_type": "Load", "inputs": {"name": "m.safetensors"}},
        "2": {"class_type": "Text", "inputs": {"model": ["1", 0], "text": "a fox"}},
        "3": {"class_type": "Sample", "inputs": {"model": ["1", 0], "cond": ["2", 0], "seed": 7}},
        "4": {"class_type": "Save", "inputs": {"latent": ["3", 0]}},
        "9": {"class_type": "Text", "inputs": {"model": ["1", 0], "text": "nobody asked for me"}}}
print("validation:", validate(base))
order, _ = execute(base); print("order:", order, " ran:", LOG)
assert order == ["1", "2", "3", "4"] and "9" not in order and not any("nobody" in x for x in LOG)
print("\nwhy an orphan does not run: execution starts from output nodes, and node 9 feeds nothing")

print("no output node:", validate({"1": base["1"]}))
print("wrong type on a link:", validate({**base, "4": {"class_type": "Save", "inputs": {"latent": ["2", 0]}}}))
print("cycle:", validate({"1": {"class_type": "Switch", "inputs": {"use_a": True, "a": ["2", 0]}}, "2": {"class_type": "Switch", "inputs": {"use_a": True, "a": ["1", 0]}}, "4": {"class_type": "Save", "inputs": {"latent": ["1", 0]}}}))
print("unknown class:", validate({"1": {"class_type": "Nope", "inputs": {}}}))
assert validate({"1": base["1"]}) == "prompt_no_outputs"

# Lazy: two expensive branches, only one is wanted.
lazy = {**{k: base[k] for k in "12"}, "3": base["3"], "5": {"class_type": "Text", "inputs": {"model": ["1", 0], "text": "other"}},
        "6": {"class_type": "Sample", "inputs": {"model": ["1", 0], "cond": ["5", 0], "seed": 8}},
        "7": {"class_type": "Switch", "inputs": {"use_a": True, "a": ["3", 0], "b": ["6", 0]}},
        "8": {"class_type": "Save", "inputs": {"latent": ["7", 0]}}}
LOG.clear(); order, res = execute(lazy); print("\nlazy switch, use_a=True  order:", order); print("ran:", LOG)
assert "6" not in order and "5" not in order and "7?" in order and LOG.count("Sample") == 1
lazy["7"]["inputs"]["use_a"] = False; LOG.clear(); order, res = execute(lazy); print("lazy switch, use_a=False order:", order)
assert "3" not in order and "6" in order
# Without laziness, both branches would run:
eager = {k: dict(v) for k, v in lazy.items()}; CLASSES["Switch"].LAZY = (); LOG.clear(); order, _ = execute(eager); print("the same graph without lazy inputs:", order, f"({LOG.count('Sample')} sampler runs)")
assert LOG.count("Sample") == 2
