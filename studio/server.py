"""Parametric Studio API + web app. One small FastAPI app between the browser (desktop or phone over Tailscale) and a plain ComfyUI.
Run:  python -m studio.server   (env: COMFYUI_URL=http://127.0.0.1:8200, STUDIO_PORT=8310, STUDIO_HOST=127.0.0.1)
Open edition: everything generates locally; the only outside calls are the model-catalogue lookups, and downloads happen only after an explicit confirm."""
import os, re, json, secrets, time, uuid, glob, hashlib, tempfile, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from studio.goals import GOALS, WF, values_for
from studio.graph_template import fill, placeholders
from studio import sfw
from psn import paths
from studio import backends

COMFY = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")
ROOT = Path(__file__).resolve().parent; WEB = ROOT / "web"
UNI = Path(os.environ.get("STUDIO_UNIVERSITY") or ROOT / "university")
MODELS = Path(paths.models_root())
STAGING = Path(os.environ.get("STUDIO_STAGING", Path.home() / "studio_downloads"))
app = FastAPI(title="Parametric Studio", docs_url="/api/docs", openapi_url="/api/openapi.json")
CLIENT_ID = "studio-" + uuid.uuid4().hex[:8]; JOBS: dict = {}

def comfy(path, payload=None, timeout=30, raw=False):
    req = urllib.request.Request(COMFY + path, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json"} if payload is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r: b = r.read()
    return b if raw else json.loads(b or b"{}")

def comfy_up():
    try: comfy("/system_stats", timeout=3); return True
    except Exception: return False

@app.get("/api/health")
def health():
    adopt_comfy_paths()
    out = {"comfy": comfy_up(), "comfy_url": COMFY, "edition": os.environ.get("PSN_EDITION", "open"), "backend": backends.target()}
    try: s = comfy("/system_stats", timeout=3); d = (s.get("devices") or [{}])[0]; out["gpu"] = {"name": d.get("name"), "vram_free_gb": round(d.get("vram_free", 0) / 2**30, 1), "vram_total_gb": round(d.get("vram_total", 0) / 2**30, 1)}
    except Exception: pass
    return out

app.include_router(backends.router)

@app.get("/api/graphs")
def graphs(): return [{"goal": k, "label": v["label"], "model": v["family"], "workflow": "workflows/" + v["template"], "url": "/api/graphs/" + k} for k, v in GOALS.items()]

@app.get("/api/graphs/{goal}")
def graph_of(goal: str):
    """The API-format ComfyUI graph behind a goal. ${names} are what /api/generate fills in; POST /api/graph returns it filled."""
    if goal not in GOALS: raise HTTPException(404, "no such goal")
    tpl = json.load(open(os.path.join(WF, GOALS[goal]["template"]))); return {"goal": goal, "fills": sorted(placeholders(tpl)), "graph": tpl}

@app.get("/api/goals")
def goals(): return {k: {kk: vv for kk, vv in v.items() if kk not in ("template",)} | {"id": k} for k, v in GOALS.items()}

def _graph(goal, req, image_name=None):
    sfw.check(*(req.get(k) for k in ("prompt", "lyrics", "target", "scene")))
    g = GOALS[goal]; tpl = json.load(open(os.path.join(WF, g["template"]))); vals, opts = values_for(goal, req, image_name)
    if not vals["prompt"]: raise HTTPException(400, "write a prompt first")
    if g["needs_image"] and not image_name: raise HTTPException(400, "add an image to animate")
    miss = placeholders(tpl) - set(vals)
    if miss: raise HTTPException(500, f"template needs {sorted(miss)}")
    graph = fill(tpl, vals)
    try:
        from studio.names import resolve_names
        graph, _rep = resolve_names(graph, comfy("/object_info", timeout=20))        # portable across boxes: map file names onto what is installed
    except Exception: pass
    return graph, vals, opts

@app.post("/api/graph")
async def graph_only(req: Request):
    b = await req.json()
    if b.get("family_job"):
        from studio import families_api
        return families_api.job_graph(b["family_job"])
    g, vals, opts = _graph(b.get("goal", "image"), b, b.get("image")); return {"graph": g, "values": vals}

@app.post("/api/generate")
async def generate(req: Request):
    b = await req.json(); goal = b.get("goal", "image")
    if goal not in GOALS: raise HTTPException(400, "unknown goal")
    g, vals, opts = _graph(goal, b, b.get("image"))
    if backends.use_sdk():
        from studio.goals import COMFY_INPUT
        meta = {"goal": goal, "prompt": vals["prompt"], "seed": vals["seed"], "options": opts, "graph_hash": hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()[:12]}
        try: jid = backends.submit(g, [b.get("image"), b.get("video"), b.get("last_image")], COMFY_INPUT, meta)
        except Exception as e: raise HTTPException(402 if type(e).__name__ == "InsufficientCredits" else 400, f"Comfy SDK: {type(e).__name__}: {str(e)[:300]}") from None
        return {"job": jid, "seed": vals["seed"], "options": opts, "graph_hash": meta["graph_hash"]}
    if not comfy_up(): raise HTTPException(503, f"ComfyUI is not reachable at {COMFY}")
    try: res = comfy("/prompt", {"prompt": g, "client_id": CLIENT_ID})
    except urllib.error.HTTPError as e:
        body = json.loads(e.read() or b"{}"); ne = body.get("node_errors") or {}
        raise HTTPException(400, "ComfyUI rejected the graph: " + ((body.get("error") or {}).get("message", "") + " " + "; ".join(f"{k}: " + ", ".join(x.get("message", "") for x in v.get("errors", [])) for k, v in list(ne.items())[:3]))) from None
    jid = res["prompt_id"]; JOBS[jid] = {"goal": goal, "prompt": vals["prompt"], "seed": vals["seed"], "options": opts, "started": time.time(), "graph_hash": hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()[:12]}
    return {"job": jid, "seed": vals["seed"], "options": opts, "graph_hash": JOBS[jid]["graph_hash"]}

def _files(hist):
    out = []
    for nid, o in (hist.get("outputs") or {}).items():
        for items in o.values():
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and it.get("filename") and it.get("type") != "temp":
                        out.append({"filename": it["filename"], "subfolder": it.get("subfolder", ""), "type": it.get("type", "output"), "url": "/api/view?" + urllib.parse.urlencode({"filename": it["filename"], "subfolder": it.get("subfolder", ""), "type": it.get("type", "output")}), "kind": "video" if it["filename"].lower().endswith((".mp4", ".webm", ".gif", ".mov")) else "audio" if it["filename"].lower().endswith((".wav", ".mp3", ".flac", ".opus", ".ogg", ".m4a")) else "image"})
    return out

@app.get("/api/jobs/{jid}")
def job(jid: str):
    if jid in backends.JOBS: return backends.status(jid)
    meta = JOBS.get(jid, {})
    try: h = comfy(f"/history/{urllib.parse.quote(jid)}").get(jid)
    except Exception: h = None
    if h:
        st = h.get("status") or {}
        if st.get("status_str") == "error":
            msg = next((i.get("exception_message", "") for k, i in st.get("messages", []) if k == "execution_error"), "")
            return {"status": "error", "error": msg.strip()[:400], **meta}
        if st.get("completed") or st.get("status_str") == "success": return {"status": "done", "files": _files(h), "seconds": round(time.time() - meta.get("started", time.time()), 1), **meta}
    try:
        q = comfy("/queue", timeout=5); running = any(len(e) > 1 and e[1] == jid for e in q.get("queue_running", [])); pending = [i for i, e in enumerate(q.get("queue_pending", [])) if len(e) > 1 and e[1] == jid]
        return {"status": "running" if running else "queued", "position": (pending[0] + 1) if pending else 0, "elapsed": round(time.time() - meta.get("started", time.time()), 1), **meta}
    except Exception: return {"status": "unknown", **meta}

@app.post("/api/jobs/{jid}/cancel")
def cancel(jid: str):
    if jid in backends.JOBS: backends.cancel(jid); return {"ok": True}
    try: comfy("/queue", {"delete": [jid]}); comfy("/interrupt", {})
    except Exception: pass
    return {"ok": True}

@app.get("/api/view")
def view(filename: str, subfolder: str = "", type: str = "output"):
    if type not in ("output", "input", "temp") or ".." in filename or ".." in subfolder: raise HTTPException(400, "bad path")
    try:
        r = urllib.request.urlopen(COMFY + "/view?" + urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": type}), timeout=60)
    except Exception: raise HTTPException(404, "file not found") from None
    return StreamingResponse(r, media_type=r.headers.get("Content-Type", "application/octet-stream"), headers={"Cache-Control": "public, max-age=3600"})

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 300 * 2**20: raise HTTPException(413, "file over 300 MB")
    if not re.search(r"\.(png|jpe?g|webp|mp4|webm|mov|mkv|wav|mp3|flac)$", file.filename or "", re.I): raise HTTPException(400, "png, jpg, webp, mp4, webm, mov, mkv, wav, mp3 or flac only")
    fn = file.filename or ""; name = "studio_" + hashlib.sha256(data).hexdigest()[:10] + os.path.splitext(fn)[1].lower()
    b = uuid.uuid4().hex; head = (f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: {file.content_type or "image/png"}\r\n\r\n').encode()
    tail = (f'\r\n--{b}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{b}--\r\n').encode()
    try: r = urllib.request.urlopen(urllib.request.Request(COMFY + "/upload/image", data=head + data + tail, headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=60)
    except Exception: raise HTTPException(503, "ComfyUI is not reachable") from None
    return {"name": json.loads(r.read())["name"]}

def _family_history(limit):
    try:
        from studio import families_api
        return families_api.history_rows(limit)
    except Exception: return []

@app.get("/api/history")
def history(limit: int = 40):
    try: h = comfy(f"/history?max_items={int(limit)}", timeout=10)
    except Exception: return (_family_history(limit) + backends.history()[-limit:][::-1])[:limit]
    rows = []
    for jid, e in h.items():
        fs = _files(e)
        if fs: rows.append({"job": jid, "files": fs, **{k: v for k, v in JOBS.get(jid, {}).items() if k in ("goal", "prompt", "seed", "options")}})
    try:
        from studio import recipes as _R; films = _R.library_rows(limit)       # finished recipe films sit next to single renders
    except Exception: films = []
    return (films + _family_history(limit) + backends.history()[::-1] + rows[::-1])[:limit]

# ---------- University
def _uni_catalogue():
    p = UNI / "catalogue.json"
    return json.load(open(p)) if p.exists() else {"levels": {}, "characters": {}, "courses": []}

@app.get("/api/university")
def university(): return _uni_catalogue()

@app.get("/api/university/{code}")
def course(code: str):
    if not re.fullmatch(r"CU-\d{3}", code): raise HTTPException(400, "bad course code")
    c = next((c for c in _uni_catalogue()["courses"] if c["code"] == code), None)
    if not c: raise HTTPException(404, "no such course")
    d = UNI / c["path"]; rd = lambda n: (d / n).read_text(errors="replace") if (d / n).exists() else ""
    q = json.loads(rd("quiz.json") or "{}")
    return {**c, "lesson": rd("lesson.md"), "lab": rd("lab.py"), "lab_output": rd("lab_output.txt"), "quiz": [{k: v for k, v in x.items()} for x in q.get("questions", [])]}

# ---------- Models + catalogue browser
_MODELS_CACHE: dict = {}
@app.get("/api/models")
def models():
    hit = _MODELS_CACHE.get("v")
    if hit and time.time() - hit[0] < 60: return hit[1]
    base = MODELS / "_complete_pipelines"; fams = []
    if base.is_dir():
        for d in sorted(base.iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                n = sum(1 for _ in d.rglob("*") if _.is_file() or _.is_symlink()); fams.append({"family": d.name, "files": n})
    _MODELS_CACHE["v"] = (time.time(), {"families": fams})
    return {"families": fams}

@app.get("/api/llm")
def llm_plan(tier: str = ""):
    """Which crew LLM fits this box, with the exact llama-server / vLLM command. ?tier=small previews another tier."""
    from studio import llm_tiers as L
    prof = L.detect_profile(); best = L.pick(prof)
    t = tier or best.get("tier")
    if t and t not in L.BY_ID: raise HTTPException(404, "no such tier")
    cmd = None
    if t: cmd = L.command_line(L.vllm_args("<models dir>") if t == "studio" else L.llama_args(t, "<models dir>", cores=prof["cores"]))
    return {"profile": prof, "pick": best, "tier": t, "command": cmd, "tiers": [{k: v for k, v in x.items() if k != "gguf"} | {"file": (x["gguf"] or {}).get("file")} for x in L.TIERS]}

@app.get("/api/browse/{source}")
def browse(source: str, q: str = "", kind: str = "", limit: int = 20):
    from psn.connectors import civitai, hf, registry
    from psn.connectors.net import ConnectorError
    if source not in registry.available(): raise HTTPException(404, "that source is not available in this edition")
    try:
        if source == "civitai": return {"items": civitai.search(q, types=[kind] if kind else None, limit=min(limit, 40))}
        return {"items": hf.search(q, pipeline_tag=kind or None, limit=min(limit, 40))}
    except ConnectorError as e: raise HTTPException(502, str(e)) from None

@app.post("/api/browse/download")
async def browse_download(req: Request):
    """Needs {"source", "confirm": true, ...}. Civitai: a file dict from search. Hugging Face: repo_id + filename. Lands in the staging folder; the model sorter files it later."""
    b = await req.json()
    if not b.get("confirm"): raise HTTPException(400, "tick the confirm box: downloads only happen when you ask")
    if os.environ.get("STUDIO_ALLOW_DOWNLOAD", "1") != "1": raise HTTPException(403, "downloads are switched off on this server")
    from psn.connectors import civitai, hf
    from psn.connectors.net import ConnectorError
    try:
        if b.get("source") == "civitai": p = civitai.fetch(b["file"], str(STAGING), confirm=True)
        elif b.get("source") == "huggingface": p = hf.fetch(b["repo_id"], filename=b["filename"], dest_dir=str(STAGING), confirm=True, dry_run=False)
        else: raise HTTPException(400, "unknown source")
    except ConnectorError as e: raise HTTPException(502, str(e)) from None
    return {"saved": str(p)}

# ---------- lanes built in parallel: presets, website builder, crew, 3D
OUTPUT = Path(paths.output_dir())
for _mod in ("presets", "site_api", "crew_api", "voice", "packs", "apps", "edits", "prime", "schedule", "github_link", "calibrate", "attach", "models_api", "phone", "families_api", "recipes", "live_api", "atlas", "processes"):
    try: app.include_router(__import__(f"studio.{_mod}", fromlist=["router"]).router)
    except Exception as e: print(f"[studio] {_mod} not loaded: {type(e).__name__}: {e}")

if os.environ.get("PSN_EDITION") == "extended":
    try: app.include_router(__import__("studio.printify", fromlist=["router"]).router)
    except Exception as e: print(f"[studio] printify not loaded: {e}")

@app.get("/api/models3d")
def models3d():
    from studio import glb
    return {"items": [{**m, "url": "/api/file3d?" + urllib.parse.urlencode({"path": m["path"]})} for m in glb.list_glb(str(OUTPUT))], "sample": "/api/sample.glb"}

@app.get("/api/file3d")
def file3d(path: str):
    p = (OUTPUT / path).resolve()
    if OUTPUT.resolve() not in p.parents or p.suffix.lower() != ".glb" or not p.is_file(): raise HTTPException(404, "no such model")
    return FileResponse(p, media_type="model/gltf-binary")

@app.get("/api/sample.glb")
def sample_glb():
    from studio.glb import knot_glb
    return Response(knot_glb(), media_type="model/gltf-binary")

# ---------- editing: probe + render
import subprocess, threading
EDITS = OUTPUT / "studio_edits"; RENDERS: dict = {}
_adopted = {"done": False}
def adopt_comfy_paths():
    """A folder with no env var and no settings entry comes from the running ComfyUI. Tried at start and on each health check until it has worked once."""
    global MODELS, OUTPUT, EDITS
    if _adopted["done"]: return
    if paths.setting("STUDIO_MODELS_ROOT", "PSN_MODELS_ROOT") and paths.setting("STUDIO_OUTPUT_DIR") or not paths.ask_comfy(): _adopted["done"] = bool(paths.setting("STUDIO_MODELS_ROOT", "PSN_MODELS_ROOT") and paths.setting("STUDIO_OUTPUT_DIR")); return
    MODELS, OUTPUT = Path(paths.models_root(True)), Path(paths.output_dir(True)); EDITS = OUTPUT / "studio_edits"; _adopted["done"] = True

@app.get("/api/probe")
def probe(path: str):
    p = (OUTPUT / path).resolve()
    if OUTPUT.resolve() not in p.parents or not p.is_file(): raise HTTPException(404, "no such file")
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(p)], capture_output=True, text=True, timeout=20)
        d = json.loads(r.stdout or "{}")
    except Exception: raise HTTPException(500, "ffprobe failed") from None
    st = d.get("streams") or []
    return {"duration": float((d.get("format") or {}).get("duration") or 0), "video": any(x.get("codec_type") == "video" for x in st), "audio": any(x.get("codec_type") == "audio" for x in st)}

@app.post("/api/timeline/render")
async def timeline_render_start(req: Request):
    from studio import timeline_render as TR
    b = await req.json(); edl = b.get("edl") or {}
    probs = TR.edl_problems(edl, str(OUTPUT))
    if probs: raise HTTPException(400, "; ".join(probs[:4]))
    rid = uuid.uuid4().hex[:10]; out = EDITS / f"edit_{rid}.mp4"; EDITS.mkdir(parents=True, exist_ok=True); RENDERS[rid] = {"status": "running", "started": time.time()}
    def work():
        try:
            r = TR.render_edl(edl, str(out), str(OUTPUT))
            RENDERS[rid] = {"status": "done" if r.get("ok") else "error", "problems": r.get("problems") or [], "tail": (r.get("ffmpeg_stderr_tail") or "")[-300:], "url": "/api/view?" + urllib.parse.urlencode({"filename": out.name, "subfolder": "studio_edits", "type": "output"}), "seconds": round(time.time() - RENDERS[rid]["started"], 1)}
        except Exception as e: RENDERS[rid] = {"status": "error", "problems": [f"{type(e).__name__}: {str(e)[:120]}"]}
    threading.Thread(target=work, daemon=True).start(); return {"render": rid}

@app.get("/api/timeline/render/{rid}")
def timeline_render_status(rid: str): return RENDERS.get(rid) or {"status": "unknown"}

_CZ: dict = {}
@app.middleware("http")
async def compress_static(request, call_next):
    """Brotli or gzip for the app's own text files only. Media keeps its Range support, and each file is compressed once per version."""
    r = await call_next(request); ae = request.headers.get("accept-encoding", ""); p = request.url.path
    if r.status_code != 200 or p.startswith("/api/") or not re.search(r"(\.(m?js|css|json|svg|html)|/)$", p) or "content-encoding" in r.headers or not ("br" in ae or "gzip" in ae): return r
    body = b"".join([c async for c in r.body_iterator]); enc = "gzip"
    try:
        import brotli
        if "br" in ae: enc = "br"
    except ImportError: pass
    key = (p, enc, hashlib.sha1(body).hexdigest())
    if key not in _CZ: _CZ[key] = brotli.compress(body, quality=5) if enc == "br" else __import__("gzip").compress(body, 6)
    h = {k: v for k, v in r.headers.items() if k.lower() != "content-length"}; h.update({"content-encoding": enc, "vary": "Accept-Encoding"})
    return Response(_CZ[key], status_code=200, headers=h, media_type=r.media_type)

@app.middleware("http")
async def lan_guard(request, call_next):
    """Requests from this machine (including Tailscale Serve, which proxies from localhost) pass. Anything else needs the pairing token, which only exists when the studio was started on a non-loopback address."""
    token = os.environ.get("STUDIO_TOKEN", "")
    if not token or (request.client is not None and request.client.host in ("127.0.0.1", "::1")): return await call_next(request)
    given = request.query_params.get("t") or request.cookies.get("studio_token") or request.headers.get("x-studio-token") or ""
    if not secrets.compare_digest(given.encode(), token.encode()): return JSONResponse({"detail": "This studio needs its pairing link. Open it from the QR code on the computer."}, status_code=401)
    r = await call_next(request)
    if request.query_params.get("t"): r.set_cookie("studio_token", token, max_age=60 * 60 * 24 * 90, httponly=True, samesite="lax")
    return r

@app.middleware("http")
async def no_cache_static(request, call_next):
    r = await call_next(request)
    if not request.url.path.startswith("/api/"): r.headers["Cache-Control"] = "no-cache"
    return r

app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    adopt_comfy_paths()
    if os.environ.get("STUDIO_HOST", "127.0.0.1") not in ("127.0.0.1", "::1", "localhost") and not os.environ.get("STUDIO_TOKEN"):
        os.environ["STUDIO_TOKEN"] = secrets.token_urlsafe(24); print("[studio] open to the local network. Pairing is required; open the Phone panel on this computer for the QR code.", flush=True)
    uvicorn.run(app, host=os.environ.get("STUDIO_HOST", "127.0.0.1"), port=int(os.environ.get("STUDIO_PORT", "8310")), log_level="warning")
