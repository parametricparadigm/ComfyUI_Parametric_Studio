"""Recipes: the data file, the chain runner with the studio's internals stubbed (no GPU, no ComfyUI, no LLM), and the ffmpeg steps run for real on tiny synthetic clips."""
import asyncio, json, os, shutil, subprocess, threading, time
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import studio.server as S
from studio import recipes as R

ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg is a documented requirement but is not on this machine")

def clip(path, color="red", seconds=2.0, audio=True, size="160x90"):
    a = ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"] if audio else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:s={size}:r=24:d={seconds}", *a, "-pix_fmt", "yuv420p", "-c:v", "libx264", "-shortest", str(path)], check=True); return str(path)
def clicks(path, bpm=120, seconds=20):
    """A metronome: a short click on every beat, an accent on every fourth."""
    beat = 60 / bpm; expr = f"lt(mod(t\\,{beat})\\,0.03)*sin(2*PI*1500*t)*(1+1.5*lt(mod(t\\,{beat * 4})\\,0.03))*0.3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={seconds}", str(path)], check=True); return str(path)
def scene_cuts(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", "select='gt(scene,0.2)',showinfo", "-f", "null", "-"], capture_output=True, text=True); return [float(x.split("pts_time:")[1].split()[0]) for x in r.stderr.splitlines() if "pts_time:" in x]

# ---------- recipes.json
def test_the_data_file_is_clean():
    assert R.validate() == []
def test_there_are_8_to_12_recipes_and_the_flagships_are_there():
    d = R.load(); ids = {r["id"] for r in d["recipes"]}; assert 8 <= len(ids) <= 12 and {"short_film", "music_video"} <= ids
    assert R.find("music_video")["title"] == "Music Video Maker" and R.find("music_video").get("hero") and R.find("short_film").get("hero")
def test_every_model_states_a_licence_and_h3_recipes_keep_its_note():
    for r in R.load()["recipes"]:
        for m in r["models"]: assert m["licence"] and m["licence_class"] in ("open", "community")
        if any(s.get("goal") in ("h3_video", "h3_animate", "director", "director_keyframes", "recast", "reshoot") for s in r["steps"]): assert any("H3" in m["name"] for m in r["models"]), r["id"]
def test_tested_is_only_claimed_with_media_and_numbers():
    for r in R.load()["recipes"]:
        t = r.get("tested")
        if t:
            for k in ("output", "media", "poster", "seconds", "peak_vram_gib", "rendered"): assert t.get(k), (r["id"], k)
def test_the_music_video_writes_enough_lyrics_and_stays_original_by_construction():
    r = R.find("music_video"); lyr = next(f for f in r["fields"] if f["key"] == "lyrics")["default"]; sung = [l for l in lyr.splitlines() if l.strip() and not l.startswith("[")]
    assert len(sung) * 6 >= 45 and "[chorus]" in lyr and "[verse]" in lyr and not any(t in lyr for t in ("[Verse 1]", "[Chorus 1]"))     # about 6 s a line; no numbered tags
    assert sum(1 for s in r["steps"] if s.get("goal") == "h3_animate") >= 6 and r["steps"][-1]["op"] == "beat_cut"
def test_a_validator_catches_real_mistakes():
    d = {"recipes": [{"id": "x", "title": "t", "pitch": "p", "why": "w", "tags": ["a"], "models": [{"name": "n", "licence": "l"}], "steps": [{"id": "a", "type": "goal", "goal": "nope"}, {"id": "b", "type": "goal", "goal": "h3_animate", "prompt": "p", "peak_gib": 1, "image": "@later"}, {"id": "c", "type": "goal", "goal": "image", "prompt": "{missing}", "options": {"aspect": "7:7"}, "peak_gib": 1}, {"id": "d", "type": "cpu", "op": "melt"}]}]}
    p = "\n".join(R.validate(d)); assert "unknown goal nope" in p and "@later is not an earlier step" in p and "7:7" in p and "{missing}" in p and "unknown op melt" in p

# ---------- film plan
PLAN = {"title": "Lamps", "logline": "l", "character": "an old man in a red coat", "world": "a flooded city at night", "look": "cinematic", "music": {"style": "orchestral", "mood": "builds", "instruments": "strings", "bpm": 90}, "shots": [{"action": f"action {i}", "shot": "wide", "camera": "dolly_in", "sound": "water"} for i in range(5)]}
def test_a_plan_is_cleaned_up_whatever_the_model_wrote():
    p = R.normalize_plan({**PLAN, "shots": [{"action": "a", "camera": "swoop", "shot": "giant"}] * 9, "music": {"bpm": 900}}, "s", "m")
    assert len(p["shots"]) == 6 and all(s["camera"] in ("dolly_in", "tracking") and s["shot"] == "wide" for s in p["shots"]) and p["music"]["bpm"] == 150 and p["writer"] == "m"
    assert R.normalize_plan({"shots": [{"action": "only one"}]}, "s")["writer"].startswith("fixed pattern")
def test_the_film_chain_keeps_one_character_and_cuts_on_the_beat():
    st = R.film_specs(R.normalize_plan(PLAN, "s", "m")); ids = [s["id"] for s in st]; assert ids[:2] == ["character", "style"] and ids[-2:] == ["score", "cut"] and sum(1 for s in st if s.get("goal") == "h3_animate") == 5
    keys = [s for s in st if s["type"] == "template"]; assert all(k["values"]["76|image"] == "@character" for k in keys) and all("an old man in a red coat" in k["set"]["75:74"]["text"] for k in keys if k["id"] != "style")
    shots = [s for s in st if s.get("goal") == "h3_animate"]; assert all(s["image"].startswith("@key") and "<Picture 1>" in s["prompt"] and "One continuous shot, no cuts." in s["prompt"] for s in shots)
    assert st[-1]["clips"] == [f"@shot{i}" for i in range(1, 6)] and st[-1]["audio"] == "@score" and "No vocals" in next(s for s in st if s["id"] == "score")["prompt"]
def test_plan_skips_a_sleeping_server_and_says_when_it_used_the_pattern(monkeypatch):
    monkeypatch.setattr(R, "_llm_candidates", lambda: [{"url": "http://x/v1", "model": "qwen"}]); monkeypatch.setattr(R, "_asleep", lambda u: True)
    p = R.plan_film("A fox crosses a frozen lake."); assert "asleep" in p["writer"] and len(p["shots"]) >= 4
def test_plan_uses_the_llm_answer_inside_fences_and_think_tags(monkeypatch):
    monkeypatch.setattr(R, "_llm_candidates", lambda: [{"url": "http://x/v1", "model": "qwen"}]); monkeypatch.setattr(R, "_asleep", lambda u: False)
    monkeypatch.setattr(R, "_chat", lambda c, t, timeout=240: "<think>hmm {not json}</think>```json\n" + json.dumps(PLAN) + "\n```")
    p = R.plan_film("A fox."); assert p["writer"] == "qwen" and p["title"] == "Lamps" and len(p["shots"]) == 5

# ---------- ffmpeg steps, for real
@ffmpeg
def test_beat_grid_finds_the_tempo_of_a_metronome(tmp_path):
    for bpm in (90, 120, 140):
        x = R.decode_mono(clicks(tmp_path / f"c{bpm}.wav", bpm)); got, beats, down, _ = R.beat_grid(x); assert abs(got - bpm) / bpm < 0.03, got
        gaps = [b - a for a, b in zip(beats, beats[1:])]; assert abs(sum(gaps) / len(gaps) - 60 / bpm) < 0.02 and len(beats) > 20
@ffmpeg
def test_beat_cut_lands_every_cut_on_a_beat_and_keeps_the_song(tmp_path):
    cs = [clip(tmp_path / f"{c}.mp4", c, 5.17, audio=False) for c in ("red", "blue", "green", "yellow")]; song = clicks(tmp_path / "song.wav", 120, 40); out = tmp_path / "out.mp4"
    r = R.beat_cut(cs, song, out); f = r["facts"]; assert abs(f["bpm"] - 120) < 3 and f["cuts_at"][0] == 0
    p = R.probe(out); assert p["audio"] and p["video"] and (p["width"], p["height"]) == (160, 90) and abs(p["duration"] - 16) < 0.5                   # 4 shots x 8 beats at 120 BPM
    cuts = scene_cuts(out); assert len(cuts) == 3
    for c in cuts: assert min(abs(c - t) for t in f["cuts_at"][1:]) <= 1.5 / 24 and abs((c / 0.5) - round(c / 0.5)) < 0.1                                    # on the grid, within a frame or so
@ffmpeg
def test_beat_cut_stays_within_a_length_limit(tmp_path):
    cs = [clip(tmp_path / f"{i}.mp4", c, 5.17, audio=False) for i, c in enumerate(("red", "blue", "green", "yellow", "white", "black"))]; song = clicks(tmp_path / "song.wav", 120, 40); out = tmp_path / "o.mp4"
    r = R.beat_cut(cs, song, out, total_max=9); assert R.probe(out)["duration"] < 9.5 and len(r["facts"]["cuts_at"]) == 2
@ffmpeg
def test_join_keeps_audio_and_size_and_mixes_a_silent_clip(tmp_path):
    a = clip(tmp_path / "a.mp4", "red", 1.0); b = clip(tmp_path / "b.mp4", "blue", 1.0, audio=False, size="320x180"); out = tmp_path / "j.mp4"
    R.join([a, b], out); p = R.probe(out); assert (p["width"], p["height"]) == (160, 90) and p["audio"] and abs(p["duration"] - 2) < 0.15
@ffmpeg
def test_loop_closes_the_seam_and_reports_it(tmp_path):
    a = tmp_path / "ramp.mp4"; subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "gradients=s=160x90:d=3:speed=0.1:r=24", "-pix_fmt", "yuv420p", str(a)], check=True); out = tmp_path / "l.mp4"
    r = R.loop_seam(a, out, 0.5); f = r["facts"]; assert f["seam_ssim_before"] is not None and f["seam_ssim_after"] >= f["seam_ssim_before"] and abs(f["seconds"] - 2.5) < 0.2
