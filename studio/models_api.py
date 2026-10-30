"""Models: what every goal and AI-edit tool needs, whether this machine has it, and one-press downloads of only what is missing.
Readiness reads studio/models_manifest.json (the files each goal needs, from Hugging Face) and the edit templates' own model links, and checks them against what ComfyUI reports as installed through studio.apps.resolve (names.resolve_names), so a file kept in a sub-folder is not 'missing'.
Downloads use huggingface_hub: resumable, one at a time, only the missing files, into the ComfyUI models folder ($STUDIO_MODELS_ROOT), refused unless the disk keeps the need plus 25 GB free. A gated repo needs the user to accept the licence on the model page and log in with the hub's own login: the studio never sees a token."""
import hashlib, json, os, re, shutil, sys, threading, time, urllib.parse, urllib.request
from collections import deque
from pathlib import Path
from psn import paths
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from studio import apps as A, attach as AT, edits as E
from studio.goals import GOALS, WF
GB = 2**30; RESERVE = 25 * GB; HERE = Path(__file__).resolve().parent; router = APIRouter(); _M = {}
ROLE = {"unet": ("UNETLoader", "unet_name"), "text_encoder": ("CLIPLoader", "clip_name"), "vae": ("VAELoader", "vae_name"), "audio_vae": ("VAELoader", "vae_name"), "lora": ("LoraLoaderModelOnly", "lora_name")}
class Cancelled(Exception): pass
def root(): return Path(paths.models_root(True))
def manifest():
    if "m" not in _M: _M["m"] = json.load(open(HERE / "models_manifest.json"))["goals"]
    return _M["m"]
def state_dir(): return Path(os.environ.get("STUDIO_STATE_DIR") or Path.home() / ".local" / "state" / "parametric-studio")
def gb(n): return round((n or 0) / GB, 2)
def parse_hf(url):
    u = urllib.parse.urlparse(url or ""); p = u.path.strip("/").split("/")
    return {"repo": "/".join(p[:2]), "rev": urllib.parse.unquote(p[3]), "path": urllib.parse.unquote("/".join(p[4:]))} if u.netloc == "huggingface.co" and len(p) >= 5 and p[2] == "resolve" else None
def free_bytes(path):
    p = Path(path)
    while not p.exists() and p != p.parent: p = p.parent
    return shutil.disk_usage(p).free
def hf_sizes(items):
    """[(repo, rev, path)] -> {(repo, rev, path): (bytes, sha256 or None)} from the hub's metadata (no download)."""
    from huggingface_hub import HfApi
    by, out = {}, {}
    for r, v, p in items: by.setdefault((r, v), []).append(p)
    for (r, v), ps in by.items():
        for x in HfApi().get_paths_info(r, ps, revision=v): out[(r, v, x.path)] = (x.size, x.lfs.sha256 if getattr(x, "lfs", None) else None)
    return out
def sizes():
    if "s" not in _M:
        try: _M["s"] = json.load(open(state_dir() / "hf_sizes.json"))
        except Exception: _M["s"] = {}
    return _M["s"]
def fill_sizes(files, wait=False):
    """Fill sizes the manifest does not carry (edit templates only link files) from the hub's metadata, cached on disk. wait=False looks them up in the background and returns at once."""
    key = lambda f: f"{f['repo']}@{f['rev']}:{f['path']}"
    def apply():
        for f in files:
            if f.get("repo") and f["size"] is None and key(f) in sizes(): f["size"], f["sha"] = sizes()[key(f)]
    apply(); todo = [f for f in files if f.get("repo") and f["size"] is None]
    if not todo: return
    def run():
        try:
            got = hf_sizes([(f["repo"], f["rev"], f["path"]) for f in todo])
            for (r, v, p), (n, sha) in got.items(): sizes()[f"{r}@{v}:{p}"] = [n, sha]
            state_dir().mkdir(parents=True, exist_ok=True); json.dump(sizes(), open(state_dir() / "hf_sizes.json", "w")); _M.pop("err", None)
        except Exception as e: _M["err"] = f"{type(e).__name__}: {str(e)[:100]}"; raise
    if wait: run()
    elif not _M.get("sizing"):
        def bg():
            try: run()
            except Exception: pass
            _M["sizing"] = False
        _M["sizing"] = True; threading.Thread(target=bg, daemon=True).start()
    apply()
def installed(f, oi, r):
    if (r / f["dest"]).exists(): return True
    cls, inp = ROLE.get(f["role"], ("UNETLoader", "unet_name")); opts = A.options_of(oi, cls, inp) if oi else None
    if opts is None: return False
    g, _ = A.resolve({"1": {"class_type": cls, "inputs": {inp: f["name"]}}}, oi); return g["1"]["inputs"][inp] in opts
