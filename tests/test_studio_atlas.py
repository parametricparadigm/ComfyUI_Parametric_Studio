"""Atlas data and API. Data checks read the shipped studio/atlas_models.json; live facts (goals, installed families, showcase renders) are stubbed, so nothing here touches a port, an account or the model folders."""
import json, re
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import atlas as A
from studio.goals import GOALS

RAW = A.DATA.read_text(encoding="utf8"); D = json.loads(RAW)
FAMILIES_82 = ["ACE-Step-1.5", "Allegro", "Anima", "Boogu", "CogVideoX", "Cosmos", "DreamX-Creator", "Ernie-Image", "FitDiT", "FlashVSR-v1.1", "Flux-Kontext", "Flux.1", "Flux.2", "Flux.3-Klein", "HY-Motion", "HiDream", "Hunyuan3D-2.1", "HunyuanDiT-1.2", "HunyuanVideo", "HunyuanWorld", "IP-Adapter", "Ideogram4", "InstantMesh", "Iris-3B", "JoyAI-Video-Edit", "Kandinsky-5.0-T2I-Lite", "Kolors", "Krea2", "LDM3D-4C", "LTX-2.5", "LongCat-Avatar-15", "LongCat-Image", "Lumina-2", "MIDI-3D", "MOVA", "Matrix-3D", "Matrix-Game-2", "Ming-Image", "Mini-Max-Music3", "MiniMax-H3", "Mochi", "Moss-Image", "Omnigen-2", "Ovis-Image", "PartCrafter", "PixArt-Sigma", "Pixal3D", "PixelDiT", "Prism-Alpha", "Qwen-Image-2.1", "SAM-3D-Objects", "SANA-Video", "SD15", "SD3-SD3.5", "SDXL", "SVD", "SeFi-Image-2B-turbo", "SeedVR2", "Shap-E", "Stable-Cascade", "Stable-Fast-3D", "TRELLIS-2-4B", "TripoSR", "TurboWan2.2-I2V", "UniRig", "VLM", "Wan-SCAIL-2", "Wan2.1", "Wan2.2", "Wan2.2-Animate", "Wan2.2-Dancer", "Z-Image", "colorization", "dwpose", "face", "frame_interpolation", "greyscale_to_rgba", "instantCharacter", "rife", "sam3", "upscale_models", "yue2"]

def test_no_private_data_in_the_shipped_json():
    hits = A.PRIVATE.findall(RAW) + re.findall(r"localhost|127\.0\.0\.1|:\d{4}\b|\\\\Users\\\\|C:\\\\", RAW)
    assert hits == []

def test_the_private_data_detector_is_not_vacuous():
    for bad in ("mail me at someone@example.com", "sold for $12", "EUR 40 per gig", "shop_" + "id 00000000", "see /home/user/notes", "in /" + "mnt/fast/models", "~/orn_work/x", "Shop " + "ID: 1"):
        assert A.PRIVATE.search(bad), bad
    for ok in ("MIT", "Apache-2.0", "FLUX.1 [dev] Non-Commercial License", "arXiv 2307.01952", "5.6B parameters"):
        assert not A.PRIVATE.search(ok), ok

def test_only_allow_listed_fields():
    assert set(D) == A.TOP_FIELDS
    for m in D["models"]: assert set(m) == A.MODEL_FIELDS, m["id"]
    for c in D["coverage"]: assert set(c) == A.COVER_FIELDS, c["name"]
    for m in D["models"]:
        assert set(m["source"]) == {"title", "url"} and set(m["run"]) == {"goals"} and set(m["proof"]) == {"tested", "mixed", "untested", "unknown"}