@ffmpeg
def test_compare_makes_a_grid_and_a_split(tmp_path):
    cs = [clip(tmp_path / f"{c}.mp4", c, 1.0) for c in ("red", "blue", "green", "white")]
    R.compare(cs, tmp_path / "g.mp4", ["A", "B", "C", "D"]); p = R.probe(tmp_path / "g.mp4"); assert p["width"] == 320 and p["height"] == 180
    R.compare(cs[:2], tmp_path / "s.mp4", ["A: it's", "B"], audio_from=1, mode="split"); p = R.probe(tmp_path / "s.mp4"); assert p["width"] == 160 and p["audio"]
@ffmpeg
def test_cut_between_and_frame_and_mux(tmp_path):
    a, b = clip(tmp_path / "a.mp4", "red", 2.0), clip(tmp_path / "b.mp4", "blue", 2.0); R.cut_between([a, b], tmp_path / "c.mp4", pieces=4); p = R.probe(tmp_path / "c.mp4"); assert p["audio"] and abs(p["duration"] - 2) < 0.15 and len(scene_cuts(tmp_path / "c.mp4")) == 3
    R.frame(a, tmp_path / "f.png"); assert (tmp_path / "f.png").stat().st_size > 0
    R.mux(clip(tmp_path / "s.mp4", "green", 1.0, audio=False), clicks(tmp_path / "s.wav", 120, 3), tmp_path / "m.mp4"); assert R.probe(tmp_path / "m.mp4")["audio"]

