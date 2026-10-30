# CU-224 lab: a client for the ComfyUI API, run against an in-memory stub that follows server.py and execution.py. No network, no real server.
# Run: python lab.py  (standard library only, under a second).
import json, uuid, urllib.parse
uuid4 = lambda n=[0]: (n.__setitem__(0, n[0] + 1), f"00000000-0000-4000-8000-{n[0]:012d}")[1]
CLASS_OUTPUT = {"SaveImage"}; KNOWN = {"SaveImage", "VAEDecode", "KSampler", "CheckpointLoaderSimple"}
class Stub:
    """What the real server does for these calls, reduced: same paths, same status codes, same field names, same event order."""
    def __init__(self): self.q = []; self.history = {}; self.events = []; self.cache = set(); self.n = 0; self.files = {}
    def post(self, path, body):
        if path == "/prompt":
            p = body["prompt"]
            for i, node in p.items():
                if node.get("class_type") not in KNOWN: return 400, {"error": {"type": "missing_node_type", "message": f"Node '{node.get('class_type')}' not found. The custom node may not be installed.", "details": f"Node ID '#{i}'", "extra_info": {}}, "node_errors": {}}
            if not any(n["class_type"] in CLASS_OUTPUT for n in p.values()): return 400, {"error": {"type": "prompt_no_outputs", "message": "Prompt has no outputs", "details": "", "extra_info": {}}, "node_errors": {}}
            pid = body.get("prompt_id") or uuid4(); num = self.n; self.n += 1; self.q.append((num, pid, p, body.get("client_id"))); return 200, {"prompt_id": pid, "number": num, "node_errors": {}}
        if path == "/interrupt": return 200, {}
        if path == "/free": return 200, {}
    def get(self, path):
        u = urllib.parse.urlparse(path); qs = urllib.parse.parse_qs(u.query)
        if u.path == "/queue": return 200, {"queue_running": [], "queue_pending": [list(x[:3]) for x in self.q]}
        if u.path.startswith("/history/"): pid = u.path.split("/")[-1]; return 200, ({pid: self.history[pid]} if pid in self.history else {})
        if u.path == "/view": return 200, self.files[(qs["filename"][0], qs.get("subfolder", [""])[0], qs.get("type", ["output"])[0])]
    def work(self):
        """One turn of prompt_worker: the events a client with this client_id receives on /ws."""
        num, pid, p, cid = self.q.pop(0); ev = lambda t, **d: self.events.append({"type": t, "data": {**d, "prompt_id": pid}})
        ev("execution_start"); keyed = {i: json.dumps(n, sort_keys=True) for i, n in p.items()}; cached = [i for i, k in keyed.items() if k in self.cache]; ev("execution_cached", nodes=cached); out = {}
        for i, n in p.items():
            if i in cached:                                          # emit_cached_output: a cached output node still reports its files
                if n["class_type"] == "SaveImage": f = {"filename": "app_00001_.png", "subfolder": "", "type": "output"}; out[i] = {"images": [f]}; ev("executed", node=i, output={"images": [f]})
                continue
            ev("executing", node=i)
            if n["class_type"] == "KSampler":
                for s in range(1, 4): ev("progress", value=s, max=3, node=i)
            if n["class_type"] == "SaveImage":
                f = {"filename": "app_00001_.png", "subfolder": "", "type": "output"}; self.files[(f["filename"], "", "output")] = b"\x89PNG..."; out[i] = {"images": [f]}; ev("executed", node=i, output={"images": [f]})
            self.cache.add(keyed[i])
        ev("execution_success"); ev("executing", node=None)
        self.history[pid] = {"prompt": [num, pid, p, {}, list(CLASS_OUTPUT & {n["class_type"] for n in p.values()})], "outputs": out, "status": {"status_str": "success", "completed": True, "messages": []}}
s = Stub(); client = uuid4()
good = {"3": {"class_type": "KSampler", "inputs": {"seed": 1}}, "9": {"class_type": "SaveImage", "inputs": {"images": ["3", 0], "filename_prefix": "app"}}}
print("POST /prompt, unknown node ->", s.post("/prompt", {"prompt": {"1": {"class_type": "Nope", "inputs": {}}}})[0], s.post("/prompt", {"prompt": {"1": {"class_type": "Nope", "inputs": {}}}})[1]["error"]["type"])
print("POST /prompt, no output    ->", s.post("/prompt", {"prompt": {"3": good["3"]}})[0], s.post("/prompt", {"prompt": {"3": good["3"]}})[1]["error"]["type"])
st, r = s.post("/prompt", {"prompt": good, "client_id": client}); pid = r["prompt_id"]; print("POST /prompt, good         ->", st, {k: r[k] for k in ("number", "node_errors")}); assert st == 200
print("GET /queue pending:", len(s.get("/queue")[1]["queue_pending"])); s.work()
print("\nevents on the websocket, in order:")
done = False
for e in s.events:
    d = e["data"]; print(" ", e["type"], {k: v for k, v in d.items() if k != "prompt_id"})
    if e["type"] == "executing" and d["node"] is None and d["prompt_id"] == pid: done = True   # how the official example knows it finished
assert done
h = s.get("/history/" + pid)[1][pid]; imgs = [i for o in h["outputs"].values() for i in o["images"]]; print("\nGET /history/<id> status:", h["status"]["status_str"], " images:", imgs)
q = urllib.parse.urlencode({"filename": imgs[0]["filename"], "subfolder": imgs[0]["subfolder"], "type": imgs[0]["type"]}); print("GET /view?" + q, "->", s.get("/view?" + q)[1][:4]); assert s.get("/view?" + q)[1].startswith(b"\x89PNG")
# Same prompt again: no node function runs and there is no progress, but the cached output node still reports its files.
s.events.clear(); st, r = s.post("/prompt", {"prompt": good, "client_id": client}); s.work(); kinds = [e["type"] for e in s.events]; print("\nsame prompt again:", kinds, " cached:", s.events[1]["data"]["nodes"]); assert "progress" not in kinds
print("outputs recorded for that run:", s.history[r["prompt_id"]]["outputs"]); assert s.history[r["prompt_id"]]["outputs"]