def test_model_records_are_well_formed():
    ids = [m["id"] for m in D["models"]]; assert len(ids) == len(set(ids)) and len(ids) >= 120
    eras = {e["id"] for e in D["eras"]}; assert len(eras) == 8
    for m in D["models"]:
        assert m["era"] in eras and m["kinds"] and set(m["kinds"]) <= set(A.KINDS) and m["licence_class"] in A.CLASSES, m["id"]
        assert m["what"] and m["name"] and (m["why"] or not m["featured"]), m["id"]
        if m["date"]: assert re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", m["date"]) and m["date_precision"] == ("day" if len(m["date"]) == 10 else "month"), m["id"]
        if m["date_verified"]: assert m["date"] and m["date_basis"], m["id"]
        if m["date_verified"] or m["licence_verified"]: assert m["source"]["url"].startswith("https://"), m["id"]
        for g in m["run"]["goals"]: assert g in GOALS, (m["id"], g)
    for e in D["eras"]: assert e["source"]["url"].startswith("https://") and e["from"] <= e["to"], e["id"]
    dates = [m["date"] for m in D["models"] if m["date"]]; assert dates == sorted(dates)
    for m in D["models"]:
        if m["date"]: assert next(e for e in D["eras"] if e["id"] == m["era"])["from"] <= int(m["date"][:4]) <= next(e for e in D["eras"] if e["id"] == m["era"])["to"], m["id"]

def test_unverified_things_are_marked_not_dropped():
    un = [m for m in D["models"] if not m["licence_verified"] or not m["date_verified"]]; assert un
    for m in un:
        if not m["licence_verified"]: assert m["licence_class"] == "unverified" or "not verified" in m["licence"].lower() or "unverified" in m["licence"].lower(), m["id"]
        if not m["date_verified"] and not m["date"]: assert m["date_basis"] == "Date not verified here", m["id"]

def test_every_installed_family_has_an_entry_and_minimax_h3_stays():
    have = {m["family"] for m in D["models"] if m["family"]}
    assert set(FAMILIES_82) - have == set(), sorted(set(FAMILIES_82) - have)
    h3 = next(m for m in D["models"] if m["id"] == "minimax-h3")
    assert h3["family"] == "MiniMax-H3" and set(h3["run"]["goals"]) >= {"h3_video", "h3_animate", "recast"} and "Excluded" not in h3["licence"] and "United States" in h3["licence_note"] and h3["licence_verified"]
    for g in ("image", "flux3", "video_ltx", "music", "anime", "video"): assert any(g in m["run"]["goals"] for m in D["models"]), g

def test_every_family_folder_on_this_machine_has_an_entry():
    try:
        from psn import instances as I; fams = I.families()
    except Exception: pytest.skip("no model folders on this machine")
    have = {m["family"] for m in D["models"] if m["family"]}; assert set(fams) - have == set()

def test_eras_cover_the_story():
    names = " ".join(m["name"] + " " + m["what"] for m in D["models"]).lower()
    for k in ("gan", "vae", "ddpm", "latent diffusion", "controlnet", "sdxl", "flux", "wan", "sora", "stable diffusion 1.x"): assert k in names, k
    assert min(m["date"] for m in D["models"] if m["date"]) == "2013-12-20" and max(m["date"] for m in D["models"] if m["date"]) >= "2026-10-01"

def test_coverage_records():
    cov = D["coverage"]; assert len(cov) >= 80 and {c["status"] for c in cov} == set(A.STATUSES)
    names = [c["name"] for c in cov]; assert len(names) == len(set(names))
    by = {m["id"]: m for m in D["models"]}
    for c in cov:
        assert set(c["kinds"]) <= set(A.KINDS) and isinstance(c["in_comfy_lists"], bool), c["name"]
        if c["model"]: assert c["model"] in by, c["name"]
        if c["status"] == "missing": assert not c["family"] and not c["goals"], c["name"]
        if c["status"] == "instance": assert c["family"] and not c["goals"], c["name"]
        if c["status"] == "goal": assert c["goals"] or c["name"].startswith("Qwen3"), c["name"]
        if c["date_verified"]: assert c["source_url"].startswith("https://"), c["name"]
    miss = {c["name"] for c in cov if c["status"] == "missing"}
    assert {"Stable Diffusion 2.x", "AuraFlow", "Chroma"} <= miss
    assert any(s["url"] == "https://comfy.org/hub/models/local/" for s in D["coverage_sources"]) and D["families_installed"] == 82

