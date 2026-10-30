import json, os, re
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psn import instances as I
from studio import families_api as F

@pytest.fixture()
def box(tmp_path, monkeypatch):
    """A fake box: two instances on disk, one model folder with no instance, one directory with no instance file. No live port, no systemctl, no nvidia-smi."""
    root, models = tmp_path / "inst", tmp_path / "models"; cp = models / "_complete_pipelines"
    for fam, files in {"Flux.3-Klein": {"diffusion_models/k.safetensors": 10, "vae/ae.safetensors": 1}, "Empty": {}, "OnlyModels": {"vae/x.safetensors": 1}}.items():
        (cp / fam).mkdir(parents=True)
        for rel, mb in files.items(): p = cp / fam / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"x" * mb * 1000)
    monkeypatch.setattr(I, "MODELS", str(models)); monkeypatch.setattr(I, "INSTANCES", str(root)); monkeypatch.setattr(I, "PS_NODES", str(tmp_path / "nodes")); monkeypatch.setattr(I, "REPO_LIB", str(tmp_path / "repos"))
    I.generate("Flux.3-Klein", ports={"Flux.3-Klein": 8700}); I.generate("Empty", ports={"Empty": 8701}); (root / "stray-dir").mkdir()
    (root / "registry.json").write_text(json.dumps({"Flux.3-Klein": 8700, "Empty": 8701, "Ghost": 8702}))
    data = {"families": {"Flux.3-Klein": {"slug": "flux-3-klein", "kind": "image", "era": 2026, "licence": "x", "crew": "master", "repos": [], "what": "w", "what_source": "notes", "level": "validated", "test": {"nodes": 5}, "media": [], "templates": [{"name": "t_ok", "title": "OK", "desc": "", "media": "image", "cat": "", "gb": 1, "tags": [], "models": [{"name": "k.safetensors", "dir": "diffusion_models", "url": "https://huggingface.co/a/b/resolve/main/k.safetensors"}]}, {"name": "t_miss", "title": "Miss", "desc": "", "media": "image", "cat": "", "gb": 9, "tags": [], "models": [{"name": "nope.safetensors", "dir": "vae", "url": "https://huggingface.co/a/b/resolve/main/nope.safetensors", "gb": 9.0}]}]},
                         "Listed-Only": {"slug": "listed-only", "kind": "video", "era": None, "licence": None, "crew": "master", "repos": ["a/b"], "what": None, "what_source": None, "level": "untested", "test": {}, "media": [], "templates": []}}}
    st = tmp_path / "family_status.json"; st.write_text(json.dumps(data)); monkeypatch.setattr(F, "STATUS", st); F._st.update(m=0.0, d={"families": {}}); F._scan.update(t=0.0, d={}); F._dirs.update(root=None, t=0.0, d={}); F._shared.update(t=0.0, d={}); F.JOBS.clear()
    monkeypatch.setattr(I, "is_up", lambda p: False); monkeypatch.setattr(I, "free_vram_gb", lambda: 50.0); monkeypatch.setattr(F, "_ensure_reaper", lambda: None); monkeypatch.setattr(F, "idle_servers", lambda: [])
    app = FastAPI(); app.include_router(F.router); return {"c": TestClient(app), "root": root, "models": models}

def rows(box): return {r["family"]: r for r in box["c"].get("/api/families").json()["families"]}

def test_every_directory_and_every_entry_is_listed_with_an_honest_state(box):
    d = box["c"].get("/api/families").json(); r = {x["family"]: x for x in d["families"]}
    assert set(r) == {"Flux.3-Klein", "Empty", "stray-dir", "Listed-Only", "OnlyModels"}
    assert r["Flux.3-Klein"]["state"] == "validated" and r["Flux.3-Klein"]["models"]["files"] == 2 and r["Flux.3-Klein"]["templates"] == 2 and r["Flux.3-Klein"]["templates_ready"] == 1 and r["Flux.3-Klein"]["status"] == "down" and r["Flux.3-Klein"]["port"] == 8700
    assert r["Empty"]["state"] == "download" and r["stray-dir"]["state"] == "orphan" and r["Listed-Only"]["state"] == "nodir" and not r["Listed-Only"]["on_disk"]
    rc = d["reconcile"]; assert rc["dirs_on_disk"] == 3 and rc["shown"] == 5 and rc["no_instance_file"] == ["stray-dir"] and "Listed-Only" in rc["family_entry_without_dir"] and rc["in_registry_without_dir"] == ["Ghost"] and rc["model_folder_without_dir"] == ["OnlyModels"] and "Empty" in rc["dir_without_family_entry"]

def test_family_page_lists_what_is_missing_with_size(box):
    d = box["c"].get("/api/families/flux-3-klein").json(); t = {x["name"]: x for x in d["templates_list"]}
    assert t["t_ok"]["ready"] and not t["t_miss"]["ready"] and t["t_miss"]["missing_gb"] == 9.0 and t["t_miss"]["missing"][0]["url"].startswith("https://huggingface.co/") and d["templates_list"][0]["name"] == "t_ok"
    assert box["c"].get("/api/families/nope").status_code == 404

