"""What ComfyUI is doing right now, node by node. ComfyUI only tells the client that queued a prompt which node it is running, over a websocket, so one small reader thread listens with that client's id and keeps the state in memory.
GET /api/live: the exact graph in ComfyUI's queue plus the state of every node. GET /api/live/preview: the latest denoising preview frame. Standard library only. The reader starts on the first request, never at import, and only ever follows studio client ids, so it cannot take over a ComfyUI browser tab's socket."""
import base64, json, os, select, socket, struct, threading, time, urllib.parse, urllib.request
from fastapi import APIRouter, HTTPException, Response
router = APIRouter()
COMFY = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")
LOCK = threading.Lock(); S = {"want": None, "client": None, "up": False, "thread": None, "seq": 0, "preview": None, "mime": "image/jpeg", "current": None, "last": None}; JOBS: dict = {}
def _get(path, timeout=4):
    with urllib.request.urlopen(COMFY + path, timeout=timeout) as r: return json.loads(r.read() or b"{}")
def _vram():
    try: d = (_get("/system_stats", 2).get("devices") or [{}])[0]; return round((d.get("vram_total", 0) - d.get("vram_free", 0)) / 2**30, 1)
    except Exception: return None
def _job(pid):
    j = JOBS.get(pid)
    if j is None:
        while len(JOBS) > 40: JOBS.pop(next(iter(JOBS)))
        j = JOBS[pid] = {"running": {}, "done": [], "cached": [], "error": None, "status": "running", "times": {}, "vram": {}, "t0": {}, "t": time.time()}
    return j
def _finish(j, nid, now, vram=None):
    """One node finished: record its elapsed time and the GPU memory in use."""
    if nid in j["running"]: j["running"].pop(nid, None)
    if nid not in j["done"] and nid not in j["cached"]: j["done"].append(nid)
    if nid in j["t0"] and nid not in j["times"]: j["times"][nid] = round(now - j["t0"][nid], 2)
    if vram is not None: j["vram"].setdefault(nid, vram)
def apply_event(msg, now=None, vram=None):
    """Update job state from one ComfyUI websocket message. Pure apart from the module's job table, and tested with recorded messages. vram: optional callable."""
    now = time.time() if now is None else now; t = msg.get("type"); d = msg.get("data") or {}; pid = d.get("prompt_id") or S["current"]
    if t == "status" or not pid: return
    j = _job(pid); S["current"] = pid
    if t == "execution_start": j["t"] = now; S["preview"] = None      # never show the last frame of the job before
    elif t == "execution_cached":
        for n in d.get("nodes") or []:
            if n not in j["cached"]: j["cached"].append(n)
    elif t == "executing":
        n = d.get("display_node") or d.get("node")
        if n is None: j["running"].clear(); return
        for o in list(j["running"]):
            if o != n: _finish(j, o, now, vram() if vram else None)
        j["running"].setdefault(n, [0, 0]); j["t0"].setdefault(n, now)
    elif t == "progress":
        n = d.get("node")
        if n is not None: j["running"][n] = [d.get("value", 0), d.get("max", 0)]; j["t0"].setdefault(n, now)
    elif t == "progress_state":
        states = d.get("nodes") or {}
        for key, st in states.items():
            n = st.get("display_node_id") or st.get("node_id") or key
            if st.get("state") == "running": j["running"][n] = [st.get("value", 0), st.get("max", 0)]; j["t0"].setdefault(n, now)
            elif st.get("state") == "finished": _finish(j, n, now, vram() if vram and n in j["running"] else None)
    elif t == "executed":
        n = d.get("display_node") or d.get("node")
        if n is not None: _finish(j, n, now, vram() if vram else None)
    elif t == "execution_success":
        for n in list(j["running"]): _finish(j, n, now, vram() if vram else None)
        j["status"] = "success"; S["last"] = pid
    elif t == "execution_error":
        j["running"].clear(); j["error"] = d.get("node_id"); j["status"] = "error"; S["last"] = pid
    elif t == "execution_interrupted":
        j["running"].clear(); j["status"] = "interrupted"; S["last"] = pid
