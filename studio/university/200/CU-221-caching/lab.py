# CU-221 lab: ComfyUI's cache keys and cache policies on a small graph. The signature follows CacheKeySetInputSignature.
# Run: python lab.py  (standard library only, under a second).
RUNS = []
CLASSES = {"Load": dict(), "Text": dict(), "Empty": dict(), "Sample": dict(), "Decode": dict(), "Save": dict(), "LoadFile": dict(is_changed=True), "Noise": dict(not_idempotent=True)}
def is_link(v): return isinstance(v, list) and len(v) == 2
def ancestry(p, i, order, map_):
    for k in sorted(p[i]["inputs"]):
        v = p[i]["inputs"][k]
        if is_link(v) and v[0] not in map_: map_[v[0]] = len(order); order.append(v[0]); ancestry(p, v[0], order, map_)
FILE_CONTENT = {"v": "hash-A"}
def immediate(p, i, map_):
    c = p[i]["class_type"]; sig = [c, FILE_CONTENT["v"] if CLASSES[c].get("is_changed") else False]
    if CLASSES[c].get("not_idempotent"): sig.append(i)               # NOT_IDEMPOTENT nodes add their own id, so copies do not share a result
    for k in sorted(p[i]["inputs"]):
        v = p[i]["inputs"][k]; sig.append((k, ("ANCESTOR", map_[v[0]], v[1])) if is_link(v) else (k, v))
    return tuple(sig)
def signature(p, i):
    order, map_ = [], {}; ancestry(p, i, order, map_); return tuple([immediate(p, i, map_)] + [immediate(p, a, map_) for a in order])
class Cache:
    """classic: at each prompt drop every key the new prompt does not use. lru: keep the last N keys."""
    def __init__(self, policy="classic", size=100): self.policy, self.size, self.d, self.tick = policy, size, {}, 0
    def begin(self, keys):
        self.tick += 1
        if self.policy == "classic": self.d = {k: v for k, v in self.d.items() if k in keys}
        if self.policy == "lru":
            for k in keys:
                if k in self.d: self.d[k] = (self.d[k][0], self.tick)
            while len(self.d) > self.size: self.d.pop(min(self.d, key=lambda k: self.d[k][1]))
        if self.policy == "none": self.d = {}
    def get(self, k): return self.d[k][0] if k in self.d else None
    def put(self, k, v): self.d[k] = (v, self.tick)
def run(p, cache):
    keys = {i: signature(p, i) for i in p}; cache.begin(set(keys.values())); ran = []
    def eval_(i):
        c = cache.get(keys[i])
        if c is not None: return c
        for v in p[i]["inputs"].values():
            if is_link(v): eval_(v[0])
        ran.append(i); cache.put(keys[i], f"out:{i}"); return f"out:{i}"
    for i, n in p.items():
        if n["class_type"] == "Save": eval_(i)
    return ran
def graph(seed=1, text="a fox", steps=20, path="m.safetensors"):
    return {"ckpt": {"class_type": "Load", "inputs": {"name": path}}, "pos": {"class_type": "Text", "inputs": {"clip": ["ckpt", 1], "text": text}},
            "neg": {"class_type": "Text", "inputs": {"clip": ["ckpt", 1], "text": ""}}, "lat": {"class_type": "Empty", "inputs": {"w": 1024, "h": 1024}},
            "smp": {"class_type": "Sample", "inputs": {"model": ["ckpt", 0], "pos": ["pos", 0], "neg": ["neg", 0], "latent": ["lat", 0], "seed": seed, "steps": steps}},
            "dec": {"class_type": "Decode", "inputs": {"samples": ["smp", 0], "vae": ["ckpt", 2]}}, "out": {"class_type": "Save", "inputs": {"images": ["dec", 0], "prefix": "x"}}}
c = Cache(); print("first run          ran:", run(graph(), c))
r = run(graph(), c); print("same graph again   ran:", r); assert r == []
r = run(graph(seed=2), c); print("seed changed       ran:", r); assert r == ["smp", "dec", "out"]
r = run(graph(seed=2, text="a cat"), c); print("prompt changed     ran:", r); assert r == ["pos", "smp", "dec", "out"]
r = run(graph(seed=2, text="a cat", steps=30), c); print("steps changed      ran:", r); assert "ckpt" not in r and "pos" not in r
# The key depends on structure, not on node ids.
g = graph(seed=2, text="a cat", steps=30); ren = {"ckpt": "A", "pos": "B", "neg": "C", "lat": "D", "smp": "E", "dec": "F", "out": "G"}
def rename(g): return {ren[i]: {"class_type": n["class_type"], "inputs": {k: [ren[v[0]], v[1]] if is_link(v) else v for k, v in n["inputs"].items()}} for i, n in g.items()}
r = run(rename(g), c); print("all ids renamed    ran:", r); assert r == []
# IS_CHANGED / fingerprint_inputs: a value that joins the signature. Same fingerprint: cached. New file content: runs again.
f = {"f": {"class_type": "LoadFile", "inputs": {"path": "in.png"}}, "out": {"class_type": "Save", "inputs": {"images": ["f", 0], "prefix": "y"}}}
c2 = Cache(); print("\nfile node, first   ran:", run(f, c2)); r = run(f, c2); print("file unchanged     ran:", r); assert r == []
FILE_CONTENT["v"] = "hash-B"; r = run(f, c2); print("file edited on disk ran:", r); assert r == ["f", "out"]
# float("NaN") is how IS_CHANGED says "always run", because NaN != NaN.
nan = float("nan"); print("NaN == NaN:", nan == nan, "  so a key holding NaN never matches, and the node always runs")
# Two identical non-idempotent nodes do not share an output.
n2 = {"a": {"class_type": "Noise", "inputs": {"seed": 5}}, "b": {"class_type": "Noise", "inputs": {"seed": 5}}, "out": {"class_type": "Save", "inputs": {"x": ["a", 0], "y": ["b", 0]}}}
print("same inputs, not_idempotent, two nodes: keys equal?", signature(n2, "a") == signature(n2, "b"))
plain = {"a": {"class_type": "Empty", "inputs": {"w": 1}}, "b": {"class_type": "Empty", "inputs": {"w": 1}}}; print("same inputs, ordinary node, two nodes: keys equal?", signature(plain, "a") == signature(plain, "b"))
assert signature(n2, "a") != signature(n2, "b") and signature(plain, "a") == signature(plain, "b")
# Cache policies: alternate between two prompts A B A B.
print("\npolicy         nodes run over A B A B   (7 per full run)")
res = {}
for name, cache in (("classic", Cache("classic")), ("lru 100", Cache("lru", 100)), ("lru 4", Cache("lru", 4)), ("none", Cache("none"))):
    total = 0
    for seed in (1, 2, 1, 2): total += len(run(graph(seed=seed), cache))
    res[name] = total; print(f"{name:14s} {total}")
assert res["classic"] > res["lru 100"] and res["none"] == 28