def test_gate_refusal_says_what_is_needed_and_free(box, monkeypatch):
    monkeypatch.setattr(I, "free_vram_gb", lambda: 5.0); calls = []; monkeypatch.setattr(I, "start", lambda *a, **k: calls.append(a) or {"status": "started"})
    monkeypatch.setattr(F, "idle_servers", lambda: [{"name": "Main ComfyUI", "state": "idle"}, {"name": "Busy", "state": "busy"}])
    i = json.load(open(box["root"] / "flux-3-klein" / "instance.json")); i["est_vram_gb"] = 30.0; json.dump(i, open(box["root"] / "flux-3-klein" / "instance.json", "w"))
    r = box["c"].post("/api/families/flux-3-klein/start").json()
    assert r["status"] == "refused" and r["need_gb"] == 30.0 and r["free_gb"] == 5.0 and r["floor_gb"] == I.FLOOR_GB and r["idle"] == ["Main ComfyUI"] and r["busy"] == ["Busy"] and not calls and "30.0 GB" in r["message"]

def test_start_and_stop_go_through_instances_and_mark_for_reaping(box, monkeypatch):
    starts, stops = [], []; monkeypatch.setattr(I, "start", lambda f, **k: starts.append((f, k)) or {"status": "started", "port": 8700, "secs": 3}); monkeypatch.setattr(I, "stop", lambda f, *a, **k: stops.append(f) or {"status": "stopped", "port": 8700})
    r = box["c"].post("/api/families/flux-3-klein/start", json={"need_gb": 0.1}).json(); assert r["status"] == "started" and starts[0][1]["need_gb"] == I.IDLE_GB
    assert (box["root"] / "flux-3-klein" / "studio_started").exists() and (box["root"] / "flux-3-klein" / "user" / "default" / "comfy.settings.json").exists()
    assert box["c"].post("/api/families/flux-3-klein/stop").json()["status"] == "stopped" and stops == ["Flux.3-Klein"] and not (box["root"] / "flux-3-klein" / "studio_started").exists()

def test_stop_refuses_a_busy_instance(box, monkeypatch):
    monkeypatch.setattr(I, "is_up", lambda p: True); monkeypatch.setattr(F, "_queue", lambda p: {"running": 1, "pending": 0, "busy": True}); stops = []; monkeypatch.setattr(I, "stop", lambda *a, **k: stops.append(a))
    assert box["c"].post("/api/families/flux-3-klein/stop").status_code == 409 and not stops

def test_free_idle_only_frees_idle_servers(box, monkeypatch):
    monkeypatch.setattr(F, "idle_servers", lambda: [{"name": "A", "url": "http://a", "port": 1, "state": "idle"}, {"name": "B", "url": "http://b", "port": 2, "state": "busy"}, {"name": "C", "url": "http://c", "port": 3, "state": "claimed"}]); posted = []; monkeypatch.setattr(F, "_post", lambda u, b, timeout=30: posted.append(u) or {}); monkeypatch.setattr(F.time, "sleep", lambda s: None)
    r = box["c"].post("/api/families/free-idle").json(); assert posted == ["http://a/free"] and r["freed"] == ["A"] and {x["name"] for x in r["left"]} == {"B", "C"}

def test_idle_servers_marks_busy_and_claimed(box, monkeypatch):
    monkeypatch.undo(); monkeypatch.setattr(I, "INSTANCES", str(box["root"])); monkeypatch.setattr(I, "is_up", lambda p: p == 8700); monkeypatch.setattr(F, "_queue_url", lambda u: u.endswith(":8700")); cl = box["root"] / "claims.json"; cl.write_text(json.dumps([8200])); monkeypatch.setenv("STUDIO_VRAM_CLAIMS", str(cl)); monkeypatch.setattr(F.A, "COMFY", "http://127.0.0.1:8200")
    s = {x["name"]: x["state"] for x in F.idle_servers()}; assert s["Main ComfyUI"] == "claimed" and s["Flux.3-Klein"] == "busy"

def test_reaper_only_touches_what_the_studio_started(box, monkeypatch):
    monkeypatch.setattr(I, "is_up", lambda p: True); monkeypatch.setattr(F, "_queue", lambda p: {"running": 0, "pending": 0, "busy": False}); monkeypatch.setattr(I, "idle_seconds", lambda p: 9999.0); stops = []; monkeypatch.setattr(I, "stop", lambda f, *a, **k: stops.append(f))
    assert F.reap_once(1) == [] and not stops                       # up and idle, but nothing here started it
    m = box["root"] / "flux-3-klein" / "studio_started"; m.write_text("x"); os.utime(m, (1, 1))
    assert F.reap_once(1) == ["Flux.3-Klein"] and stops == ["Flux.3-Klein"] and not m.exists()

