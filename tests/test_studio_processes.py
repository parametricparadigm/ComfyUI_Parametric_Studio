"""Processes page: the generated data, the cleaned docs and the API. No live ports, no accounts."""
import importlib.util, json
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import processes as P, sfw

ROOT = Path(__file__).resolve().parent.parent; STUDIO = ROOT / "studio"
_spec = importlib.util.spec_from_file_location("build_processes", ROOT / "scripts" / "build_processes.py"); B = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(B)
DATA = json.load(open(STUDIO / "processes.json", encoding="utf-8")); ROWS = DATA["processes"]; BY_ID = {r["id"]: r for r in ROWS}

@pytest.fixture
def client():
    app = FastAPI(); app.include_router(P.router); return TestClient(app)

def test_every_card_is_complete():
    assert len(ROWS) >= 90 and len(BY_ID) == len(ROWS)
    for r in ROWS:
        assert r["name"] and r["description"] and r["kind"] in DATA["kinds"] and r["status"] in DATA["status_labels"] and isinstance(r["models"], list), r["id"]
        assert r["open"] or r["doc"], f"{r['id']} has nothing to open"

def test_docs_match_the_cards_with_no_orphans():
    names = {p.stem for p in (STUDIO / "processes").glob("*.md")}
    assert names == {r["id"] for r in ROWS if r["doc"]}

def test_every_doc_and_card_passes_the_scan():
    for p in (STUDIO / "processes").glob("*.md"):
        t = p.read_text(encoding="utf-8")
        assert B.verify_text(t) == [] and not sfw.flagged(t), p.name
    for r in ROWS:
        t = " ".join([r["name"], r["description"], r["status_note"], *r["models"]])
        assert B.verify_text(t) == [] and not sfw.flagged(t), r["id"]

def test_tested_here_needs_a_real_render_through_the_same_goal():
    shown = {x["goal"] for x in json.load(open(STUDIO / "web" / "showcase" / "showcase.json", encoding="utf-8"))}
    here = [r for r in ROWS if r["status"] == "here"]
    assert here
    for r in here: assert r["open"]["type"] == "goal" and not r["open"]["near"] and r["open"]["id"] in shown, r["id"]

def test_open_targets_exist():
    goals = (STUDIO / "goals.py").read_text(encoding="utf-8"); recipes = {x["id"] for x in json.load(open(STUDIO / "recipes.json", encoding="utf-8"))["recipes"]} if isinstance(json.load(open(STUDIO / "recipes.json", encoding="utf-8")), dict) else {x["id"] for x in json.load(open(STUDIO / "recipes.json", encoding="utf-8"))}
    packs = (STUDIO / "packs" / "packs.json").read_text(encoding="utf-8")
    for r in ROWS:
        o = r["open"]
        if not o: continue
        assert o["type"] in ("goal", "recipe", "designer", "edit", "family"), r["id"]
        if o["type"] == "goal": assert f'"{o["id"]}"' in goals, r["id"]
        if o["type"] == "recipe": assert o["id"] in recipes, r["id"]
        if o["type"] == "designer": assert f'"{o["id"]}"' in packs, r["id"]

def test_cleaner_drops_private_lines_and_rewrites_the_rest():
    assert B.clean_line("write to someone@example.com")[0] is None
    assert B.clean_line("costs $12 a month")[0] is None
    assert B.clean_line("see https://example.com/a")[0] is None
    assert B.clean_line("the model on https://huggingface.co/a/b")[0]
    box = "/" + "home" + "/"
    assert box not in B.clean_line("run " + box + "someone/x.py now")[0]
    assert "tiktok" not in B.clean_line("Loud enough for TikTok")[0].lower()
    assert B.verify_text("a clean line about depth maps") == []
    assert B.verify_text("the file at /mnt/data/x") == ["local"]

def test_api_lists_and_serves_docs(client):
    d = client.get("/api/processes").json(); assert len(d["processes"]) == len(ROWS) and d["kinds"]
    pid = next(r["id"] for r in ROWS if r["doc"]); x = client.get(f"/api/processes/{pid}/doc").json(); assert x["id"] == pid and x["markdown"].startswith("# ")
    assert client.get("/api/processes/not-a-process/doc").status_code == 404
    assert client.get("/api/processes/BAD_ID/doc").status_code == 400
    out = next((r["id"] for r in ROWS if not r["doc"]), None)
    if out: assert client.get(f"/api/processes/{out}/doc").status_code == 404

def test_near_links_are_real_processes_and_family_pages():
    from studio.processes import NEAR, load
    assert set(NEAR) <= set(BY_ID) and not any(BY_ID[k]["open"] for k in NEAR)
    rows = {p["id"]: p for p in load()["processes"]}
    for k, (slug, label) in NEAR.items(): assert rows[k]["open"] == {"type": "family", "id": slug, "label": label, "near": True}

def test_family_graphs_list_is_flat_and_complete():
    from studio.families_api import family_graphs, status_data
    rows = family_graphs()["graphs"]
    assert len(rows) == sum(len(r.get("templates") or []) for r in status_data()["families"].values())
    assert rows and all(x["slug"] and x["name"] and x["title"] for x in rows)
