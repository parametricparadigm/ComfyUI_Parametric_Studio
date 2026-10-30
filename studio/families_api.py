"""Model families in the studio: one row per family (status, VRAM estimate, models on disk, last test level, crew, licence, kind, era), start and stop through psn.instances behind its VRAM gate, the family's templates as generated forms that run on the family's own instance, and outputs that outlive the instance.
Facts shipped with the repo live in family_status.json (scripts/build_family_art.py); what this machine has is read live. A job record is kept next to its instance, because a ComfyUI server forgets its history when it stops."""
import json, os, random, re, shutil, threading, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from psn import instances as I
from studio import apps as A
ROOT = Path(__file__).resolve().parent; STATUS = ROOT / "family_status.json"; WEB = ROOT / "web"
REAP_MIN = float(os.environ.get("STUDIO_FAMILY_REAP_MIN", "15")); RUN_TIMEOUT = int(os.environ.get("STUDIO_FAMILY_RUN_TIMEOUT", "1800")); DISK_SPARE_GB = 25
EXT = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".sft", ".onnx", ".pkl")
GOAL_FAMILY = {"image": "Flux.2", "video": "Wan2.2", "animate": "Wan2.2", "reshoot_wan": "Wan2.2", "anime": "Anima", "flux3": "Flux.3-Klein", "video_ltx": "LTX-2.5", "animate_ltx": "LTX-2.5", "vfx_ltx": "LTX-2.5", "music": "Mini-Max-Music3", "h3_video": "MiniMax-H3", "h3_animate": "MiniMax-H3", "recast": "MiniMax-H3", "reshoot": "MiniMax-H3", "orbit360": "MiniMax-H3", "director": "MiniMax-H3", "director_keyframes": "MiniMax-H3"}
LEVEL = {"render": "Rendered here", "validated": "Template checks out", "nodes": "Server starts, no render yet", "started": "Server starts, no render yet", "untested": "Not tested yet"}
router = APIRouter(); _st = {"m": 0.0, "d": {"families": {}}}; _scan = {"t": 0.0, "d": {}}; _names = {"t": 0.0, "d": {}}; _dirs = {"root": None, "t": 0.0, "d": {}}; JOBS: dict = {}; _reaper = {"on": False}; _dl = {"state": None}

def status_data():
    try:
        m = STATUS.stat().st_mtime
        if m != _st["m"]: _st.update(m=m, d=json.load(open(STATUS)))
    except OSError: pass
    return _st["d"]
def instance_dirs():
    """What is really on disk in the instances folder (the source of truth): {family name: dir name}, from each directory's instance.json. A directory with no readable instance.json is listed under its own name, not dropped."""
    if _dirs["root"] == I.INSTANCES and time.time() - _dirs["t"] < 5: return _dirs["d"]
    out = {}
    try: names = sorted(os.listdir(I.INSTANCES))
    except OSError: return out
    for d in names:
        p = os.path.join(I.INSTANCES, d)
        if not os.path.isdir(p) or d.startswith("."): continue
        try: out[json.load(open(os.path.join(p, "instance.json")))["family"]] = d
        except (OSError, ValueError, KeyError): out[d] = d
    _dirs.update(root=I.INSTANCES, t=time.time(), d=out); return out
def family_names():
    out = set(status_data().get("families", {})) | set(instance_dirs())
    try: out |= set(I.families())
    except OSError: pass
    return sorted(out, key=str.lower)
def _slug(f, dirs=None):
    d = (dirs if dirs is not None else instance_dirs()).get(f); return d or I.slug(f)
def _family(slug):
    dirs = instance_dirs()
    for f in family_names():
        if _slug(f, dirs) == slug or I.slug(f) == slug: return f
    raise HTTPException(404, "no such family")
def reconcile():
    """Instance directories on disk against the families the page shows: anything on one side only is named, never dropped."""
    dirs = instance_dirs(); known = set(status_data().get("families", {})); reg = {}
    try: reg = json.load(open(os.path.join(I.INSTANCES, "registry.json")))
    except (OSError, ValueError): pass
    try: lib = set(I.families())
    except OSError: lib = set()
    return {"dirs_on_disk": len(dirs), "shown": len(family_names()), "no_instance_file": [d for f, d in dirs.items() if not os.path.exists(os.path.join(I.INSTANCES, d, "instance.json"))], "dir_without_family_entry": sorted(set(dirs) - known), "family_entry_without_dir": sorted(known - set(dirs)), "in_registry_without_dir": sorted(set(reg) - set(dirs)), "model_folder_without_dir": sorted(lib - set(dirs))}
