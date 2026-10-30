"""Optimize this box: a calibration run. For every goal whose models are installed and whose measured/estimated peak fits in free VRAM (+4 GiB headroom), render one small representative job twice (cold, then warm)
through the studio itself and record seconds and peak VRAM. The result is the box profile the planner and Prime use instead of estimates. Runs only when ComfyUI is idle, one job at a time, and can be cancelled."""
import json, os, subprocess, threading, time, urllib.request
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from studio.goals import GOALS
STATE = Path(os.environ.get("STUDIO_STATE_DIR") or Path.home() / ".local" / "state" / "parametric-studio"); PROFILE = lambda: STATE / "box_profile.json"
SAMPLES = {  # goal -> (prompt, options, estimated peak GiB measured on a 96 GB Blackwell during the contest render window)
 "image": ("a red fox standing in fresh snow at sunrise, soft golden light", {"aspect": "1:1", "mode": "fast"}, 21.8), "anime": ("a girl reading under cherry blossoms, soft light", {"aspect": "1:1", "mode": "fast", "style": "tv"}, 12.7),
 "flux3": ("a ceramic teapot on a wooden table, morning light", {"aspect": "1:1"}, 23.7), "video": ("a paper boat drifting down a small stream, camera slowly pushes in", {"aspect": "16:9", "quality": "480p", "seconds": 2}, 28.2),
 "h3_video": ("a fox walks through snow at sunrise, slow dolly in", {"aspect": "16:9", "quality": "standard", "seconds": 2, "speed": "fast"}, 46.2), "video_ltx": ("a violinist under a bridge at dusk, slow orbit", {"aspect": "16:9", "seconds": 2}, 42.3),
 "music": ("warm acoustic folk, gentle guitar, calm", {"seconds": 30}, 26.7)}
HEADROOM = 4.0; _st = {"running": False, "cancel": False, "log": [], "profile": None}
def gpu_free_gib():
    try: u, t = (float(x) / 1024 for x in subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8).stdout.split(",")); return t - u
    except Exception: return None
def load_profile():
    try: return json.load(open(PROFILE()))
    except Exception: return None
def plan(free, installed):
    """-> [(goal, reason)] ordered smallest first: which goals can be calibrated now."""
    out = []
    for g, (_, _, peak) in sorted(SAMPLES.items(), key=lambda kv: kv[1][2]):
        if g not in installed: out.append((g, "models not installed")); continue
        if free is None or free < peak + HEADROOM: out.append((g, f"needs about {peak + HEADROOM:.0f} GiB free, {0 if free is None else free:.0f} free")); continue
        out.append((g, None))
    return out
def run(post, poll, free_fn=gpu_free_gib, installed=None, sleep=time.sleep, runs=2):
    """post(body)->job id; poll(job)->{'status','seconds',...}. Returns the profile dict."""
    prof = {"created": int(time.time()), "goals": {}}; _st["log"] = []
    for goal, why in plan(free_fn(), installed if installed is not None else set(SAMPLES)):
        if _st["cancel"]: break
        if why: prof["goals"][goal] = {"ok": None, "skipped": why}; _st["log"].append(f"{goal}: skipped ({why})"); continue
        prompt, opts, _ = SAMPLES[goal]; secs = []; ok = True
        for i in range(runs):
            t0 = time.time()
            try:
                job = post({"goal": goal, "prompt": prompt, "options": opts, "seed": 7, "lyrics": ""})
                while True:
                    s = poll(job)
                    if s["status"] == "done": break
                    if s["status"] == "error" or time.time() - t0 > 900: raise RuntimeError(s.get("error") or "timed out")
                    sleep(2)
                secs.append(round(time.time() - t0, 1))
            except Exception as e: ok = False; prof["goals"][goal] = {"ok": False, "error": str(e)[:120]}; break
        if ok: prof["goals"][goal] = {"ok": True, "seconds_cold": secs[0], "seconds_warm": secs[-1], "peak_vram_gib_ref": SAMPLES[goal][2]}; _st["log"].append(f"{goal}: {secs[0]}s cold, {secs[-1]}s warm")
        else: _st["log"].append(f"{goal}: failed")
    STATE.mkdir(parents=True, exist_ok=True); tmp = PROFILE().with_suffix(".tmp"); tmp.write_text(json.dumps(prof, indent=1)); os.replace(tmp, PROFILE()); return prof
def _http(path, body=None):
    base = f"http://127.0.0.1:{os.environ.get('STUDIO_PORT', '8310')}"
    r = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {"Content-Type": "application/json"}); return json.loads(urllib.request.urlopen(r, timeout=30).read())
def comfy_idle():
    try: q = json.load(urllib.request.urlopen(os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200") + "/queue", timeout=4)); return not (q.get("queue_running") or q.get("queue_pending"))
    except Exception: return False
router = APIRouter()
class Go(BaseModel): confirm: bool = False
@router.post("/api/calibrate")
def calibrate_start(b: Go):
    if not b.confirm: raise HTTPException(400, "calibration renders a few small jobs on your GPU: confirm to start")
    if _st["running"]: raise HTTPException(409, "already running")
    if not comfy_idle(): raise HTTPException(409, "ComfyUI is busy: try again when your queue is empty")
    installed = {g for g in SAMPLES if g in GOALS}
    def work():
        _st.update(running=True, cancel=False)
        try: _st["profile"] = run(lambda body: _http("/api/generate", body)["job"], lambda j: _http("/api/jobs/" + j), installed=installed)
        except Exception as e: _st["log"].append(f"error: {str(e)[:100]}")
        _st["running"] = False
    threading.Thread(target=work, daemon=True).start(); return {"started": True}
@router.post("/api/calibrate/cancel")
def calibrate_cancel(): _st["cancel"] = True; return {"ok": True}
@router.get("/api/calibrate")
def calibrate_status(): return {"running": _st["running"], "log": _st["log"][-12:], "profile": _st["profile"] or load_profile()}
