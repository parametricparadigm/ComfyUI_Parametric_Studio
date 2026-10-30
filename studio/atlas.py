"""The Atlas: a dated map of generative AI models, from the first GANs and VAEs to today, with what this studio can run and how well each model has been tested here.
Data lives in atlas_models.json: allow-listed model facts only (name, family, kind, licence, source URL, date, why it mattered, test status). Nothing in it is copied from private notes; tests/test_studio_atlas.py fails on emails, prices, shop ids and local paths.
GET /api/atlas merges the static facts with live ones: which goals exist in this build, which family instances are installed and up, and the renders in web/showcase (measured time and peak VRAM)."""
import json, re, statistics, time
from pathlib import Path
from fastapi import APIRouter
from studio.goals import GOALS

router = APIRouter()
ROOT = Path(__file__).resolve().parent; DATA = ROOT / "atlas_models.json"; SHOWCASE = ROOT / "web" / "showcase" / "showcase.json"
KINDS = ("image", "video", "audio", "3d", "llm"); STATUSES = ("goal", "instance", "missing"); CLASSES = ("open", "community", "noncommercial", "research", "proprietary", "paper", "unverified")
MODEL_FIELDS = {"id", "name", "org", "family", "era", "kinds", "date", "date_precision", "date_basis", "date_verified", "licence", "licence_class", "licence_note", "licence_verified", "source", "what", "why", "featured", "run", "proof", "instance_check"}
COVER_FIELDS = {"name", "kinds", "date", "date_verified", "status", "model", "family", "goals", "in_comfy_lists", "licence", "licence_verified", "source_url", "note"}
TOP_FIELDS = {"version", "built", "about", "instance_check_as_of", "coverage", "coverage_sources", "families_installed", "eras", "models"}
PRIVATE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|/home/|/mnt/|~/|[$€£]\s?\d|\b\d[\d,.]*\s?(?:USD|EUR|GBP)\b|\b(?:USD|EUR|GBP)\s?\d|shop[_ -]?id", re.I)
_cache: dict = {}

def data():
    if "d" not in _cache: _cache["d"] = json.loads(DATA.read_text(encoding="utf8"))
    return _cache["d"]

def showcase():
    try: return json.loads(SHOWCASE.read_text(encoding="utf8"))
    except Exception: return []

def installed():
    """-> {family folder: {port, up}} for the family instances on this machine. Empty on a machine without psn instances (a clean clone)."""
    hit = _cache.get("inst")
    if hit and time.time() - hit[0] < 20: return hit[1]
    out = {}
    try:
        from psn import instances as I
        for f in I.families():
            out[f] = {"port": None, "up": False}
        for r in I.status(): out[r["family"]] = {"port": r["port"], "up": bool(r["up"])}
    except Exception: pass
    _cache["inst"] = (time.time(), out); return out

def renders_for(goal_ids, shots):
    rows = [s for s in shots if s.get("goal") in goal_ids]
    if not rows: return None
    timed = [float(s["seconds"]) for s in rows if s.get("seconds")]; peak = [float(s["peak_vram_gib"]) for s in rows if s.get("peak_vram_gib")]
    vis = next((s for s in rows if s.get("kind") != "audio"), rows[0])
    return {"count": len(rows), "median_seconds": round(statistics.median(timed), 1) if timed else None, "peak_vram_gib": max(peak) if peak else None,
            "media": {"kind": vis.get("kind"), "src": vis.get("src"), "poster": vis.get("poster"), "alt": (vis.get("prompt") or "")[:140]}}

def merge(d=None, goals=None, inst=None, shots=None):
    """Static atlas + live facts. Pure given its inputs, so tests can stub every one of them."""
    d = d or data(); goals = GOALS if goals is None else goals; inst = installed() if inst is None else inst; shots = showcase() if shots is None else shots
    models = []
    for m in d["models"]:
        live_goals = [g for g in m["run"]["goals"] if g in goals]; here = inst.get(m["family"]) if m["family"] else None
        r = renders_for(live_goals, shots) if live_goals else None; p = m["proof"]
        can = "goal" if live_goals else "instance" if here is not None else None
        tested = bool(r) or p.get("tested", 0) > 0
        models.append({**m, "can_run": can, "goals_live": [{"id": g, "label": goals[g]["label"]} for g in live_goals], "instance": {"family": m["family"], "port": here["port"], "up": here["up"]} if here is not None else None,
                       "renders": r, "tested": tested})
    cov = [{**c, "goals_live": [g for g in c["goals"] if g in goals]} for c in d["coverage"]]
    stats = {"models": len(models), "run_here": sum(1 for m in models if m["can_run"]), "tested": sum(1 for m in models if m["tested"]), "rendered_here": sum(1 for m in models if m["renders"]),
             "coverage": {s: sum(1 for c in cov if c["status"] == s) for s in STATUSES}, "families_installed": len(inst) or d["families_installed"]}
    return {**{k: d[k] for k in ("version", "built", "about", "instance_check_as_of", "eras", "coverage_sources", "families_installed")}, "models": models, "coverage": cov, "stats": stats}

def select(models, kind=None, tested=False, runs=False, q=""):
    """The same filters the page applies, kept here so they can be tested."""
    q = (q or "").strip().lower(); out = []
    for m in models:
        if kind and kind != "all" and kind not in m["kinds"]: continue
        if tested and not m.get("tested"): continue
        if runs and not m.get("can_run"): continue
        if q and q not in " ".join(str(m.get(k, "")) for k in ("name", "org", "what", "why", "licence", "family")).lower(): continue
        out.append(m)
    return out

@router.get("/api/atlas")
def atlas(): return merge()
