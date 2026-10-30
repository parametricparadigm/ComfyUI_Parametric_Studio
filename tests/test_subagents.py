import json, os, stat
import pytest
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from psn.subagents import ROLES, run_subagent, fan_out, join
from psn.subagents import llm, tools, runner
from psn.subagents.verify import validate, extract_json

OI = {"EmptyImage": {"input": {"required": {"width": ["INT", {}], "height": ["INT", {}], "batch_size": ["INT", {}], "color": ["INT", {}]}}, "output": ["IMAGE"]},
      "SaveImage": {"input": {"required": {"images": ["IMAGE"], "filename_prefix": ["STRING", {}]}}, "output": []}}
GOOD_G = {"1": {"class_type": "EmptyImage", "inputs": {"width": 64, "height": 64, "batch_size": 1, "color": 0}}, "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0], "filename_prefix": "x"}}}
SRC = "The studio runs on port 8200. It has 16 nodes. Torch 2.16 is installed."
steps = [{"id": "a", "goal": "g", "depends_on": [], "role": "writer"}, {"id": "b", "goal": "h", "depends_on": ["a"], "role": "judge"}]
LIC = {"good": "MIT License. Permission is hereby granted, free of charge", "nc": "Creative Commons Attribution-NonCommercial 4.0 (CC-BY-NC)"}

SITE_OK = {"pages": [{"slug": "home", "title": "Home", "description": "A family bakery.", "sections": [{"id": "welcome", "heading": "Fresh bread daily", "body": "We bake sourdough and pastries every morning in our small shop.", "alt": "Loaves of bread on a wooden counter", "image_prompt": "loaves of sourdough bread on a wooden counter, warm morning light"}]}]}
SITE_BAD = {"pages": [{"slug": "home", "title": "Home", "description": "A family bakery.", "sections": [{"id": "welcome", "heading": "Call us", "body": "Phone us any time on 555-0199 or write to fake@scam.example for orders.", "alt": "Bread", "image_prompt": "bread"}]}]}

# role -> (ctx, good output, bad output, text expected in the problems for the bad one)
CASES = {
 "writer": ({"sections": ["Purpose"], "max_words": 50}, {"text": "## Purpose\nShort."}, {"text": "No headings here."}, "missing section"),
 "classifier": ({"labels": ["a", "b"]}, {"label": "a", "confidence": 0.9}, {"label": "zzz", "confidence": 0.9}, "not in the allowed set"),
 "coder": ({"tests": "assert add(1, 2) == 3"}, {"code": "def add(a, b):\n    return a + b", "explanation": "adds"}, {"code": "import os\ndef add(a, b):\n    return a + b", "explanation": "x"}, "banned import"),
 "judge": ({"threshold": 0.5}, {"score": 0.8, "verdict": "pass", "reasons": ["ok"]}, {"score": 0.2, "verdict": "pass", "reasons": ["ok"]}, "contradicts"),
 "fact_checker": ({"source": SRC}, {"claims": [{"claim": "port 8200", "verdict": "supported", "quote": "The studio runs on port 8200."}]},
                  {"claims": [{"claim": "port 9", "verdict": "supported", "quote": "The studio runs on port 9."}]}, "not found verbatim"),
 "researcher": ({"read_roots": [REPO]}, {"findings": [{"statement": "s", "source_path": os.path.join(REPO, "EDITIONS.md"), "quote": "Open"}]},
                {"findings": [{"statement": "s", "source_path": "/etc/passwd", "quote": "root"}]}, "not a readable file"),
 "planner": ({}, {"steps": steps}, {"steps": [{"id": "a", "goal": "g", "depends_on": ["b"], "role": "writer"}, {"id": "b", "goal": "h", "depends_on": ["a"], "role": "writer"}]}, "cycle"),
 "captioner": ({}, {"caption": "a red paper boat on wet cobblestones at dusk", "tags": ["boat", "street", "rain"], "objects": ["boat"]},
               {"caption": "nude figure on a beach at sunset today ok", "tags": ["a", "b", "c"], "objects": []}, "non-SFW"),
 "prompt_enhancer": ({"must_keep": ["fox"], "min_words": 5}, {"prompt": "a red fox standing in morning mist, shallow depth of field", "negative": "blurry"},
                     {"prompt": "a dog in mist at dawn with soft light all around", "negative": "blurry"}, "dropped"),
 "sfw_guard": ({"text": "a naked person"}, {"allowed": False, "categories": ["nudity"], "reason": "r"}, {"allowed": True, "categories": [], "reason": "r"}, "keyword filter"),
 "graph_builder": ({"object_info": OI}, {"graph": GOOD_G}, {"graph": {"1": {"class_type": "LtxApi25TextToVideo", "inputs": {}}}}, "partner"),
 "graph_debugger": ({"object_info": OI, "graph": {"1": {"class_type": "EmptyImage", "inputs": {}}}}, {"graph": GOOD_G, "changes": ["added inputs and a SaveImage"]}, {"graph": {"1": {"class_type": "EmptyImage", "inputs": {}}}, "changes": []}, "unchanged"),
 "summarizer": ({"source": SRC, "must_keep": ["8200"]}, {"summary": "Runs on port 8200 with 16 nodes."}, {"summary": "Runs on port 8200 with 99 nodes."}, "numbers not in the source"),
 "extractor": ({"source": SRC, "schema": {"type": "object", "required": ["port"], "properties": {"port": {"type": "string"}}}}, {"data": {"port": "8200"}}, {"data": {"port": "8300"}}, "not found in the source"),
 "red_team": ({}, {"cases": [{"input": "i1", "expected_failure": "e", "why": "w"}, {"input": "i2", "expected_failure": "e", "why": "w"}, {"input": "i3", "expected_failure": "e", "why": "w"}]},
              {"cases": [{"input": "same", "expected_failure": "e", "why": "w"}] * 3}, "distinct"),
 "license_auditor": ({"files": LIC}, {"packs": [{"name": "good", "spdx": "MIT", "open_ok": True, "reason": "r"}]}, {"packs": [{"name": "nc", "spdx": "CC-BY-NC-4.0", "open_ok": True, "reason": "r"}]}, "non-commercial"),
 "vram_steward": ({"free_gb": 10, "need_gb": 7}, {"action": "wait", "reason": "r"}, {"action": "run", "reason": "r"}, "floor"),
 "site_copywriter": ({"brief": {"name": "Harbor Bakery", "facts": {"email": "hello@example.org"}}}, SITE_OK, SITE_BAD, "contact detail not in the brief"),
 "router": ({"allowed": ["writer", "coder"]}, {"role": "coder", "reason": "r"}, {"role": "judge", "reason": "r"}, "not one of"),
}



def scripted(*replies):
    it = iter(replies)
    def transport(url, body, timeout):
        r = next(it); text = r if isinstance(r, str) else json.dumps(r)
        return {"choices": [{"message": {"content": text}}], "usage": {"completion_tokens": 10}}
    return transport

def test_every_role_has_a_case_and_a_job():
    assert set(CASES) | {"builder", "operator", "scout", "model_sorter"} == set(ROLES), set(ROLES) ^ set(CASES)   # builder/operator: tests/test_subagent_tools.py (they need recorded tool state)
    for r in ROLES.values():
        assert r.purpose and r.system and r.schema["required"] and callable(r.verify)
        assert set(r.tools) <= set(tools.TOOLS) and "spawn" not in r.tools

@pytest.mark.parametrize("name", sorted(CASES))
def test_verifier_accepts_good_and_rejects_bad(name):
    ctx, good, bad, expect = CASES[name]; r = ROLES[name]
    assert validate(good, r.schema) == [] and r.verify(good, ctx) == [], (r.verify(good, ctx), validate(good, r.schema))
    assert validate(bad, r.schema) == [], validate(bad, r.schema)
    probs = r.verify(bad, ctx); assert probs and any(expect in p for p in probs), probs

@pytest.mark.parametrize("name", sorted(CASES))
def test_run_subagent_end_to_end_bad_then_good(name, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", str(tmp_path)); ctx, good, bad, _ = CASES[name]
    r = run_subagent(name, "do it", ctx, transport=scripted({"final": bad}, {"final": good}))
    assert r.ok and r.attempts == 2 and r.output == good and r.problems == []

def test_gives_up_with_problems_when_never_fixed(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", str(tmp_path)); ctx, good, bad, _ = CASES["classifier"]
    r = run_subagent("classifier", "x", ctx, max_attempts=2, transport=scripted({"final": bad}, {"final": bad}))
    assert not r.ok and r.attempts == 2 and "not in the allowed set" in r.problems[0]

def test_tool_allow_list_and_tool_use(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", str(tmp_path)); seen = []
    monkeypatch.setitem(tools.TOOLS, "vram_status", lambda a, c: {"free_gb": 20.0}); monkeypatch.setitem(tools.TOOLS, "run_python", lambda a, c: seen.append(1) or {})
    r = run_subagent("vram_steward", "start LTX", {"free_gb": 20, "need_gb": 5}, transport=scripted({"tool": "run_python", "args": {"code": "1"}}, {"tool": "vram_status", "args": {}}, {"final": {"action": "run", "reason": "fits"}}))
    assert r.ok and r.steps == 3 and not seen                      # the disallowed tool was never executed
    msgs = json.load(open(r.transcript)); assert any("not allowed for role" in m["content"] for m in msgs if isinstance(m["content"], str))

def test_budget_stops_the_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", str(tmp_path))
    r = run_subagent("classifier", "x", {"labels": ["a"]}, max_total_tokens=5, transport=scripted("not json", "not json", "not json"))
    assert not r.ok and any("budget" in p or "JSON" in p for p in r.problems)

def test_open_edition_refuses_remote_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", str(tmp_path)); monkeypatch.delenv("PSN_EDITION", raising=False)
    with pytest.raises(PermissionError, match="loopback"):
        run_subagent("router", "x", {}, endpoint={"url": "https://api.example.com/v1", "model": "m"}, transport=scripted({"final": {}}))

def test_logs_and_private_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", str(tmp_path)); ctx, good, _, _ = CASES["router"]
    r = run_subagent("router", "pick", ctx, transport=scripted({"final": good}))
    rec = json.loads((tmp_path / "subagents.jsonl").read_text().splitlines()[-1]); assert rec["role"] == "router" and rec["ok"] and rec["tokens"] == 10
    assert stat.S_IMODE(os.stat(r.transcript).st_mode) == 0o600

def test_fanout_vote_and_isolated_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", str(tmp_path)); ctx, good, bad, _ = CASES["classifier"]
    calls = iter([good, good, {"label": "b", "confidence": 0.5}])
    rs = fan_out([{"role": "classifier", "task": str(i), "ctx": ctx} for i in range(3)], max_workers=1, transport=lambda u, b, t: {"choices": [{"message": {"content": json.dumps({"final": next(calls)})}}], "usage": {}})
    j = join(rs, "vote"); assert j["ok"] and j["output"] == good and "2 of 3" in j["detail"]
    boom = fan_out([{"role": "classifier", "task": "x", "ctx": ctx}], runner=lambda *a, **k: 1 / 0); assert not boom[0].ok and "ZeroDivisionError" in boom[0].problems[0]

def test_extract_json_and_nodes(monkeypatch):
    assert extract_json("sure!\n```json\n{\"a\": {\"b\": 1}}\n```") == {"a": {"b": 1}} and extract_json("none") is None
    from psn_nodes import subagents as N
    from psn.subagents.runner import Result
    monkeypatch.setattr(N, "run_subagent", lambda *a, **k: Result(True, "writer", {"text": "hello"}))
    out = N.PSN_Subagent().run("writer", "t"); assert out[0] == "hello" and out[2] is True
    assert "PSN_Subagent" in N.NODE_CLASS_MAPPINGS and N.PSN_Subagent.INPUT_TYPES()["required"]["role"][0] == list(ROLES)

def test_graph_links_must_use_string_ids():
    bad = json.loads(json.dumps(GOOD_G)); bad["2"]["inputs"]["images"] = [1, 0]
    probs = ROLES["graph_builder"].verify({"graph": bad}, {"object_info": OI}); assert any("must be a string" in p for p in probs), probs