def summary(kind, id, files, **extra):
    miss = [f for f in files if not f["present"]]; dl = [f for f in miss if f.get("repo")]
    return {"id": id, "kind": kind, "known": True, "ready": not miss, "files": len(files), "missing": len(miss), "downloadable": len(dl), "manual": [f["name"] for f in miss if not f.get("repo")],
            "total_gb": gb(sum(f["size"] for f in files)) if all(f["size"] is not None for f in files) else None, "missing_gb": gb(sum(f["size"] or 0 for f in miss)), "unknown_sizes": sum(1 for f in dl if f["size"] is None),
            "gated": any(f["gated"] for f in miss), "license_url": next((f"https://huggingface.co/{f['repo']}" for f in miss if f["gated"]), None),
            "items": [{"name": f["name"], "role": f["role"], "size_gb": gb(f["size"]) if f["size"] else None, "present": f["present"], "gated": f["gated"], "repo": f.get("repo")} for f in files], **extra}
def goal_files(gid, oi, r):
    m = manifest().get(gid)
    if not m: return None, ""
    fs = [{"name": Path(x["dest"]).name, "role": x["role"], "repo": x["repo"], "path": x["path"], "rev": "main", "dest": x["dest"], "size": int(x["size_gb"] * GB), "sha": x.get("sha256") or None, "gated": bool(x.get("gated"))} for x in m["files"]]
    for f in fs: f["present"] = installed(f, oi, r)
    return fs, m.get("note", "")
def edit_files(tid, oi):
    t, p = E._find(tid); d = A.describe(tid, p, oi); fs = []
    for n in d["models"]:
        h = d["hints"].get(n) or {}; hf = parse_hf(h.get("url")) or {}
        fs.append({"name": n, "role": (h.get("directory") or "model").rstrip("s"), "repo": hf.get("repo"), "path": hf.get("path"), "rev": hf.get("rev", "main"), "dest": f"{h.get('directory') or 'other'}/{n}", "size": None, "sha": None, "gated": False, "present": n not in d["missing_models"]})
    return fs, d
def target(b, oi, r):
    if b.goal:
        if b.goal not in GOALS: raise HTTPException(400, "unknown goal")
        fs, _ = goal_files(b.goal, oi, r)
        if fs is None: raise HTTPException(409, "the manifest does not list this goal's files yet")
        return "goal", b.goal, fs
    if b.edit:
        if not oi: raise HTTPException(503, "ComfyUI is not reachable")
        try: fs, _ = edit_files(b.edit, oi)
        except HTTPException: raise HTTPException(400, "unknown edit tool") from None
        return "edit", b.edit, fs
    raise HTTPException(400, "say which goal or edit tool to download")
def readiness():
    r = root()
    try: oi = A.object_info()
    except Exception: oi = None
    goals, edits = {}, {}
    for gid in GOALS:
        fs, note = goal_files(gid, oi, r); goals[gid] = summary("goal", gid, fs, note=note) if fs is not None else {"id": gid, "kind": "goal", "known": False}
    rows = []
    for t in (E.TOOLS if oi else []):
        try: rows.append((t[0], *edit_files(t[0], oi)))
        except Exception as e: edits[t[0]] = {"id": t[0], "kind": "edit", "known": False, "error": str(e)[:100]}
    fill_sizes([f for _, fs, _ in rows for f in fs if not f["present"]])          # one background lookup for every missing file of every tool
    for tid, fs, d in rows: edits[tid] = summary("edit", tid, fs, needs_nodes=d["unknown_nodes"], runnable=d["runnable"])
    for e in edits.values():
        if e.get("known") and e["unknown_sizes"]: e["sizes_pending"] = True
    return {"root": str(r), "root_ok": r.is_dir(), "free_gb": gb(free_bytes(r)) if r.exists() or r.parent.exists() else None, "reserve_gb": RESERVE // GB, "comfy": oi is not None, "goals": goals, "edits": edits, "size_error": _M.get("err")}
@router.get("/api/models/readiness")
def get_readiness():
    hit = _M.get("ready")
    if hit and time.time() - hit[0] < 5: return {**hit[1], "download": status()}
    out = readiness(); _M["ready"] = (time.time(), out); return {**out, "download": status()}
# ---------- downloads: one at a time
_DL = {"state": "idle"}; _LOCK = threading.Lock(); _CANCEL = threading.Event(); _SAMP = deque(maxlen=16)
def status():
    s = dict(_DL)
    if s["state"] in ("running", "cancelling"):
        got = s.get("done", 0) + s.get("cur", 0); tot = s.get("total", 0); s["bytes"] = got; s["pct"] = round(100 * got / tot, 1) if tot else None
        if len(_SAMP) > 2 and _SAMP[-1][0] > _SAMP[0][0]: sp = (_SAMP[-1][1] - _SAMP[0][1]) / (_SAMP[-1][0] - _SAMP[0][0]); s["mb_s"] = round(sp / 2**20, 1); s["eta_s"] = round((tot - got) / sp) if sp > 0 and tot else None
    return s
def on_bytes(n, reset=False):
    _DL["cur"] = n if reset else _DL.get("cur", 0) + n; now = time.time()
    if not _SAMP or now - _SAMP[-1][0] > 0.5: _SAMP.append((now, _DL.get("done", 0) + _DL["cur"]))
def hf_download(f, stage, progress, cancelled):
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import tqdm as T
    class Bar(T):
        def __init__(self, *a, **k):
            k["file"] = open(os.devnull, "w"); super().__init__(*a, **k)
            if k.get("unit") == "B" and k.get("initial"): progress(k["initial"], reset=True)
        def update(self, n=1):
            if cancelled(): raise Cancelled()
            if getattr(self, "unit", "") == "B": progress(n)
            return super().update(n)
    return hf_hub_download(repo_id=f["repo"], filename=f["path"], revision=f["rev"], local_dir=str(stage), tqdm_class=Bar)
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(8 << 20), b""): h.update(c)
    return h.hexdigest()
