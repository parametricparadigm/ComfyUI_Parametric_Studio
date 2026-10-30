from studio import calibrate as C

def test_plan_respects_free_vram_and_installed():
    p = dict(C.plan(40.0, {"image", "anime", "h3_video", "music"}))
    assert p["anime"] is None and p["image"] is None and p["music"] is None and "needs about 50" in p["h3_video"] and p["video"] == "models not installed"
    assert all(v for v in dict(C.plan(None, {"image"})).values())              # unknown VRAM: nothing runs

def test_run_records_cold_and_warm_and_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "STATE", tmp_path); clock = {"t": 0.0}; monkeypatch.setattr(C.time, "time", lambda: clock["t"])
    calls = []
    def post(body):
        calls.append(body["goal"]); 
        if body["goal"] == "anime" and calls.count("anime") == 2: raise RuntimeError("boom")
        return f"j{len(calls)}"
    def poll(j): clock["t"] += 3.0; return {"status": "done"}
    prof = C.run(post, poll, free_fn=lambda: 60.0, installed={"image", "anime"}, sleep=lambda s: None)
    assert prof["goals"]["image"]["ok"] is True and prof["goals"]["image"]["seconds_warm"] == 3.0 and prof["goals"]["anime"]["ok"] is False
    assert C.load_profile()["goals"]["image"]["ok"] and C.load_profile()["goals"]["video"]["skipped"] == "models not installed"
