"""Minimal ComfyUI client (standard library): fill a ${placeholder} template, queue it on a LOCAL ComfyUI, wait, download outputs. Loopback only."""
import json, re, time, urllib.request, urllib.parse, urllib.error, os
_PH = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

def fill(graph, values):
    def w(v):
        if isinstance(v, str):
            m = _PH.fullmatch(v)
            if m: return values[m.group(1)]
            return _PH.sub(lambda mm: str(values[mm.group(1)]), v)
        if isinstance(v, dict): return {k: w(x) for k, x in v.items()}
        if isinstance(v, list): return [w(x) for x in v]
        return v
    return w(graph)

def placeholders(graph): return set(_PH.findall(json.dumps(graph)))

def _req(base, path, payload=None, raw=False, timeout=120):
    u = urllib.parse.urlparse(base)
    if u.hostname not in ("127.0.0.1", "localhost", "::1"): raise PermissionError("ComfyUI must be on this machine")
    r = urllib.request.Request(base.rstrip("/") + path, json.dumps(payload).encode() if payload is not None else None, {"Content-Type": "application/json"} if payload is not None else {})
    with urllib.request.urlopen(r, timeout=timeout) as x: b = x.read()
    return b if raw else json.loads(b or b"{}")

def run(base, graph, dest, timeout=900, poll=1.0):
    """-> {"job_id", "files": [paths]}; raises RuntimeError with the node error text on failure."""
    try: pid = _req(base, "/prompt", {"prompt": graph, "client_id": "psn-subagent"})["prompt_id"]
    except urllib.error.HTTPError as e:
        b = json.loads(e.read() or b"{}"); raise RuntimeError("graph rejected: " + str((b.get("error") or {}).get("message", e)) + " " + json.dumps(b.get("node_errors", {}))[:400])
    t0 = time.monotonic()
    while True:
        h = _req(base, f"/history/{pid}").get(pid)
        if h and ((h.get("status") or {}).get("completed") or (h.get("status") or {}).get("status_str") in ("success", "error")): break
        if time.monotonic() - t0 > timeout:
            try: _req(base, "/queue", {"delete": [pid]}); _req(base, "/interrupt", {})
            except Exception: pass
            raise RuntimeError(f"timed out after {timeout}s")
        time.sleep(poll)
    if (h.get("status") or {}).get("status_str") == "error":
        for k, i in (h["status"].get("messages") or []):
            if k == "execution_error": raise RuntimeError(f"{i.get('node_type')} (node {i.get('node_id')}): {str(i.get('exception_message', ''))[:300]}")
        raise RuntimeError("job failed")
    os.makedirs(dest, exist_ok=True); files = []
    for out in (h.get("outputs") or {}).values():
        for items in out.values():
            for it in items if isinstance(items, list) else []:
                if isinstance(it, dict) and it.get("filename") and it.get("type", "output") != "temp":
                    q = urllib.parse.urlencode({"filename": it["filename"], "subfolder": it.get("subfolder", ""), "type": it.get("type", "output")})
                    p = os.path.join(dest, os.path.basename(it["filename"])); open(p, "wb").write(_req(base, "/view?" + q, raw=True, timeout=600)); files.append(p)
    return {"job_id": pid, "files": files}
