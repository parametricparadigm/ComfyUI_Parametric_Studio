"""Comfy Prime: the studio's conversational guide. The studio is run by agents you talk to: Prime listens (text or voice), answers from the crew's notes, and can DRIVE the studio through a short list of safe actions
(navigate, pick a goal, fill the prompt, open a lesson, remember your name). It never starts a render by itself: 'generate' comes back as a proposal the user confirms. Output is validated against the allowed actions.
Also here: the user profile (name, voice) and the self-tuning log (what each goal really costs on this box), which Prime uses to give honest advice."""
import json, os, re, statistics, time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from studio.goals import GOALS
CONF = Path(os.environ.get("STUDIO_CONFIG_DIR") or Path.home() / ".config" / "parametric-studio"); STATE = Path(os.environ.get("STUDIO_STATE_DIR") or Path.home() / ".local" / "state" / "parametric-studio")
TABS = ["create", "library", "apps", "design", "edit", "university", "models", "crew", "site", "viewer", "pro"]
# ---------- profile
def load_user():
    try: return json.load(open(CONF / "user.json"))
    except Exception: return {}
def save_user(name=None):
    u = load_user()
    if name is not None:
        name = re.sub(r"[^\w .'-]", "", str(name)).strip()[:40]
        if name: u["name"] = name
    CONF.mkdir(parents=True, exist_ok=True); tmp = CONF / "user.json.tmp"; tmp.write_text(json.dumps(u)); os.replace(tmp, CONF / "user.json"); return u
# ---------- self-tuning log
def record(goal, seconds, ok=True, peak_vram_gib=None, options=None, path=None):
    p = Path(path) if path else STATE / "runs.jsonl"; p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f: f.write(json.dumps({"t": int(time.time()), "goal": goal, "seconds": round(float(seconds), 1), "ok": bool(ok), "vram": peak_vram_gib, "options": options or {}}) + "\n")
def summary(path=None, last=200):
    p = Path(path) if path else STATE / "runs.jsonl"
    try: rows = [json.loads(l) for l in open(p).read().splitlines()[-2000:]]
    except Exception: return {}
    out = {}
    for g in {r["goal"] for r in rows}:
        rs = [r for r in rows if r["goal"] == g][-last:]; ok = [r for r in rs if r["ok"]]
        out[g] = {"runs": len(rs), "fail_rate": round(1 - len(ok) / len(rs), 2), "median_s": round(statistics.median([r["seconds"] for r in ok]), 1) if ok else None, "peak_vram_gib": max([r["vram"] for r in ok if r.get("vram")] or [None]) if ok else None}
    return out
def advice(goal, free_vram_gib, stats=None):
    s = (stats or summary()).get(goal)
    if not s: return "No history for this goal yet: the first run teaches the studio how this box behaves."
    if s["peak_vram_gib"] and free_vram_gib is not None and free_vram_gib < s["peak_vram_gib"] + 4: return f"This goal peaked at {s['peak_vram_gib']} GiB here and only {free_vram_gib:.0f} GiB is free: pick the fast mode or a smaller size."
    if s["fail_rate"] >= 0.3 and s["runs"] >= 3: return f"{int(s['fail_rate'] * 100)}% of recent runs failed: check Models for missing files."
    return f"Typical run here: about {s['median_s']} s."
# ---------- conversation
SYSTEM = """You are Comfy Prime, the friendly master guide of Parametric Studio, a local ComfyUI studio. You know ComfyUI deeply, speak warmly and briefly (under 60 words), and use the user's name when you know it.
Reply with ONE JSON object: {"say": str, "actions": [ ... ]}. Allowed actions (use none if unsure):
 {"type":"navigate","tab": one of %s}  {"type":"set_goal","goal": one of %s}  {"type":"set_prompt","text": str (an improved, specific prompt, one camera move at most for video)}
 {"type":"open_course","code":"CU-###"}  {"type":"remember_name","name": str}  {"type":"propose_generate"}  {"type":"ask_crew","question": str}
Never claim a render started: you can only propose it. If the user tells you their name, add remember_name. If a question needs facts about a model, use ask_crew instead of guessing."""
def validate(obj, goals=None, tabs=None):
    goals = set(goals or GOALS); tabs = set(tabs or TABS); say = str(obj.get("say", "")).strip()[:600] if isinstance(obj, dict) else ""; acts = []
    for a in (obj.get("actions") or []) if isinstance(obj, dict) else []:
        if not isinstance(a, dict): continue
        t = a.get("type")
        if t == "navigate" and a.get("tab") in tabs: acts.append({"type": t, "tab": a["tab"]})
        elif t == "set_goal" and a.get("goal") in goals: acts.append({"type": t, "goal": a["goal"]})
        elif t == "set_prompt" and isinstance(a.get("text"), str) and a["text"].strip(): acts.append({"type": t, "text": a["text"].strip()[:600]})
        elif t == "open_course" and re.fullmatch(r"CU-\d{3}", str(a.get("code", ""))): acts.append({"type": t, "code": a["code"]})
        elif t == "remember_name" and isinstance(a.get("name"), str) and a["name"].strip(): acts.append({"type": t, "name": a["name"].strip()[:40]})
        elif t == "ask_crew" and isinstance(a.get("question"), str) and len(a["question"]) > 2: acts.append({"type": t, "question": a["question"][:300]})
        elif t == "propose_generate": acts.append({"type": t})
    return {"say": say or "I'm here. What shall we make?", "actions": acts[:4]}
def converse(text, history, chat, user=None, stats=None, free_vram=None, goal=None):
    name = (user or {}).get("name"); ctx = f"User's name: {name}." if name else "The user's name is not known yet; ask for it kindly once."
    if goal and stats and goal in stats: ctx += " Current goal advice: " + advice(goal, free_vram, stats)
    msgs = [{"role": "system", "content": SYSTEM % (json.dumps(TABS), json.dumps(list(GOALS))) + "\n" + ctx}] + [{"role": h["role"], "content": str(h["text"])[:500]} for h in (history or [])[-6:] if h.get("role") in ("user", "assistant")] + [{"role": "user", "content": text[:800]}]
    raw = chat(msgs); m = re.search(r"\{.*\}", raw or "", re.S)
    try: obj = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError: obj = {}
    return validate(obj)
router = APIRouter()
class Say(BaseModel): text: str; history: list = []; goal: str = ""
class Who(BaseModel): name: str
@router.get("/api/user")
def user_get(): return load_user()
@router.post("/api/user")
def user_set(b: Who): return save_user(b.name)
@router.get("/api/tuning")
def tuning(): return {"goals": summary()}
@router.post("/api/prime")
def prime(b: Say):
    if not (1 <= len(b.text.strip()) <= 800): raise HTTPException(400, "say something short")
    from studio import crew
    free = None
    try:
        import json as _j, urllib.request as _u
        d = _j.load(_u.urlopen(os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200") + "/system_stats", timeout=3))["devices"][0]; free = d["vram_free"] / 2**30
    except Exception: pass
    try: return converse(b.text, b.history, crew.default_chat, load_user(), summary(), free, b.goal or None)
    except Exception as e: raise HTTPException(503, "Prime can't reach the language model right now (it may be asleep while the GPU is busy)") from None
