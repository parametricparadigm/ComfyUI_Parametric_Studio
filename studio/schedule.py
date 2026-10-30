"""Set-and-forget schedules: 'every day at 8, make me a lofi track', 'every Friday, a new wallpaper'. Cron-style timing (APScheduler), stored in ~/.config/parametric-studio/schedules.json, and safe on a shared box:
a job only fires when ComfyUI is idle (never queues behind or on top of your own work), obeys a daily cap, only uses the studio's own goals, and keeps prompts SFW. Results land in the Library like any render."""
import json, os, re, time, uuid, urllib.request
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from studio.goals import GOALS
from studio.sfw import BAD, MESSAGE
CONF = Path(os.environ.get("STUDIO_CONFIG_DIR") or Path.home() / ".config" / "parametric-studio"); FILE = lambda: CONF / "schedules.json"
PRESETS = {"every morning at 8": "0 8 * * *", "every evening at 6": "0 18 * * *", "every hour": "0 * * * *", "every Monday at 9": "0 9 * * 1", "every Friday at 5": "0 17 * * 5", "every weekend morning": "0 9 * * 6,0", "every night at 2": "0 2 * * *"}
_sched = {"s": None}
def load():
    try: return json.load(open(FILE()))
    except Exception: return []
def save(jobs):
    CONF.mkdir(parents=True, exist_ok=True); tmp = FILE().with_suffix(".tmp"); tmp.write_text(json.dumps(jobs, indent=1)); os.replace(tmp, FILE())
def trigger(cron):
    from apscheduler.triggers.cron import CronTrigger
    return CronTrigger.from_crontab(cron)                          # raises ValueError on a bad expression
def validate(d):
    cron = PRESETS.get(str(d.get("cron", "")).strip().lower(), str(d.get("cron", "")).strip())
    try: trigger(cron)
    except Exception: raise ValueError("that schedule is not valid; use a preset or five cron fields like '0 8 * * *'") from None
    if d.get("goal") not in GOALS: raise ValueError("unknown goal")
    if GOALS[d["goal"]]["needs_image"]: raise ValueError("scheduled jobs cannot need an input image")
    prompt = str(d.get("prompt", "")).strip()
    if not 3 <= len(prompt) <= 600: raise ValueError("the prompt needs 3 to 600 characters")
    if BAD.search(prompt) or BAD.search(str(d.get("lyrics", ""))): raise ValueError(MESSAGE)
    return {"name": str(d.get("name") or prompt[:40])[:60], "cron": cron, "goal": d["goal"], "prompt": prompt, "options": d.get("options") or {}, "lyrics": str(d.get("lyrics", ""))[:2000], "max_per_day": max(1, min(int(d.get("max_per_day", 3)), 24)), "enabled": bool(d.get("enabled", True))}
def comfy_idle(base=None):
    try:
        q = json.load(urllib.request.urlopen((base or os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200")) + "/queue", timeout=4)); return not (q.get("queue_running") or q.get("queue_pending"))
    except Exception: return False
def fire(job_id, post=None, idle=None, now=None):
    """Run one scheduled job if allowed. Returns a status string and records it. `post(path, body)` and `idle()` are injectable for tests."""
    jobs = load(); j = next((x for x in jobs if x["id"] == job_id), None)
    if not j: return "missing"
    day = time.strftime("%Y-%m-%d", time.localtime(now or time.time()))
    if j.get("day") != day: j["day"], j["runs_today"] = day, 0
    status = "skipped: not safe-for-work" if BAD.search(str(j.get("prompt", ""))) or BAD.search(str(j.get("lyrics", ""))) else "skipped: paused" if not j["enabled"] else "skipped: daily cap reached" if j["runs_today"] >= j["max_per_day"] else "skipped: busy" if not (idle or comfy_idle)() else None
    if status is None:
        body = {"goal": j["goal"], "prompt": j["prompt"], "options": j["options"], "lyrics": j.get("lyrics", ""), "seed": None}
        try: (post or _post)("/api/generate", body); j["runs_today"] += 1; status = "started"
        except Exception as e: status = f"failed: {str(e)[:80]}"
    j["last_run"], j["last_status"] = int(now or time.time()), status; save(jobs); return status
def _post(path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{os.environ.get('STUDIO_PORT', '8310')}{path}", json.dumps(body).encode(), {"Content-Type": "application/json"}); return json.loads(urllib.request.urlopen(r, timeout=30).read())
def start():
    """Start the background scheduler and register every enabled job (called once at server start)."""
    from apscheduler.schedulers.background import BackgroundScheduler
    if _sched["s"] is None: _sched["s"] = BackgroundScheduler(timezone=time.tzname[0] if False else None); _sched["s"].start()
    sync()
def sync():
    s = _sched["s"]
    if s is None: return
    for j in s.get_jobs(): j.remove()
    for j in load():
        if j["enabled"]: s.add_job(fire, trigger(j["cron"]), args=[j["id"]], id=j["id"], coalesce=True, max_instances=1, misfire_grace_time=600)
router = APIRouter()
class New(BaseModel):
    name: str = ""; cron: str; goal: str; prompt: str; options: dict = {}; lyrics: str = ""; max_per_day: int = 3; enabled: bool = True
@router.get("/api/schedules")
def sched_list(): return {"jobs": load(), "presets": PRESETS}
@router.post("/api/schedules")
def sched_add(b: New):
    try: d = validate(b.model_dump())
    except ValueError as e: raise HTTPException(400, str(e)) from None
    jobs = load()
    if len(jobs) >= 20: raise HTTPException(400, "20 schedules is the limit")
    d.update(id=uuid.uuid4().hex[:8], runs_today=0, day="", last_run=None, last_status="never run"); jobs.append(d); save(jobs); sync(); return d
@router.post("/api/schedules/{sid}/toggle")
def sched_toggle(sid: str):
    jobs = load(); j = next((x for x in jobs if x["id"] == sid), None)
    if not j: raise HTTPException(404, "no such schedule")
    j["enabled"] = not j["enabled"]; save(jobs); sync(); return j
@router.post("/api/schedules/{sid}/run-now")
def sched_run(sid: str): return {"status": fire(sid)}
@router.delete("/api/schedules/{sid}")
def sched_del(sid: str):
    jobs = [x for x in load() if x["id"] != sid]; save(jobs); sync(); return {"ok": True}