def _meta(f): return status_data().get("families", {}).get(f) or {"slug": _slug(f), "kind": "utility", "era": None, "licence": None, "crew": "master", "repos": [], "what": None, "what_source": None, "level": "untested", "test": {}, "media": [], "templates": []}
def _info(f):
    try: return json.load(open(os.path.join(I.INSTANCES, _slug(f), "instance.json")))
    except (OSError, ValueError): return None
def scan(force=False):
    """family -> {file name: bytes} of the model files its instance can see. A plain walk, cached for five minutes."""
    if not force and _scan["d"]:
        if time.time() - _scan["t"] > 300 and not _scan.get("busy"):
            _scan["busy"] = True; threading.Thread(target=scan, args=(True,), daemon=True, name="family-scan").start()
        return _scan["d"]
    out = {}
    for f in family_names():
        files = {}
        try:
            for rels in I.model_dirs(f).values():
                for rel in rels:
                    for dp, _, fs in os.walk(os.path.join(I.MODELS, rel), followlinks=True):
                        for x in fs:
                            if x.endswith(EXT):
                                try: files[x] = os.path.getsize(os.path.join(dp, x))
                                except OSError: pass
            for _t, name, rel in (I.WRAPS.get(f) or {}).get("files", []):
                p = os.path.join(I.MODELS, rel)
                if os.path.exists(p): files[name] = os.path.getsize(p)
        except OSError: pass
        out[f] = files
    _scan.update(t=time.time(), d=out, busy=False); return out
_shared = {"t": 0.0, "d": {}}
def shared_files():
    """Model files every instance can read besides its own folder: the shared list beside ComfyUI's main.py (instances keep reading it, so shared encoders and VAEs stay available). Empty on a box without one."""
    if _shared["d"] and time.time() - _shared["t"] < 300: return _shared["d"]
    out = {}; base = None; y = os.path.join(os.path.dirname(I.PS_NODES), "extra_model_paths.yaml")
    try: lines = open(y).read().splitlines()
    except OSError: lines = []
    for ln in lines:
        m = re.match(r"\s*base_path:\s*(.*)", ln)
        if m: base = m.group(1).strip(); continue
        m = re.match(r"\s{8}(\S.*)", ln) or re.match(r"\s+\w+:\s+([^|\s].*)", ln)
        if m and base:
            q = m.group(1).strip(); q = q if os.path.isabs(q) else os.path.join(base, q)
            for dp, _, fs in os.walk(q, followlinks=True):
                for x in fs:
                    if x.endswith(EXT):
                        try: out.setdefault(x, os.path.getsize(os.path.join(dp, x)))
                        except OSError: pass
    _shared.update(t=time.time(), d=out); return out
def free_gb():
    try: return round(I.free_vram_gb(), 1)
    except Exception: return None
PRECISION = re.compile(r"[_.-]?(fp8|fp16|fp32|bf16|int8|convrot|scaled|e4m3fn|sft|pruned|ema|emaonly)(?=[_.-]|$)")
_keys = {"id": None, "d": {}}
def _key(n):
    from studio.names import norm
    return PRECISION.sub("", norm(n)).rsplit(".", 1)[0]
def _have(files, name):
    """The installed file that answers for a template's model name: the same base name, or the same name in another precision. Close-but-different names are left to the run step's resolver, which checks variants."""
    b = os.path.basename(name)
    if b in files: return b
    if _keys["id"] != id(files): _keys.update(id=id(files), d={_key(x): x for x in files})
    return _keys["d"].get(_key(b))
_look = {"a": None, "b": None, "d": {}}
def _view(files):
    shared = shared_files()
    if _look["a"] is not files or _look["b"] is not shared: _look.update(a=files, b=shared, d={**shared, **files})
    return _look["d"]
def tpl_state(t, files):
    """Which of a template's model files this family's instance can see: its own folder first, then the shared list every instance reads."""
    look = _view(files); miss = [m for m in t.get("models", []) if not _have(look, m["name"])]; have = [m for m in t.get("models", []) if _have(look, m["name"])]
    gb = sum(look.get(_have(look, m["name"]), 0) for m in have) / 1e9
    return {"ready": not miss, "missing": miss, "missing_gb": round(sum(m.get("gb") or 0 for m in miss), 1) if all(m.get("gb") for m in miss) else None, "need_gb": round(gb * 1.15 + 2.0, 1), "weights_gb": round(gb, 1)}
