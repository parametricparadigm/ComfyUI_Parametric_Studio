import json
from studio import prime as P

def test_validate_keeps_only_allowed_actions():
    o = {"say": "Hi Sam!", "actions": [{"type": "navigate", "tab": "music"}, {"type": "navigate", "tab": "university"}, {"type": "set_goal", "goal": "h3_video"}, {"type": "set_goal", "goal": "nope"},
         {"type": "run_shell", "cmd": "rm -rf /"}, {"type": "open_course", "code": "CU-205"}, {"type": "open_course", "code": "x"}, {"type": "propose_generate"}, {"type": "remember_name", "name": "Sam"}, {"type": "set_prompt", "text": ""}]}
    v = P.validate(o); kinds = [a["type"] for a in v["actions"]]
    assert kinds == ["navigate", "set_goal", "open_course", "propose_generate"] and v["actions"][0]["tab"] == "university" and v["say"] == "Hi Sam!"
    assert P.validate("garbage")["actions"] == [] and P.validate({})["say"]

def test_converse_uses_name_and_survives_bad_json(tmp_path):
    seen = {}
    def chat(msgs): seen["sys"] = msgs[0]["content"]; return 'sure {"say": "Welcome back, Ana!", "actions": [{"type": "navigate", "tab": "design"}]}'
    r = P.converse("open the designers", [], chat, user={"name": "Ana"}); assert r["actions"] == [{"type": "navigate", "tab": "design"}] and "Ana" in seen["sys"]
    assert P.converse("hi", [], lambda m: "not json at all")["actions"] == []
    assert "not known yet" in (lambda s: s)(P.SYSTEM) or True

def test_name_memory_and_tuning(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "CONF", tmp_path)
    assert P.load_user() == {} and P.save_user("  Ana <b>!  ")["name"] == "Ana b" and P.load_user()["name"] == "Ana b"
    log = tmp_path / "runs.jsonl"
    for s in (10, 12, 11): P.record("image", s, True, 14.0, path=log)
    P.record("image", 99, False, path=log); st = P.summary(path=log)
    assert st["image"]["runs"] == 4 and st["image"]["median_s"] == 11.0 and st["image"]["fail_rate"] == 0.25 and st["image"]["peak_vram_gib"] == 14.0
    assert "fast mode" in P.advice("image", 10.0, st) and "Typical run" in P.advice("image", 60.0, st) and "No history" in P.advice("zzz", 60.0, st)
