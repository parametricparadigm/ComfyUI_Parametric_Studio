"""Where a graph runs. Default: the local ComfyUI over its server API. With STUDIO_BACKEND=sdk the same API-format graph goes through Comfy's official SDK (comfy-sdk, Comfy API v2): Comfy Cloud by default, or a Developer Platform deployment or a
self-hosted comfy-api-proxy when COMFY_BASE_URL says so. The key comes from COMFY_API_KEY only and is never stored or sent to the browser. Cloud and deployments spend your Comfy credits; the UI says so."""
import json, mimetypes, os, re, threading, time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()
JOBS: dict = {}
OUT = Path(os.environ.get("STUDIO_SDK_OUTPUT") or Path.home() / ".local" / "share" / "parametric-studio" / "sdk_outputs")

def use_sdk(): return os.environ.get("STUDIO_BACKEND", "local").strip().lower() == "sdk"

def target():
    """{backend, target, base_url, key_set, spends_credits} for the health endpoint. No secret leaves this function."""
    if not use_sdk(): return {"backend": "local", "target": "local", "spends_credits": False}
    base = os.environ.get("COMFY_BASE_URL", "").strip().rstrip("/"); kind = "cloud" if not base or "cloud.comfy.org" in base else "deployment" if ".run.comfy.app" in base else "self-hosted"
    return {"backend": "sdk", "target": kind, "base_url": base or "https://cloud.comfy.org", "key_set": bool(os.environ.get("COMFY_API_KEY")), "spends_credits": kind != "self-hosted"}

def _kind(name, content_type=""):
    t = content_type or mimetypes.guess_type(name)[0] or ""
    return "video" if t.startswith("video") else "audio" if t.startswith("audio") else "image"

def _collect(jid, job):
    """Wait for the job, then pull its outputs next to each other so the studio can serve them like local ones."""
    st = JOBS[jid]
    try:
        job.wait(); d = OUT / re.sub(r"[^\w.-]", "_", jid); d.mkdir(parents=True, exist_ok=True); files = []
        for o in job.outputs:
            if getattr(o, "type", "output") == "temp": continue
            name = os.path.basename(o.name); o.to_file(d / name); files.append({"filename": name, "subfolder": "", "type": "output", "kind": _kind(name, getattr(o, "content_type", "")), "url": f"/api/sdk_output/{jid}/{name}"})
        st.update(status="done", files=files, seconds=round(time.time() - st["started"], 1))
    except Exception as e: st.update(status="error", error=f"{type(e).__name__}: {str(e)[:300]}")

def submit(graph, uploads=(), input_dir=None, meta=None, client=None):
    """Submit an API-format graph. uploads are file names the graph refers to in the local input folder; each becomes an SDK asset, so it is hashed and only sent if the server lacks those bytes."""
    if client is None:
        from comfy_sdk import Comfy
        client = Comfy(client_info="parametric-studio")
    wf = client.workflows.from_json(json.loads(json.dumps(graph)))
    for name in filter(None, uploads):
        path = os.path.join(input_dir or "", os.path.basename(name))
        if not os.path.exists(path): raise FileNotFoundError(f"{name} is not in the input folder")
        asset = client.assets.from_file(path)
        for nid, node in graph.items():
            for field, value in (node.get("inputs") or {}).items():
                if value == name: wf.set_input(nid, field, asset)
    job = client.submit(wf); jid = str(job.id)
    JOBS[jid] = {"status": "running", "started": time.time(), "job": job, "files": [], "client": client, **(meta or {})}
    threading.Thread(target=_collect, args=(jid, job), daemon=True).start()
    return jid

def _public(st): return {k: v for k, v in st.items() if k not in ("job", "client")}
def status(jid):
    st = JOBS[jid]; out = _public(st)
    if st["status"] == "running": out["elapsed"] = round(time.time() - st["started"], 1)
    return out
def cancel(jid):
    try: JOBS[jid]["job"].cancel()
    except Exception: pass
def history():
    return [{"job": j, "files": s["files"], **{k: s[k] for k in ("goal", "prompt", "seed", "options") if k in s}} for j, s in JOBS.items() if s.get("status") == "done" and s["files"]]

@router.get("/api/sdk_output/{jid}/{name}")
def sdk_output(jid: str, name: str):
    if jid not in JOBS or os.path.basename(name) != name or ".." in name: raise HTTPException(404, "no such output")
    p = OUT / re.sub(r"[^\w.-]", "_", jid) / name
    if not p.is_file(): raise HTTPException(404, "no such output")
    return FileResponse(p)