def _showcase():
    try: items = json.load(open(WEB / "showcase" / "showcase.json"))
    except (OSError, ValueError): return {}
    out = {}
    for x in items:
        f = GOAL_FAMILY.get(x.get("goal"))
        if f: out.setdefault(f, []).append(x)
    return out
def _merge(media, show):
    """Renders of this family first, then studio showcase clips of it that are not already there; a library sample only when nothing was rendered here."""
    seen = {m.get("prompt") for m in media}; real = [m for m in media if not m.get("library")] + [x for x in show if x.get("prompt") not in seen]
    return real or media
def _state(meta, files, info, on_disk=True):
    if not on_disk: return "nodir", "No instance folder yet"
    if not info: return "orphan", "Folder only, no instance file"
    if not files: return "download", "Needs download"
    if info and info.get("loader") == "needs-pack": return "pack", "Needs a node pack"
    return meta.get("level", "untested"), LEVEL.get(meta.get("level"), "Not tested yet")
def _crew(cid):
    try:
        from studio import crew_api
        for m in crew_api._get_roster():
            if m.get("id") == cid: return {"id": cid, "name": m.get("name"), "tier": m.get("tier"), "files": m.get("files") or []}
    except Exception: pass
    return {"id": cid, "name": None, "tier": None, "files": []}
def _row(f, files, sc, crew_names):
    dirs = instance_dirs(); meta, info = _meta(f), _info(f); port = (info or {}).get("port"); up = bool(port and I.is_up(port)); st, lb = _state(meta, files, info, f in dirs); tl = meta.get("templates", []); ready = [t for t in tl if tpl_state(t, files)["ready"]]; media = meta.get("media") or []; show = [x for x in sc.get(f, []) if x.get("kind") != "audio"] + [x for x in sc.get(f, []) if x.get("kind") == "audio"]
    t = meta.get("test") or {}
    return {"family": f, "slug": _slug(f, dirs), "on_disk": f in dirs, "kind": meta.get("kind"), "era": meta.get("era"), "licence": meta.get("licence"), "crew": {"id": meta.get("crew"), "name": crew_names.get(meta.get("crew"))}, "port": port, "generated": bool(info), "status": "up" if up else "down", "up": up, "est_vram_gb": (info or {}).get("est_vram_gb"), "nodes": t.get("nodes"), "psn_nodes": t.get("psn"),
            "models": {"files": len(files), "gb": round(sum(files.values()) / 1e9, 1), "ready": bool(files)}, "level": meta.get("level"), "state": st, "state_label": lb, "note": t.get("note"), "render_secs": t.get("secs"), "peak_gib": t.get("peak_gib"), "tested_template": t.get("tpl"), "templates": len(tl), "templates_ready": len(ready), "media": _merge(media, show)[:1], "media_count": len(_merge(media, show)), "media_library": bool(_merge(media, show)) and bool(_merge(media, show)[0].get("library")), "repos": meta.get("repos", []), "what": meta.get("what")}
@router.get("/api/families")
def families_list():
    fams = family_names(); sc = _showcase(); s = scan()
    try:
        from studio import crew_api
        names = {m.get("id"): m.get("name") for m in crew_api._get_roster()}
    except Exception: names = {}
    rows = [_row(f, s.get(f, {}), sc, names) for f in fams]
    return {"families": rows, "free_gb": free_gb(), "floor_gb": I.FLOOR_GB, "built": status_data().get("built"), "reconcile": reconcile()}
def _dossier(crew):
    """The opening of the crew's SKILL page for this family, when the knowledge base is on this machine and the page passed its source check."""
    for p in crew.get("files") or []:
        if os.path.basename(p) != "SKILL.md": continue
        try: t = open(p, errors="replace").read()
        except OSError: return None
        if "UNVERIFIED" in t[:400] or "NEEDS REVIEW" in t[:400]: return None
        ps = [x.strip() for x in re.split(r"\n\s*\n", t) if x.strip() and not x.strip().startswith(("#", "|", ">", "---"))]
        return re.sub(r"[`*]", "", " ".join(ps[:2]))[:700] or None
    return None