def test_view_stays_inside_the_instance(box):
    out = box["root"] / "flux-3-klein" / "output"; (out / "a.png").write_bytes(b"png"); c = box["c"]
    assert c.get("/api/families/flux-3-klein/view", params={"filename": "a.png"}).content == b"png"
    assert c.get("/api/families/flux-3-klein/view", params={"filename": "../instance.json"}).status_code == 400 and c.get("/api/families/flux-3-klein/view", params={"filename": "x", "subfolder": "../.."}).status_code == 400 and c.get("/api/families/flux-3-klein/view", params={"filename": "a.png", "type": "secret"}).status_code == 400

def test_history_merges_saved_jobs_and_keeps_only_media(box):
    rec = {"job": "fam-1", "slug": "flux-3-klein", "family": "Flux.3-Klein", "status": "done", "started": 5.0, "prompt": "a fox", "seed": 3, "template": "t_ok", "graph": {"1": {"class_type": "X", "inputs": {}}}, "files": [{"filename": "a.png", "kind": "image", "url": "/u"}, {"filename": "a.glb", "kind": "model", "url": "/g"}]}
    with open(box["root"] / "flux-3-klein" / "studio_jobs.jsonl", "w") as fh: fh.write(json.dumps(rec) + "\n" + json.dumps({**rec, "job": "fam-2", "status": "error"}) + "\nnot json\n")
    r = F.history_rows(10); assert [x["job"] for x in r] == ["fam-1"] and r[0]["family"] == "flux-3-klein" and r[0]["goal"] == "Flux.3-Klein" and [f["filename"] for f in r[0]["files"]] == ["a.png"]
    assert F.job_graph("flux-3-klein/fam-1")["graph"]["1"]["class_type"] == "X" and box["c"].get("/api/families/flux-3-klein/jobs/fam-1").json()["status"] == "done"

def test_a_template_with_missing_files_does_not_run(box):
    assert box["c"].post("/api/families/flux-3-klein/templates/t_miss/run", json={"values": {}}).status_code in (400, 503)

def test_run_builds_on_the_instance_and_records_the_job(box, monkeypatch, tmp_path):
    tdir = tmp_path / "tpl"; tdir.mkdir(); (tdir / "t_ok.json").write_text("{}"); monkeypatch.setattr(F.A, "template_dir", lambda: str(tdir)); monkeypatch.setattr(I, "is_up", lambda p: True); oi = {"X": {}}; monkeypatch.setattr(F, "_oi", lambda p: oi)
    g = {"1": {"class_type": "SaveImage", "inputs": {"seed": 1}}}; monkeypatch.setattr(F.A, "build_graph", lambda p, v, o: g); posted = []
    def fake_post(u, b, timeout=30): posted.append(u); return {"prompt_id": "P"} if u.endswith("/prompt") else {}
    monkeypatch.setattr(F, "_post", fake_post); monkeypatch.setattr(F, "_queue", lambda p: {"running": 1, "pending": 0, "busy": True})
    class R:
        def read(self): return json.dumps({"P": {"status": {"status_str": "success", "completed": True}, "outputs": {"1": {"images": [{"filename": "a.png", "subfolder": "", "type": "output"}]}}}}).encode()
    monkeypatch.setattr(F.urllib.request, "urlopen", lambda *a, **k: R()); monkeypatch.setattr(F.time, "sleep", lambda s: None); started = []
    class T:
        def __init__(self, target, args, **k): self.t, self.a = target, args
        def start(self): self.t(*self.a)
    monkeypatch.setattr(F.threading, "Thread", T)
    j = box["c"].post("/api/families/flux-3-klein/templates/t_ok/run", json={"values": {"1|text": "a red fox"}}).json()["job"]; s = box["c"].get(f"/api/families/flux-3-klein/jobs/{j}").json()
    assert s["status"] == "done" and s["files"][0]["url"].startswith("/api/families/flux-3-klein/view?") and "graph" not in s and any(u.endswith(":8700/prompt") for u in posted) and any(u.endswith(":8700/free") for u in posted) and s["prompt"] == "a red fox"
    assert F.job_graph(f"flux-3-klein/{j}")["graph"] is g and [x["job"] for x in F.history_rows(5)] == [j]

def test_generate_themes_new_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "MODELS", str(tmp_path / "m")); monkeypatch.setattr(I, "INSTANCES", str(tmp_path / "i")); monkeypatch.setattr(I, "REPO_LIB", str(tmp_path / "r")); os.makedirs(tmp_path / "m"); I.generate("New", models=str(tmp_path / "m"), root=str(tmp_path / "i"), ps_nodes=str(tmp_path / "n"), ports={"New": 8999})
    s = json.load(open(tmp_path / "i" / "new" / "user" / "default" / "comfy.settings.json")); assert s["Comfy.ColorPalette"] == "custom_parametric" and "parametric" in s["Comfy.CustomColorPalettes"]

def test_shipped_status_file_has_every_family_and_no_box_paths():
    p = F.ROOT / "family_status.json"; t = p.read_text(); assert not re.search(r"/mnt/|/home/|/tmp/", t); d = json.loads(t)["families"]; assert len(d) >= 82
    for f, v in d.items(): assert v["kind"] in ("image", "video", "audio", "3d", "utility", "llm") and v["slug"] == I.slug(f) and v["level"] in ("render", "validated", "nodes", "started", "untested") and v["crew"]