def explain(e, f):
    code = getattr(getattr(e, "response", None), "status_code", None)
    if type(e).__name__ == "GatedRepoError" or code in (401, 403):
        url = f"https://huggingface.co/{f['repo']}"
        return {"state": "needs_license", "license_url": url, "error": f"{f['repo']} is gated. Open {url}, accept the licence while signed in to Hugging Face, then log in on this machine with `hf auth login` (the studio never asks for or stores your token) and press Download again."}
    return {"state": "error", "error": f"{type(e).__name__}: {str(e)[:240]}"}
def work(files, r):
    f = None
    try:
        for i, f in enumerate(files):
            if _CANCEL.is_set(): raise Cancelled()
            dest = r / f["dest"]; dest.parent.mkdir(parents=True, exist_ok=True); _DL.update(file=f["name"], index=i + 1, cur=0, phase="downloading")
            if dest.exists(): _DL["done"] += f["size"] or 0; continue
            stage = dest.parent / ".psn_part" / f["repo"].replace("/", "__"); got = hf_download(f, stage, on_bytes, _CANCEL.is_set)
            if f.get("sha") and re.fullmatch(r"[0-9a-f]{64}", f["sha"]):
                _DL["phase"] = "verifying"
                if sha256_file(got) != f["sha"]: os.remove(got); raise ValueError(f"checksum mismatch for {f['name']}; the bad copy was removed, press Download to fetch it again")
            os.replace(got, dest); _DL["done"] += f["size"] or dest.stat().st_size; _DL["cur"] = 0; shutil.rmtree(stage, ignore_errors=True)    # the staging folder is ours
        _DL.update(state="done", phase="", finished=time.time())
    except Cancelled: _DL.update(state="cancelled", phase="", finished=time.time())
    except Exception as e: _DL.update(**explain(e, f or {"repo": "the repository"}), phase="", finished=time.time())
    finally: _M.pop("ready", None); A._oi["d"] = None; _SAMP.clear()      # ComfyUI rescans its folders on the next /object_info
class Body(BaseModel): goal: str = ""; edit: str = ""
@router.post("/api/models/download")
def download(b: Body):
    if os.environ.get("STUDIO_ALLOW_DOWNLOAD", "1") != "1": raise HTTPException(403, "downloads are switched off on this server")
    r = root()
    try: oi = A.object_info()
    except Exception: oi = None
    kind, id, fs = target(b, oi, r); miss = [f for f in fs if not f["present"]]; dl = [f for f in miss if f.get("repo")]
    if not miss: return {"started": False, "message": "everything for this is already installed"}
    if not dl: raise HTTPException(409, "no download source is known for: " + ", ".join(f["name"] for f in miss))
    with _LOCK:
        if _DL.get("state") in ("running", "cancelling"): raise HTTPException(409, "a download is already running: wait for it or cancel it first")
        try: fill_sizes(dl, wait=True)
        except Exception as e: raise HTTPException(502, f"could not reach Hugging Face to check file sizes: {type(e).__name__}") from None
        by = {}
        for f in dl:
            d = (r / f["dest"]).parent; p = d
            while not p.exists() and p != p.parent: p = p.parent
            by.setdefault(os.stat(p).st_dev, [d, 0])[1] += f["size"] or 0
        for d, need in by.values():
            free = free_bytes(d)
            if free < need + RESERVE: raise HTTPException(507, f"not enough disk space: {gb(need)} GB to download plus {RESERVE // GB} GB kept free needs {gb(need + RESERVE)} GB, and {gb(free)} GB is free where {d} lives")
        _CANCEL.clear(); _SAMP.clear(); _DL.clear(); _DL.update(state="running", kind=kind, id=id, count=len(dl), index=0, file="", done=0, cur=0, total=sum(f["size"] or 0 for f in dl), phase="starting", started=time.time())
        threading.Thread(target=work, args=(dl, r), daemon=True).start()
    return {"started": True, "files": len(dl), "need_gb": gb(sum(f["size"] or 0 for f in dl))}