@router.get("/api/families/{slug}")
def family_get(slug: str):
    f = _family(slug); files = scan().get(f, {}); sc = _showcase(); crew = _crew(_meta(f).get("crew")); meta = _meta(f); r = _row(f, files, sc, {crew["id"]: crew["name"]}); info = _info(f); ts = []
    for t in meta.get("templates", []): ts.append({k: t.get(k) for k in ("name", "title", "desc", "media", "cat", "gb", "tags")} | tpl_state(t, files))
    goals = [g for g, x in GOAL_FAMILY.items() if x == f]
    from studio.goals import GOALS
    r.update(media=_merge(meta.get("media") or [], sc.get(f, [])), what_source=meta.get("what_source"), dossier=_dossier(crew), templates_list=sorted(ts, key=lambda x: (not x["ready"], x["need_gb"])), goals=[{"id": g, "label": GOALS[g]["label"]} for g in goals if g in GOALS], packs=[p for p in (info or {}).get("packs", []) if p not in I.COMMON_PACKS], packs_missing=(info or {}).get("packs_not_installed", []), wrap_note=(info or {}).get("note", ""), wrap_missing=[os.path.basename(x) for x in (info or {}).get("wrap_missing", [])], free_gb=free_gb(), floor_gb=I.FLOOR_GB, biggest=[{"name": n, "gb": round(b / 1e9, 2)} for n, b in sorted(files.items(), key=lambda kv: -kv[1])[:8]], test=meta.get("test") or {}, crew={"id": crew["id"], "name": crew["name"]})
    if r["up"]:
        try: r["queue"] = _queue(r["port"]); r["nodes_live"] = len(_oi(r["port"]))
        except Exception: pass
    return r
# ---- gate, start, stop, free ------------------------------------------------------------------------------------------------------------------------------------------
def _ensure(f):
    """The instance directory exists and carries the black, gold and green theme, whatever made it."""
    info = _info(f)
    if not info: ports = I.registry_ports([f]); I.write_unit(); I.subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True); info = I.generate(f, ports=ports)
    I.apply_theme(os.path.join(I.INSTANCES, info["slug"])); return info
def _mark(slug, on=True):
    p = os.path.join(I.INSTANCES, slug, "studio_started")
    try:
        if on: open(p, "w").write(str(time.time()))
        elif os.path.exists(p): os.remove(p)
    except OSError: pass
def refusal(f, need, free):
    idle = idle_servers(); after = None if free is None else round(free - need, 1)
    return {"status": "refused", "family": f, "need_gb": need, "free_gb": free, "floor_gb": I.FLOOR_GB, "short_gb": None if after is None else round(I.FLOOR_GB - after, 1), "idle": [x["name"] for x in idle if x["state"] == "idle"], "busy": [x["name"] for x in idle if x["state"] == "busy"], "message": f"{f} needs about {need} GB and {I.FLOOR_GB} GB must stay free, but only {free} GB is free now."}
def _start(f, need=None, wait=240):
    info = _ensure(f); n = info["est_vram_gb"] if need is None else need; fr = free_gb()
    if I.is_up(info["port"]): return {"status": "already running", "port": info["port"]}
    if fr is None: return {"status": "refused", "family": f, "need_gb": n, "free_gb": None, "floor_gb": I.FLOOR_GB, "idle": [], "busy": [], "message": "This machine does not report GPU memory, so the VRAM check cannot pass."}
    if not I.can_start(f, free_gb=fr, need_gb=n)[0]: return refusal(f, n, fr)
    r = I.start(f, wait=wait, need_gb=n)
    if r["status"] == "refused": return refusal(f, n, free_gb())
    if r["status"] == "started": _mark(info["slug"]); _ensure_reaper()
    return r
@router.post("/api/families/{slug}/start")
def family_start(slug: str, b: dict = None):
    b = b or {}; f = _family(slug); need = b.get("need_gb")
    if need is not None: need = max(I.IDLE_GB, float(need))
    return _start(f, need)
@router.post("/api/families/{slug}/stop")
def family_stop(slug: str):
    f = _family(slug); info = _info(f)
    if not info: return {"status": "stopped"}
    if I.is_up(info["port"]):
        q = _queue(info["port"])
        if q["busy"]: raise HTTPException(409, "This family is running a job. Cancel it first.")
    r = I.stop(f); _mark(info["slug"], False); return r
def _queue(port):
    q = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/queue", timeout=5)); return {"running": len(q.get("queue_running") or []), "pending": len(q.get("queue_pending") or []), "busy": bool(q.get("queue_running") or q.get("queue_pending"))}