# ---------- the runner, with the studio's internals stubbed
RECIPE = {"id": "t", "title": "Test", "pitch": "p", "why": "w", "tags": ["a"], "models": [{"name": "n", "licence": "l", "licence_class": "open"}], "fields": [{"key": "subject", "label": "s", "default": "a fox"}], "steps": [
    {"id": "still", "type": "goal", "goal": "image", "label": "Still", "peak_gib": 23, "seed": 5, "prompt": "picture of {subject}", "options": {"aspect": "16:9"}, "swappable": True, "accepts": "image"},
    {"id": "move", "type": "goal", "goal": "h3_animate", "label": "Move", "peak_gib": 46, "seed": 6, "image": "@still", "prompt": "{subject} moves", "options": {"speed": "fast"}},
    {"id": "song", "type": "goal", "goal": "music", "label": "Song", "peak_gib": 27, "seed": 7, "prompt": "a song", "options": {"seconds": 30}}]}
class Fake:
    def __init__(self, tmp, free=90.0):
        self.bodies, self.free_calls, self.uploads, self.free, self.fail_on, self.order, self.cancelled = [], 0, [], free, None, [], []; self.tmp = tmp
    async def generate(self, req):
        b = await req.json(); self.bodies.append(b); self.order.append("gen:" + b["goal"])
        if b["goal"] == self.fail_on: raise HTTPException(400, "write a prompt first")
        return {"job": f"j{len(self.bodies)}", "seed": b.get("seed"), "graph_hash": "h"}
    def job(self, jid):
        i = int(jid[1:]); g = self.bodies[i - 1]["goal"]; ext, kind = {"image": ("png", "image"), "music": ("flac", "audio")}.get(g, ("mp4", "video")); f = self.tmp / f"{jid}.{ext}"; f.write_bytes(b"x")
        return {"status": "done", "files": [{"filename": f.name, "subfolder": "", "type": "output", "kind": kind, "url": "/api/view?filename=" + f.name}]}
    async def upload(self, file): self.uploads.append(file.filename); return {"name": "up_" + file.filename}
    def comfy(self, path, payload=None, timeout=30, raw=False):
        if path == "/free": self.free_calls += 1; self.order.append("free"); return {}
        if path == "/system_stats": return {"devices": [{"vram_free": self.free * 2**30, "vram_total": 96 * 2**30}]}
        return {}
    def cancel(self, jid): self.cancelled.append(jid); return {"ok": True}
    def _graph(self, goal, b, image): return {"1": {"class_type": "Node", "inputs": {"seed": b.get("seed")}}}, {}, {}
