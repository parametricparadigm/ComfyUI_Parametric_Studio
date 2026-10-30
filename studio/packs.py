"""Designer packs: product, vehicle, setting, animal, plant, hair, nail, furniture and costume designers whose option lists come from the owner's own designer modules. A pack lists option groups and views;
compose() turns the user's picks into one clear prompt (originals only: no brands, logos or readable text unless the exact words are given). Generation itself is the ordinary /api/generate path."""
import json, os, re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packs", "packs.json")
TAIL = "Original design: no real brand names, logos, badges or watermarks, and no readable text except the exact words given."
APPAREL = {"tshirt", "mug", "printify"}
_cache = {}
# The print-on-demand module kept its views as an option group called swap_views, so the pack listed 0 views and had no sheet. They are lifted into views here, with a few generic views added so it has a sheet like the others.
LIFTED = {"mockup on the product, front": "Print-on-demand product mockup: the design printed on the product, seen from the front on a clean studio backdrop", "flat lay mockup": "Flat-lay print-on-demand mockup: the product with the design printed on it, on a plain surface seen from above",
          "close-up of the printed artwork": "Close photograph of the printed artwork on the product, the print texture visible", "product catalogue shot": "Product catalogue photograph of the product with the design printed on it, soft studio light",
          "lifestyle scene, product in use": "Lifestyle photograph of the product in everyday use, natural light, no face shown", "print-ready artwork on a plain background": "The print-ready artwork alone, centred on a plain flat background, no product"}
def _norm(p):
    if not p.get("views"):
        sv = next((g for g in p["groups"] if g["id"].endswith("views")), None)
        if sv: p["views"] = list(sv.get("options") or []) + [v for v in LIFTED if v not in (sv.get("options") or [])]; p["groups"] = [g for g in p["groups"] if g is not sv]
    p.setdefault("view_words", {})
    for v in p["views"]: p["view_words"].setdefault(v, LIFTED.get(v, v))
    return p
def load():
    if "d" not in _cache: _cache["d"] = {k: _norm(p) for k, p in json.load(open(FILE))["packs"].items()}
    return _cache["d"]
def _opts(g): return g.get("options") or [o for v in g.get("categories", {}).values() for o in v]
FIRST = ("character", "fashion", "vehicle")      # the first three tiles on the Designers page
def summary(): return [{"id": p["id"], "label": p["label"], "doc": p["doc"], "groups": len(p["groups"]), "views": len(p["views"])} for p in sorted(load().values(), key=lambda p: FIRST.index(p["id"]) if p["id"] in FIRST else len(FIRST))]
def compose(pack_id, choices, idea="", view="", words=""):
    p = load().get(pack_id)
    if not p: raise KeyError(pack_id)
    parts = []; allowed = {g["id"]: set(_opts(g)) for g in p["groups"]}; labels = {g["id"]: g["label"].lower() for g in p["groups"]}
    for gid, val in (choices or {}).items():
        if gid not in allowed or not val: continue
        if val not in allowed[gid]: raise ValueError(f"'{val}' is not an option of {gid}")
        parts.append(val if gid == "kinds" else f"{labels[gid]}: {val}")
    head = (p["view_words"].get(view) or view or "").strip()
    if view and view not in p["views"] and view not in p["view_words"]: raise ValueError("unknown view")
    subject = ", ".join(x for x in [str(idea or "").strip()[:300]] + parts if x)
    if pack_id in APPAREL and words.strip(): subject += f'. The text reads exactly: "{words.strip()[:80]}"'
    lead = [head.replace("{subject}", subject or "the subject") + ("" if head.endswith(".") else ".")] if "{subject}" in head else [head + ("." if head and not head.endswith(".") else ""), subject + "."]   # plant and animal views carry a {subject} slot
    return " ".join(x for x in lead + [TAIL] if x.strip(". "))
router = APIRouter()
class Compose(BaseModel):
    choices: dict = {}; idea: str = ""; view: str = ""; words: str = ""
@router.get("/api/packs")
def packs_list(): return {"packs": summary()}
@router.get("/api/packs/{pack_id}")
def packs_get(pack_id: str):
    p = load().get(pack_id)
    if not p: raise HTTPException(404, "no such designer")
    return p
@router.post("/api/packs/{pack_id}/compose")
def packs_compose(pack_id: str, b: Compose):
    try: return {"prompt": compose(pack_id, b.choices, b.idea, b.view, b.words)}
    except KeyError: raise HTTPException(404, "no such designer") from None
    except ValueError as e: raise HTTPException(400, str(e)) from None