def apply_binary(data):
    """Binary frames: event 1 is a preview image, then 4 bytes for its type (1 JPEG, 2 PNG)."""
    if len(data) < 8 or struct.unpack(">I", data[:4])[0] != 1: return
    S["mime"] = "image/png" if struct.unpack(">I", data[4:8])[0] == 2 else "image/jpeg"; S["preview"] = data[8:]; S["seq"] += 1
def _read(s, n):
    b = bytearray()
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c: raise EOFError("socket closed")
        b += c
    return bytes(b)
def read_frame(s):
    """-> (fin, opcode, payload) for one RFC 6455 frame."""
    h = _read(s, 2); n = h[1] & 127; masked = h[1] & 128
    if n == 126: n = struct.unpack(">H", _read(s, 2))[0]
    elif n == 127: n = struct.unpack(">Q", _read(s, 8))[0]
    mask = _read(s, 4) if masked else None; data = _read(s, n)
    if mask: data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
    return bool(h[0] & 128), h[0] & 15, data
def _connect(client):
    u = urllib.parse.urlparse(COMFY); s = socket.create_connection((u.hostname, u.port or 80), timeout=5); key = base64.b64encode(os.urandom(16)).decode()
    s.sendall(f"GET /ws?clientId={urllib.parse.quote(client)} HTTP/1.1\r\nHost: {u.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()); head = b""
    while b"\r\n\r\n" not in head:
        c = s.recv(1)
        if not c: raise EOFError("no handshake")
        head += c
    if b" 101 " not in head.split(b"\r\n", 1)[0]: raise ConnectionError("websocket refused")
    return s
def _run():
    while True:
        client = S["want"]
        if not client: time.sleep(0.5); continue
        s = None
        try:
            s = _connect(client); S["client"] = client; S["up"] = True; parts = b""; op0 = 0
            while S["want"] == client:
                if not select.select([s], [], [], 1.0)[0]: continue
                fin, op, data = read_frame(s)
                if op == 8: break
                if op == 9: s.sendall(bytes([0x8A, 0x80 | len(data)]) + b"\0\0\0\0" + data); continue
                if op == 0: parts += data
                else: parts = data; op0 = op
                if not fin: continue
                with LOCK:
                    if op0 == 2: apply_binary(parts)
                    elif op0 == 1:
                        try: apply_event(json.loads(parts), vram=_vram)
                        except ValueError: pass
                parts = b""
        except Exception: time.sleep(3)
        finally:
            S["up"] = False
            if s:
                try: s.close()
                except OSError: pass
def follow(client):
    if not client: return
    S["want"] = client
    if S["thread"] is None: S["thread"] = threading.Thread(target=_run, daemon=True, name="studio-live"); S["thread"].start()
def _view(pid):
    j = JOBS.get(pid) or {}
    return {"running": j.get("running", {}), "done": j.get("done", []), "cached": j.get("cached", []), "error": j.get("error"), "times": j.get("times", {}), "vram": j.get("vram", {})}
@router.get("/api/live")
def live(have: str = ""):
    try: q = _get("/queue")
    except Exception: return {"running": False, "comfy": False}
    run = (q.get("queue_running") or [None])[0]; pending = len(q.get("queue_pending") or [])
    if not run:
        with LOCK: last = S["last"]; v = _view(last) if last else None; st = (JOBS.get(last) or {}).get("status")
        return {"running": False, "pending": pending, "last": {"job": last, "status": st, "nodes": v} if last else None}
    jid = run[1]; extra = run[3] if len(run) > 3 and isinstance(run[3], dict) else {}; client = str(extra.get("client_id") or ""); ours = client.startswith("studio-")
    if ours: follow(client)
    with LOCK: S["current"] = jid; v = _view(jid); seq = S["seq"]
    out = {"running": True, "job": jid, "pending": pending, "mode": "nodes" if ours and S["up"] and S["client"] == client else "pulse", "nodes": v, "preview": seq if S["preview"] else 0}
    if have != jid: out["graph"] = run[2]
    return out
@router.get("/api/live/preview")
def live_preview():
    with LOCK: b = S["preview"]; mime = S["mime"]
    if not b: raise HTTPException(404, "no preview yet")
    return Response(b, media_type=mime, headers={"Cache-Control": "no-store"})