def claimed_ports():
    """Ports another tool has claimed on the shared card: a JSON list or {port: ...} in $STUDIO_VRAM_CLAIMS. Those are never freed."""
    p = os.environ.get("STUDIO_VRAM_CLAIMS")
    if not p or not os.path.exists(p): return set()
    try: d = json.load(open(p)); return {int(x) for x in (d if isinstance(d, list) else d.keys())}
    except (OSError, ValueError): return set()
def idle_servers():
    """The ComfyUI servers the studio knows: the main one and every family instance that is up. state: idle, busy or claimed. LLM servers are not on this list and are never touched."""
    out = []; claimed = claimed_ports(); main = A.COMFY
    def one(name, url, port):
        try: q = _queue_url(url)
        except Exception: return
        out.append({"name": name, "url": url, "port": port, "state": "claimed" if port in claimed else "busy" if q else "idle"})
    one("Main ComfyUI", main, urllib.parse.urlparse(main).port)
    for f in family_names():
        i = _info(f)
        if i and I.is_up(i["port"]): one(f, f"http://127.0.0.1:{i['port']}", i["port"])
    return out
def _queue_url(url):
    q = json.load(urllib.request.urlopen(url + "/queue", timeout=5)); return bool(q.get("queue_running") or q.get("queue_pending"))
def _post(url, body, timeout=30): return json.loads(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=timeout).read() or b"{}")
@router.post("/api/families/free-idle")
def free_idle():
    """ComfyUI /free on idle servers only. Never stops a server, never touches anything busy or claimed, never touches an LLM server."""
    before = free_gb(); freed, left = [], []
    for s in idle_servers():
        if s["state"] != "idle": left.append({"name": s["name"], "why": s["state"]}); continue
        try: _post(s["url"] + "/free", {"unload_models": True, "free_memory": True}); freed.append(s["name"])
        except Exception as e: left.append({"name": s["name"], "why": type(e).__name__})
    time.sleep(1.5); return {"freed": freed, "left": left, "free_before_gb": before, "free_gb": free_gb()}
def reap_once(minutes=None):
    """Stop instances the studio itself started that have an empty queue and have sat idle for REAP_MIN minutes. Instances started by anything else are left alone."""
    minutes = REAP_MIN if minutes is None else minutes; out = []
    for f in family_names():
        i = _info(f)
        if not i: continue
        mark = os.path.join(I.INSTANCES, i["slug"], "studio_started")
        if not os.path.exists(mark): continue
        if not I.is_up(i["port"]): _mark(i["slug"], False); continue
        try:
            if _queue(i["port"])["busy"]: continue
            idle = I.idle_seconds(i["port"]); since = time.time() - os.path.getmtime(mark)
            if (idle if idle is not None else since) > minutes * 60 and since > minutes * 60: I.stop(f); _mark(i["slug"], False); out.append(f)
        except Exception: continue
    return out
def _ensure_reaper():
    if _reaper["on"]: return
    _reaper["on"] = True
    def loop():
        while True:
            time.sleep(60)
            try: reap_once()
            except Exception: pass
    threading.Thread(target=loop, daemon=True, name="family-reaper").start()
# ---- templates as forms ------------------------------------------------------------------------------------------------------------------------------------------------
def _oi(port): return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/object_info", timeout=120))
def _tpl(f, tid):
    t = next((t for t in _meta(f).get("templates", []) if t["name"] == tid), None)
    if not t: raise HTTPException(404, "this family has no such template")
    d = A.template_dir(); p = os.path.join(d, tid + ".json") if d else None
    if not p or not os.path.exists(p): raise HTTPException(503, "ComfyUI's template package is not installed in this Python")
    return t, p
@router.get("/api/families/{slug}/templates/{tid}")
def template_form(slug: str, tid: str):
    f = _family(slug); t, p = _tpl(f, tid); info = _info(f); up = bool(info and I.is_up(info["port"])); files = scan().get(f, {})
    try: oi = _oi(info["port"]) if up else A.object_info()
    except Exception: raise HTTPException(503, "Could not read the node list. Start this family or the main ComfyUI first.") from None
    d = A.describe(tid, p, oi); s = tpl_state(t, files)
    return {"id": tid, "title": t.get("title"), "desc": t.get("desc"), "media": t.get("media"), "inputs": d["inputs"], "problems": d["problems"], "unknown_nodes": d["unknown_nodes"], "nodes": d["nodes"], "outputs": d["outputs"], "ready": s["ready"] and d["ready"], "missing": s["missing"], "missing_gb": s["missing_gb"], "need_gb": s["need_gb"], "weights_gb": s["weights_gb"], "gb": t.get("gb"), "checked_on": "this family" if up else "the main ComfyUI"}