SHOTS = [{"goal": "image", "kind": "image", "prompt": "a lighthouse", "seconds": 10.0, "peak_vram_gib": 22.6, "src": "showcase/a.webp", "poster": "showcase/a.webp"}, {"goal": "image", "kind": "image", "prompt": "x", "seconds": 12.0, "peak_vram_gib": 21.0, "src": "showcase/b.webp", "poster": "showcase/b.webp"}, {"goal": "music", "kind": "audio", "prompt": "song", "seconds": 40.0, "peak_vram_gib": 26.0, "src": "showcase/s.m4a"}]
INST = {"Flux.1": {"port": 8650, "up": True}, "Mochi": {"port": 8651, "up": False}}
def merged(goals=None, inst=INST, shots=SHOTS): return A.merge(goals=GOALS if goals is None else goals, inst=inst, shots=shots)

def test_merge_marks_goal_instance_and_tested_from_stubbed_live_facts():
    r = merged(); by = {m["id"]: m for m in r["models"]}
    k = by["flux2-klein"]; assert k["can_run"] == "goal" and k["renders"]["count"] == 2 and k["renders"]["median_seconds"] == 11.0 and k["renders"]["peak_vram_gib"] == 22.6 and k["tested"] and k["goals_live"][0]["id"] == "image"
    assert by["flux1"]["can_run"] == "instance" and by["flux1"]["instance"]["up"] is True and by["flux1"]["instance"]["port"] == 8650
    assert by["mochi"]["can_run"] == "instance" and by["mochi"]["instance"]["up"] is False and by["mochi"]["renders"] is None
    assert by["gan"]["can_run"] is None and by["gan"]["instance"] is None and by["gan"]["tested"] is False
    assert by["minimax-music3"]["renders"]["media"]["kind"] == "audio"
    assert r["stats"]["models"] == len(D["models"]) and r["stats"]["coverage"]["missing"] >= 20

def test_a_goal_missing_from_this_build_is_not_offered_and_clean_clone_works():
    r = merged(goals={k: v for k, v in GOALS.items() if k != "image"}, inst={}, shots=[])
    k = next(m for m in r["models"] if m["id"] == "flux2-klein"); assert k["can_run"] is None and k["goals_live"] == [] and k["renders"] is None
    assert all(m["can_run"] != "instance" for m in r["models"]) and r["stats"]["rendered_here"] == 0

def test_tested_uses_renders_or_recorded_notes_only():
    r = merged(inst={}, shots=[]); by = {m["id"]: m for m in r["models"]}
    assert by["wan22"]["tested"] is (by["wan22"]["proof"]["tested"] > 0)
    assert not any(m["tested"] for m in r["models"] if m["proof"]["tested"] == 0 and not m["renders"])

def test_select_filters():
    ms = merged()["models"]
    assert {m["id"] for m in A.select(ms, kind="3d")} == {m["id"] for m in ms if "3d" in m["kinds"]}
    assert all(m["tested"] for m in A.select(ms, tested=True)) and A.select(ms, tested=True)
    assert all(m["can_run"] for m in A.select(ms, runs=True)) and {m["id"] for m in A.select(ms, kind="video", runs=True)} >= {"mochi", "wan22"}
    hit = A.select(ms, q="  ddpm "); assert "ddpm" in [m["id"] for m in hit] and all("ddpm" in (m["name"] + m["what"] + m["why"]).lower() for m in hit) and A.select(ms, kind="llm", q="qwen")
    assert A.select(ms, kind="all", q="zzzz-not-a-model") == []

def test_api_endpoint_with_stubs(monkeypatch):
    monkeypatch.setattr(A, "installed", lambda: INST); monkeypatch.setattr(A, "showcase", lambda: SHOTS)
    app = FastAPI(); app.include_router(A.router); r = TestClient(app).get("/api/atlas")
    assert r.status_code == 200; j = r.json()
    assert {"eras", "models", "coverage", "stats", "coverage_sources"} <= set(j) and len(j["eras"]) == 8
    assert not A.PRIVATE.search(r.text) and not re.search(r"localhost|127\.0\.0\.1", r.text)
    assert next(m for m in j["models"] if m["id"] == "flux1")["instance"]["port"] == 8650

def test_the_router_is_mounted_by_the_server():
    src = (Path(A.ROOT) / "server.py").read_text(encoding="utf8"); assert '"atlas"' in src