@pytest.fixture
def rig(tmp_path, monkeypatch):
    fake = Fake(tmp_path); monkeypatch.setattr(S, "generate", fake.generate); monkeypatch.setattr(S, "job", fake.job); monkeypatch.setattr(S, "upload", fake.upload); monkeypatch.setattr(S, "comfy", fake.comfy); monkeypatch.setattr(S, "cancel", fake.cancel); monkeypatch.setattr(S, "_graph", fake._graph); monkeypatch.setattr(S, "OUTPUT", tmp_path)
    data = {"version": 1, "measured": {"image": {"seconds": 10, "peak_gib": 23}}, "recipes": [RECIPE]}; monkeypatch.setattr(R, "load", lambda: data); monkeypatch.setattr(R, "_srv", lambda: S); monkeypatch.setattr(R, "POLL", 0.01); monkeypatch.setattr(R, "_used_gib", lambda: 12.0); monkeypatch.setattr(R, "_sampler", lambda box, stop: box.__setitem__(0, 12.0))
    R.RUNS.clear(); yield fake
    for r in R.RUNS.values(): r["_cancel"] = True
def wait(client, rid, run, timeout=8):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"/api/recipes/{rid}/runs/{run}").json()
        if r["status"] not in ("queued", "running"): return r
        time.sleep(0.02)
    raise AssertionError("the run did not finish")
client = TestClient(S.app)
def test_a_chain_passes_each_output_to_the_next_step_and_unloads_between_steps(rig):
    run = client.post("/api/recipes/t/run", json={"values": {"subject": "a red fox"}}).json()["run"]; r = wait(client, "t", run); assert r["status"] == "done", r
    assert [b["goal"] for b in rig.bodies] == ["image", "h3_animate", "music"] and rig.bodies[0]["prompt"] == "picture of a red fox" and rig.bodies[1]["image"] == "up_j1.png" and rig.uploads == ["j1.png"] and rig.bodies[0]["seed"] == 5
    assert rig.free_calls == 3 and rig.order[:3] == ["gen:image", "free", "gen:h3_animate"]
    assert [s["status"] for s in r["steps"]] == ["done"] * 3 and r["output"]["kind"] == "audio" and r["peak_vram_gib"] == 12.0 and r["steps"][1]["body"]["image"] == "up_j1.png"
def test_each_step_keeps_its_graph_one_click_away(rig):
    run = client.post("/api/recipes/t/run", json={}).json()["run"]; wait(client, "t", run)
    g = client.get(f"/api/recipes/t/runs/{run}/graph/still"); assert g.status_code == 200 and g.json()["graph"]["1"]["class_type"] == "Node"
    assert client.get(f"/api/recipes/t/runs/{run}/graph/../../x").status_code == 404 and client.get(f"/api/recipes/t/runs/{run}/graph/none").status_code == 404
def test_a_failed_step_stops_the_chain_and_says_why(rig):
    rig.fail_on = "h3_animate"; run = client.post("/api/recipes/t/run", json={}).json()["run"]; r = wait(client, "t", run)
    assert r["status"] == "error" and "write a prompt first" in r["error"] and [s["status"] for s in r["steps"]] == ["done", "error", "pending"] and len(rig.bodies) == 2
def test_the_vram_rule_unloads_then_waits_then_refuses_with_the_numbers(rig, monkeypatch):
    rig.free = 30.0; monkeypatch.setattr(R, "VRAM_WAIT", 0); run = client.post("/api/recipes/t/run", json={}).json()["run"]; r = wait(client, "t", run)
    assert r["status"] == "error" and "30 GiB free" in r["error"] and "needs 50 GiB" in r["error"] and [x["status"] for x in r["steps"]] == ["done", "error", "pending"]      # the still fits (23 + 4), the H3 step does not (46 + 4)
    assert [b["goal"] for b in rig.bodies] == ["image"] and rig.free_calls >= 2                                                                                                   # unloaded after the still, and once more when it came up short