def _jobs_file(slug): return os.path.join(I.INSTANCES, slug, "studio_jobs.jsonl")
def _persist(rec):
    try:
        with open(_jobs_file(rec["slug"]), "a") as fh: fh.write(json.dumps(rec) + "\n")
    except OSError: pass
def _file_rows(slug, entry):
    out = []
    for o in (entry.get("outputs") or {}).values():
        for items in o.values():
            if not isinstance(items, list): continue
            for it in items:
                if isinstance(it, dict) and it.get("filename") and it.get("type", "output") != "temp":
                    fn = it["filename"]; out.append({"filename": fn, "subfolder": it.get("subfolder", ""), "type": it.get("type", "output"), "url": f"/api/families/{slug}/view?" + urllib.parse.urlencode({"filename": fn, "subfolder": it.get("subfolder", ""), "type": it.get("type", "output")}), "kind": "video" if fn.lower().endswith((".mp4", ".webm", ".gif", ".mov")) else "audio" if fn.lower().endswith((".wav", ".mp3", ".flac", ".opus", ".ogg", ".m4a")) else "model" if fn.lower().endswith((".glb", ".obj", ".ply", ".spz", ".splat")) else "text" if fn.lower().endswith((".txt", ".json")) else "image"})
    return out
def _prompt_text(values):
    t = [v for k, v in (values or {}).items() if isinstance(v, str) and not re.search(r"\.(png|jpe?g|webp|mp4|webm|mov|wav|flac|mp3|safetensors|ckpt|gguf)$", v, re.I) and len(v) > 3]
    return max(t, key=len) if t else ""
def _work(rec, f, path, values):
    slug = rec["slug"]; t0 = time.time()
    try:
        info = _ensure(f); port = info["port"]
        if not I.is_up(port):
            rec.update(status="starting", step="Starting this family's server"); r = _start(f, rec["need_gb"])
            if r["status"] == "refused": rec.update(r); return
            if r["status"] not in ("started", "already running"): rec.update(status="error", error=f"The server did not start: {r.get('reason') or r['status']}"); return
        else:
            fr = free_gb()
            if fr is not None and fr - rec["need_gb"] < I.FLOOR_GB:
                _post(f"http://127.0.0.1:{port}/free", {"unload_models": True, "free_memory": True}); time.sleep(2); fr = free_gb()
                if fr is not None and fr - rec["need_gb"] < I.FLOOR_GB: rec.update(refusal(f, rec["need_gb"], fr)); return
        rec.update(status="building", step="Building the graph"); oi = _oi(port); g = A.build_graph(path, values, oi); A.fill_dynamic(g, oi); seed = random.randint(1, 2**31)
        for n in g.values():
            for k in ("seed", "noise_seed"):
                if isinstance(n["inputs"].get(k), int) and not any(kk.endswith("|" + k) for kk in values): n["inputs"][k] = seed
        rec.update(graph=g, seed=seed)
        try: pid = _post(f"http://127.0.0.1:{port}/prompt", {"prompt": g, "client_id": "studio-family"}, 60)["prompt_id"]
        except urllib.error.HTTPError as e:
            body = json.loads(e.read() or b"{}"); ne = body.get("node_errors") or {}; rec.update(status="error", error=("ComfyUI rejected the graph: " + (body.get("error") or {}).get("message", "") + " " + "; ".join(f"{k}: " + ", ".join(x.get("message", "") + " " + str((x.get("extra_info") or {}).get("input_name", "")) for x in v.get("errors", [])) for k, v in list(ne.items())[:3]))[:500]); return
        rec.update(status="queued", prompt_id=pid, step="Waiting for the GPU")
        while time.time() - t0 < RUN_TIMEOUT:
            time.sleep(1.5); h = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/history/{pid}", timeout=20)).get(pid)
            if rec.get("cancel"): rec.update(status="error", error="Cancelled"); return
            if not h: rec.update(status="running", step="Running on your GPU") if rec["status"] == "queued" and _queue(port)["running"] else None; continue
            st = h.get("status") or {}
            if st.get("status_str") == "error" or any(m[0] == "execution_error" for m in st.get("messages", [])):
                m = next((m[1] for m in st.get("messages", []) if m[0] == "execution_error"), {}); rec.update(status="error", error=f"{m.get('node_type', '')}: {str(m.get('exception_message', '')).strip()[:300]}"); return
            if st.get("completed") or st.get("status_str") == "success": rec.update(status="done", files=_file_rows(slug, h), seconds=round(time.time() - t0, 1)); return
        rec.update(status="error", error=f"No result after {RUN_TIMEOUT} s")
    except urllib.error.URLError as e: rec.update(status="error", error=f"Lost the family's server: {str(e)[:160]}")
    except Exception as e: rec.update(status="error", error=f"{type(e).__name__}: {str(e)[:300]}")
    finally:
        try:
            if rec.get("prompt_id"): _post(f"http://127.0.0.1:{_info(f)['port']}/free", {"unload_models": True, "free_memory": True}, 20)
        except Exception: pass
        rec["finished"] = time.time(); _persist(rec)
