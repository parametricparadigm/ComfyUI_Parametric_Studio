"""Proof levels for workflows, with evidence that EXPIRES. recipe: the template exists. load-tested: it validates against a live /object_info and every model file is present. verified: it ran end to end and the
outputs were recorded (sha256, size, seconds). A 'verified' label is valid only while the template is byte-identical to the one that ran and the recorded outputs still exist; otherwise the level falls back, so the
label can never claim more than the evidence shows. Idea carried over from the home studio's LoRA proof levels (verified / load-tested / recipe). Original code."""
import hashlib, json, os, time

STATE = os.environ.get("PSN_STATE_DIR") or os.path.expanduser("~/.local/state/parametric_studio")
LEVELS = ("recipe", "load-tested", "verified")

def graph_hash(graph): return hashlib.sha256(json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def _path(wid): return os.path.join(STATE, "proof", os.path.basename(wid) + ".json")
def _load(wid):
    try: return json.load(open(_path(wid)))
    except (OSError, ValueError): return {}
def _save(wid, d): os.makedirs(os.path.dirname(_path(wid)), exist_ok=True); json.dump(d, open(_path(wid), "w"), indent=1)
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(1 << 24): h.update(c)
    return h.hexdigest()

def record_load_test(wid, graph, problems, readiness):
    """problems: validation problems against /object_info (list); readiness: psn.readiness.check() result. Passes only when both are clean."""
    d = _load(wid); d["load_test"] = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "graph_hash": graph_hash(graph), "problems": problems[:10], "models_missing": [m["value"] for m in readiness["missing"]], "passed": not problems and readiness["ready"]}; _save(wid, d); return d["load_test"]

def record_run(wid, graph, output_files, seconds=None, notes=""):
    files = [{"path": p, "bytes": os.path.getsize(p), "sha256": sha256_file(p)} for p in output_files if os.path.isfile(p)]
    if not files: raise ValueError("no output files to record: a run without outputs is not evidence")
    ran_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(max(os.path.getmtime(f["path"]) for f in files)))      # when the OUTPUT was written, not when this record was made
    d = _load(wid); d["run"] = {"ts": ran_at, "recorded": time.strftime("%Y-%m-%dT%H:%M:%S"), "graph_hash": graph_hash(graph), "files": files, "seconds": seconds, "notes": notes}; _save(wid, d); return d["run"]

def level(wid, graph):
    """-> (level, why). Highest level whose evidence is still valid for this exact graph."""
    d, gh = _load(wid), graph_hash(graph)
    r = d.get("run")
    if r:
        if r["graph_hash"] != gh: why = "verified run is for an older version of the workflow"
        elif not all(os.path.isfile(f["path"]) and os.path.getsize(f["path"]) == f["bytes"] for f in r["files"]): why = "recorded outputs are gone or changed"
        else: return "verified", f"ran {r['ts']}, {len(r['files'])} output(s) recorded"
    else: why = "never run"
    t = d.get("load_test")
    if t and t["graph_hash"] == gh and t["passed"]: return "load-tested", f"validated {t['ts']}; {why}"
    return "recipe", (f"load test failed: {t['problems'][:2] or t['models_missing'][:2]}" if t and t["graph_hash"] == gh else "not load-tested for this version") + f"; {why}"
