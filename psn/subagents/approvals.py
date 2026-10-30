"""Owner approvals. A subagent has NO tool that posts, sends, publishes, spends, restarts a service, deletes or installs: it can only file a request here, then stop. The owner lists and
decides with `python3 -m psn.subagents.approvals list|approve ID|deny ID`; a decision is just a file, so any front-end (a node, a phone bridge) can read it."""
import json, os, sys, time, uuid
KINDS = ("publish", "post", "send", "spend", "restart_service", "delete", "install", "other")
def _dir():
    d = os.path.join(os.environ.get("PSN_STATE_DIR") or os.path.expanduser("~/.local/state/parametric_studio"), "approvals"); os.makedirs(d, exist_ok=True); return d
def request(kind, details, requested_by=""):
    if kind not in KINDS: kind = "other"
    rid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    rec = {"id": rid, "kind": kind, "details": str(details)[:2000], "by": requested_by, "status": "pending", "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    fd = os.open(os.path.join(_dir(), rid + ".json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(rec, f)
    return rec
def get(rid): return json.load(open(os.path.join(_dir(), os.path.basename(rid) + ".json")))
def decide(rid, approve):
    r = get(rid); r["status"] = "approved" if approve else "denied"; r["decided"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(r, open(os.path.join(_dir(), r["id"] + ".json"), "w")); return r
def pending(): return [json.load(open(os.path.join(_dir(), f))) for f in sorted(os.listdir(_dir())) if f.endswith(".json") and json.load(open(os.path.join(_dir(), f)))["status"] == "pending"]
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["list"]: [print(r["id"], r["kind"], r["by"], r["details"][:100]) for r in pending()]
    elif a[:1] in (["approve"], ["deny"]) and len(a) == 2: print(decide(a[1], a[0] == "approve"))
    else: print(__doc__)
