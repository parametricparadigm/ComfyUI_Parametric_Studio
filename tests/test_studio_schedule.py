import pytest
from studio import schedule as S

@pytest.fixture(autouse=True)
def conf(tmp_path, monkeypatch): monkeypatch.setattr(S, "CONF", tmp_path)

def good(**k): return {"cron": "0 8 * * *", "goal": "image", "prompt": "a calm lake at sunrise", **k}

def test_validation_rules():
    assert S.validate(good(cron="every morning at 8"))["cron"] == "0 8 * * *"
    for bad, msg in ((good(cron="nonsense"), "schedule"), (good(goal="nope"), "goal"), (good(goal="animate"), "image"), (good(prompt="hi"), "prompt"), (good(prompt="explicit nude art"), "safe-for-work")):
        with pytest.raises(ValueError, match=msg): S.validate(bad)
    assert S.validate(good(max_per_day=99))["max_per_day"] == 24

def test_fire_respects_idle_cap_and_pause():
    d = S.validate(good(max_per_day=2)); d.update(id="a1", runs_today=0, day="", last_run=None, last_status=""); S.save([d]); calls = []
    post = lambda path, body: calls.append((path, body))
    assert S.fire("a1", post=post, idle=lambda: False) == "skipped: busy" and calls == []
    assert S.fire("a1", post=post, idle=lambda: True, now=1_000_000) == "started" and S.fire("a1", post=post, idle=lambda: True, now=1_000_100) == "started"
    assert S.fire("a1", post=post, idle=lambda: True, now=1_000_200) == "skipped: daily cap reached" and len(calls) == 2 and calls[0][1]["goal"] == "image"
    assert S.fire("a1", post=post, idle=lambda: True, now=1_000_000 + 90_000) == "started"          # next day resets the counter
    j = S.load()[0]; j["enabled"] = False; S.save([j]); assert S.fire("a1", post=post, idle=lambda: True) == "skipped: paused" and S.fire("zzz") == "missing"

def test_router_roundtrip():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI(); app.include_router(S.router); c = TestClient(app)
    r = c.post("/api/schedules", json=good()); assert r.status_code == 200; sid = r.json()["id"]
    assert c.post("/api/schedules", json=good(cron="bad")).status_code == 400 and len(c.get("/api/schedules").json()["jobs"]) == 1
    assert c.post(f"/api/schedules/{sid}/toggle").json()["enabled"] is False and c.delete(f"/api/schedules/{sid}").json()["ok"] and c.get("/api/schedules").json()["jobs"] == []