def test_the_vram_rule_lets_a_small_card_run_on_offload(rig, monkeypatch):
    monkeypatch.setattr(R, "_vram", lambda: (21.7, 24.0)); R._vram_gate({"_cancel": False, "steps": [], "run": "0" * 12}, {}, 46.0); assert rig.free_calls == 0          # 90% of a 24 GB card is enough, however large the step's peak on a bigger card
def test_runs_are_queued_one_at_a_time(rig):
    started = threading.Event(); go = threading.Event(); orig = rig.job
    def slow(jid):
        started.set(); go.wait(3); return orig(jid)
    S.job = slow
    a = client.post("/api/recipes/t/run", json={}).json(); assert started.wait(3); b = client.post("/api/recipes/t/run", json={}).json(); st = client.get(f"/api/recipes/t/runs/{b['run']}").json(); assert st["status"] == "queued" and st["position"] == 1 and len(rig.bodies) == 1
    go.set(); assert wait(client, "t", a["run"])["status"] == "done" and wait(client, "t", b["run"])["status"] == "done" and len(rig.bodies) == 6
def test_cancel_stops_a_running_chain(rig):
    go = threading.Event(); orig = rig.job
    S.job = lambda jid: ({"status": "running"} if not go.is_set() else orig(jid))
    run = client.post("/api/recipes/t/run", json={}).json()["run"]; time.sleep(0.1); assert client.post(f"/api/recipes/t/runs/{run}/cancel").json()["ok"]; r = wait(client, "t", run); assert r["status"] == "cancelled" and rig.cancelled == ["j1"] and r["steps"][1]["status"] == "pending"; go.set()
def test_a_user_upload_replaces_a_swappable_step_only(rig, tmp_path):
    (tmp_path / "mine.png").write_bytes(b"x"); assert client.post("/api/recipes/t/run", json={"uploads": {"move": "a.mp4"}}).status_code == 400; assert client.post("/api/recipes/t/run", json={"uploads": {"still": "../etc/passwd"}}).status_code == 400
    f = rig.job; rig.job = f; S.urllib = S.urllib
    orig = R._localize; R._localize = lambda run, fl: str(tmp_path / "mine.png")
    try: run = client.post("/api/recipes/t/run", json={"uploads": {"still": "mine.png"}}).json()["run"]; r = wait(client, "t", run)
    finally: R._localize = orig
    assert r["status"] == "done" and r["steps"][0]["status"] == "skipped" and [b["goal"] for b in rig.bodies] == ["h3_animate", "music"] and rig.bodies[0]["image"] == "mine.png"
def test_state_survives_a_restart_and_a_lost_run_says_so(rig):
    run = client.post("/api/recipes/t/run", json={}).json()["run"]; wait(client, "t", run); R.RUNS.clear(); assert client.get(f"/api/recipes/t/runs/{run}").json()["status"] == "done"
    p = S.OUTPUT / "studio_recipes" / run / "run.json"; d = json.load(open(p)); d["status"] = "running"; p.write_text(json.dumps(d)); r = client.get(f"/api/recipes/t/runs/{run}").json(); assert r["status"] == "interrupted" and "restarted" in r["error"]
def test_the_api_lists_recipes_and_refuses_what_it_should(rig):
    d = client.get("/api/recipes").json(); assert d["untested"] == 1 and d["recipes"][0]["status"] == "untested" and d["recipes"][0]["expected"]["seconds"] == 10
    assert client.get("/api/recipes/nope").status_code == 404 and client.post("/api/recipes/nope/run", json={}).status_code == 404 and client.get("/api/recipes/t/runs/zzz").status_code == 404
    assert client.get("/api/recipes/files/" + "a" * 12 + "/run.json").status_code == 404 and client.get("/api/recipes/files/" + "a" * 12 + "/..%2F..%2Fsecret").status_code in (400, 404)
def test_finished_films_reach_the_library(rig, tmp_path):
    run = client.post("/api/recipes/t/run", json={}).json()["run"]; wait(client, "t", run); rows = R.library_rows(); assert rows and rows[0]["recipe"]["run"] == run and rows[0]["goal"] == "recipe" and rows[0]["files"][0]["url"]