@router.post("/api/families/{slug}/templates/{tid}/run")
def template_run(slug: str, tid: str, b: dict = None):
    b = b or {}; f = _family(slug); t, p = _tpl(f, tid); s = tpl_state(t, scan().get(f, {})); jid = "fam-" + uuid.uuid4().hex[:12]; values = b.get("values") or {}
    if not s["ready"] and not b.get("anyway"): raise HTTPException(400, "This template needs files that are not in this family's folder: " + ", ".join(m["name"] for m in s["missing"][:4]))
    rec = {"job": jid, "slug": slug, "family": f, "template": tid, "title": t.get("title"), "status": "queued", "values": values, "prompt": _prompt_text(values) or t.get("title"), "need_gb": s["need_gb"], "started": time.time()}; JOBS[jid] = rec
    threading.Thread(target=_work, args=(rec, f, p, values), daemon=True, name=f"family-job-{jid}").start(); return {"job": jid, "need_gb": s["need_gb"]}
def _saved_jobs(slug):
    out = []
    try:
        with open(_jobs_file(slug)) as fh:
            for ln in fh:
                try: out.append(json.loads(ln))
                except ValueError: pass
    except OSError: pass
    return out
def _job(slug, jid):
    r = JOBS.get(jid)
    if r and r["slug"] == slug: return r
    r = next((x for x in _saved_jobs(slug) if x.get("job") == jid), None)
    if not r: raise HTTPException(404, "no such job")
    return r
@router.get("/api/families/{slug}/jobs/{jid}")
def job_get(slug: str, jid: str):
    r = _job(slug, jid); return {k: v for k, v in r.items() if k != "graph"} | {"elapsed": round(time.time() - r["started"], 1)}
@router.post("/api/families/{slug}/jobs/{jid}/cancel")
def job_cancel(slug: str, jid: str):
    r = _job(slug, jid); r["cancel"] = True; i = _info(_family(slug))
    try:
        if r.get("prompt_id"): _post(f"http://127.0.0.1:{i['port']}/queue", {"delete": [r["prompt_id"]]}, 10); _post(f"http://127.0.0.1:{i['port']}/interrupt", {}, 10)
    except Exception: pass
    return {"ok": True}
def job_graph(ref):
    """'slug/job' -> the exact graph that job ran, for Pro."""
    slug, _, jid = str(ref).partition("/"); r = _job(slug, jid)
    if not r.get("graph"): raise HTTPException(404, "this job has no graph on record")
    return {"graph": r["graph"], "values": r.get("values") or {}, "family": r.get("family"), "template": r.get("template")}
def history_rows(limit=40):
    """Finished family jobs, newest first, in the shape /api/history uses. Read from the job records, so they stay in the Library after the instance stops."""
    rows = []
    for f in family_names():
        slug = I.slug(f)
        if not os.path.exists(_jobs_file(slug)): continue
        for r in _saved_jobs(slug):
            if r.get("status") == "done" and any(x.get("kind") in ("image", "video", "audio") for x in r.get("files") or []): rows.append({"job": r["job"], "files": [x for x in r["files"] if x.get("kind") in ("image", "video", "audio")], "goal": f, "prompt": r.get("prompt") or r.get("title") or "", "seed": r.get("seed"), "options": {}, "family": slug, "family_name": f, "template": r.get("template"), "title": r.get("title"), "started": r.get("started", 0)})
    return sorted(rows, key=lambda x: -x["started"])[:limit]