@router.get("/api/models/download")
def download_status(): return status()
@router.post("/api/models/download/cancel")
def download_cancel():
    if _DL.get("state") == "running": _CANCEL.set(); _DL["state"] = "cancelling"
    return status()
# ---------- attach another ComfyUI: test it, show its GPU and node count and what it lacks, switch the studio to it. The URL is kept server-side by studio/attach.py (mode 600); the browser never holds a secret.
DEFAULT_ATTACH = "http://127.0.0.1:8188"; ORIGINAL = {"url": A.COMFY}
def fetch_json(url, timeout): return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "psn-studio"}), timeout=timeout))
def probe(url):
    url = (url or "").strip().rstrip("/"); AT._validate_url(url)        # ValueError: http(s) only, loopback or private LAN unless STUDIO_ALLOW_REMOTE=1
    try: st = fetch_json(url + "/system_stats", 8); oi = fetch_json(url + "/object_info", 60)
    except Exception as e: return {"ok": False, "url": url, "error": f"could not read a ComfyUI at {url} ({type(e).__name__})"}
    d = (st.get("devices") or [{}])[0]; goals = []
    for gid, g in GOALS.items():
        fs, _ = goal_files(gid, oi, Path("/nonexistent")); row = {"goal": gid, "label": g["label"], "missing_models": [f["name"] for f in fs if not f["present"]] if fs else [], "missing_gb": gb(sum(f["size"] for f in fs if not f["present"])) if fs else 0}
        try: row["missing_nodes"] = sorted({n["class_type"] for n in json.load(open(os.path.join(WF, g["template"]))).values()} - set(oi))
        except Exception: row["missing_nodes"] = []
        goals.append(row)
    return {"ok": True, "url": url, "version": (st.get("system") or {}).get("comfyui_version"), "gpu": {"name": d.get("name"), "vram_total_gb": gb(d.get("vram_total")), "vram_free_gb": gb(d.get("vram_free"))}, "nodes": len(oi), "goals": goals, "ready_goals": sum(1 for r in goals if not r["missing_models"] and not r["missing_nodes"])}
def switch(url):
    """Point every studio module at another ComfyUI without a restart (server.py and apps.py hold COMFY; calibrate, prime and schedule read the environment)."""
    url = url.rstrip("/"); os.environ["COMFYUI_URL"] = url
    for m in list(sys.modules.values()):
        if str(getattr(m, "__file__", "") or "").startswith(str(HERE)) and hasattr(m, "COMFY"): m.COMFY = url
    A._oi["d"] = None; _M.pop("ready", None)
try:
    if "COMFYUI_URL" not in os.environ and AT.load().get("comfy_url"): switch(AT.load()["comfy_url"])      # a URL saved in an earlier session wins unless the environment names one
except Exception: pass
class AttachBody(BaseModel): url: str
@router.get("/api/models/attach")
def attach_get(): return {"url": A.COMFY, "default_url": DEFAULT_ATTACH, "original_url": ORIGINAL["url"], "saved": AT.load().get("comfy_url")}
@router.post("/api/models/attach/test")
def attach_test(b: AttachBody):
    try: return probe(b.url)
    except ValueError as e: raise HTTPException(400, str(e)) from None
@router.post("/api/models/attach")
def attach_use(b: AttachBody):
    r = attach_test(b)
    if not r["ok"]: raise HTTPException(502, r["error"])
    AT.save(comfy_url=r["url"]); switch(r["url"]); return {**r, "switched": True}
@router.post("/api/models/attach/reset")
def attach_reset(): AT.save(comfy_url=ORIGINAL["url"]); switch(ORIGINAL["url"]); return attach_get()