def _safe(slug, kind, sub, name):
    if kind not in ("output", "input", "temp") or ".." in name or ".." in sub or "/" in name or name.startswith("."): raise HTTPException(400, "bad path")
    root = (Path(I.INSTANCES) / slug / kind).resolve(); p = (root / sub / name).resolve()
    if root not in p.parents: raise HTTPException(400, "bad path")
    return p
@router.get("/api/families/{slug}/view")
def view(slug: str, filename: str, subfolder: str = "", type: str = "output"):
    f = _family(slug); p = _safe(I.slug(f), type, subfolder, filename)
    if not p.is_file(): raise HTTPException(404, "file not found")
    return FileResponse(p, headers={"Cache-Control": "public, max-age=3600"})
@router.post("/api/families/{slug}/upload")
async def upload(slug: str, file: UploadFile = File(...)):
    f = _family(slug); data = await file.read()
    if len(data) > 300 * 2**20: raise HTTPException(413, "file over 300 MB")
    if not re.search(r"\.(png|jpe?g|webp|mp4|webm|mov|mkv|wav|mp3|flac)$", file.filename or "", re.I): raise HTTPException(400, "png, jpg, webp, mp4, webm, mov, mkv, wav, mp3 or flac only")
    import hashlib
    name = "studio_" + hashlib.sha256(data).hexdigest()[:10] + os.path.splitext(file.filename)[1].lower(); info = _ensure(f); d = Path(I.INSTANCES) / info["slug"] / "input"; d.mkdir(parents=True, exist_ok=True); (d / name).write_bytes(data); return {"name": name}
@router.get("/api/family-graphs")
def family_graphs():
    """Every graph a family page offers, flat, for the Apps page."""
    out = []
    for f, r in status_data().get("families", {}).items():
        art = next((m.get("poster") for m in (r.get("media") or []) if m.get("kind") != "audio" and m.get("poster")), None)
        out += [{"family": f, "slug": r.get("slug"), "name": t.get("name"), "title": t.get("title") or t.get("name"), "desc": t.get("desc") or "", "cat": t.get("cat") or r.get("kind") or "", "art": art} for t in (r.get("templates") or []) if isinstance(t, dict)]
    return {"graphs": out}

# ---- downloads: the exact files a template lists, into the family's own folder, one at a time ---------------------------------------------------------------------------------
@router.get("/api/families/downloads/state")
def download_state(): return _dl["state"] or {"status": "idle"}
@router.post("/api/families/{slug}/templates/{tid}/download")
def template_download(slug: str, tid: str, b: dict = None):
    """Task 4's /api/models/download works per goal; a family template lists its own files, so this fetches exactly those (hash-checked by psn.connectors.net) into _complete_pipelines/<family>/<type>/ where the instance sees them."""
    b = b or {}; f = _family(slug); t, _p = _tpl(f, tid); s = tpl_state(t, scan().get(f, {}))
    if not b.get("confirm"): raise HTTPException(400, "downloads need confirm=true")
    if not s["missing"]: return {"status": "nothing to do"}
    if _dl["state"] and _dl["state"].get("status") == "running": raise HTTPException(409, f"Already downloading {_dl['state'].get('file')}. One at a time.")
    need = s["missing_gb"] or 0; os.makedirs(I.MODELS, exist_ok=True); room = shutil.disk_usage(I.MODELS).free / 1e9
    if room < need + DISK_SPARE_GB: raise HTTPException(507, f"Needs {need} GB plus {DISK_SPARE_GB} GB spare, and the disk has {room:.0f} GB free.")
    miss = [m for m in s["missing"] if str(m.get("url", "")).startswith("https://huggingface.co/")]
    if not miss: raise HTTPException(400, "This template gives no download link for its files.")
    _dl["state"] = {"status": "running", "family": f, "template": tid, "done": 0, "total": len(miss), "file": miss[0]["name"]}
    def work():
        from psn.connectors.net import download
        try:
            for i, m in enumerate(miss):
                _dl["state"].update(done=i, file=m["name"]); typ = (str(m.get("dir") or "other").split("/") or ["other"])[-1]; download(m["url"], os.path.join(I.MODELS, "_complete_pipelines", f, typ, m["name"]))
            _dl["state"].update(status="done", done=len(miss)); I.generate(f, ports=I.registry_ports([f])); scan(True)
        except Exception as e: _dl["state"].update(status="error", error=f"{type(e).__name__}: {str(e)[:200]}")
    threading.Thread(target=work, daemon=True, name="family-download").start(); return _dl["state"]
