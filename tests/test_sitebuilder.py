import json, os, stat, zipfile
import pytest
from psn.sitebuilder import build_site, check_site, style
from psn.sitebuilder import build as B, export as E
from psn.subagents.runner import Result
from tests.test_subagents import SITE_OK

def test_tokens_meet_contrast_for_any_brand_colour():
    for brand in ("#3b6ea5", "#ffff00", "#000000", "#ff00ff", "#fafafa", "#b5651d"):
        t = style.make_tokens(brand); assert style.token_problems(t) == [], (brand, style.token_problems(t))
    assert style.contrast("#000000", "#ffffff") == pytest.approx(21.0, abs=0.05)
    with pytest.raises(ValueError): style.make_tokens("red")
    bad = style.make_tokens(); bad["light"]["muted"] = "#dddddd"; assert any("muted" in p for p in style.token_problems(bad))

def fake_runner(output):
    def run(role, task, ctx=None, **kw): return Result(True, role, output, attempts=1)
    return run

def test_build_writes_a_checked_offline_site(tmp_path):
    rep = build_site({"name": "Harbor Bakery", "about": "x", "facts": {"email": "hello@example.org", "phone": "+1 555 0100"}, "brand": "#b5651d"}, str(tmp_path / "s"), runner=fake_runner(SITE_OK))
    assert rep["ok"], rep["problems"]; d = tmp_path / "s"
    assert (d / "index.html").exists() and (d / "assets/style.css").exists() and (d / "assets/home-welcome.svg").exists() and rep["images_todo"] == 1
    h = (d / "index.html").read_text(); assert "mailto:hello@example.org" in h and "tel:+15550100" in h and "http://" not in h.replace("http://www.w3.org", "") and "<h1>Home</h1>" in h
    assert json.loads((d / "images_todo.json").read_text())[0]["prompt"].startswith("loaves of sourdough") and zipfile.ZipFile(rep["zip"]).testzip() is None

def test_copy_is_html_escaped(tmp_path):
    evil = json.loads(json.dumps(SITE_OK)); evil["pages"][0]["sections"][0]["heading"] = "<script>alert(1)</script> Bread & more"
    rep = build_site({"name": "A<b>B", "brand": "#336699"}, str(tmp_path / "s"), runner=fake_runner(evil)); h = (tmp_path / "s/index.html").read_text()
    assert "<script>alert" not in h and "&lt;script&gt;" in h and "A&lt;b&gt;B" in h and rep["ok"]

def test_checker_catches_each_kind_of_problem(tmp_path):
    good = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>T</title></head><body><h1>Hi</h1><img src="a.svg" alt="x"></body></html>'
    (tmp_path / "a.svg").write_text("<svg/>"); (tmp_path / "index.html").write_text(good); assert check_site(str(tmp_path)) == []
    cases = {"two h1": good.replace("<h1>Hi</h1>", "<h1>a</h1><h1>b</h1>"), "alt": good.replace(' alt="x"', ""), "remote": good.replace("</body>", '<a href="https://example.com">x</a></body>'), "broken": good.replace("</body>", '<a href="nope.html">x</a></body>'),
             "viewport": good.replace('<meta name="viewport" content="width=device-width,initial-scale=1">', ""), "inline script": good.replace("</body>", "<script>1</script></body>"), "unclosed": good.replace("</body>", "<div></body>"), "sfw": good.replace("Hi", "nude art")}
    want = {"two h1": "exactly one", "alt": "alt text", "remote": "remote resource", "broken": "broken link", "viewport": "viewport", "inline script": "inline script", "unclosed": "unclosed", "sfw": "non-SFW"}
    for k, html in cases.items():
        (tmp_path / "index.html").write_text(html); assert any(want[k] in p for p in check_site(str(tmp_path))), (k, check_site(str(tmp_path)))
    (tmp_path / "index.html").write_text(good); (tmp_path / "x.css").write_text("@import url('https://fonts.example/x.css');"); assert any("remote URL in CSS" in p for p in check_site(str(tmp_path)))

def test_brief_and_failed_copy_write_nothing(tmp_path):
    assert B.brief_problems({}) == ["brief needs a name"] and any("non-SFW" in p for p in B.brief_problems({"name": "x", "about": "explicit nude photos"}))
    r = build_site({"name": "x", "about": "naked"}, str(tmp_path / "s"), runner=fake_runner(SITE_OK)); assert not r["ok"] and r["stage"] == "brief" and not (tmp_path / "s").exists()
    def failing(role, task, ctx=None, **kw): return Result(False, role, None, problems=["contact detail not in the brief's facts: 'x'"], attempts=3)
    r = build_site({"name": "x"}, str(tmp_path / "t"), runner=failing); assert not r["ok"] and r["stage"] == "copy" and not (tmp_path / "t").exists()

def test_dyad_export_uses_only_allowed_bridge_commands(tmp_path, monkeypatch):
    site = tmp_path / "site"; (site / "assets").mkdir(parents=True); (site / "index.html").write_text("<h1>x</h1>"); (site / "assets/style.css").write_text("a{}")
    log = tmp_path / "log.txt"; br = tmp_path / "dyad-bridge"; br.write_text(f'#!/bin/sh\necho "$@" >> {log}\n'); br.chmod(br.stat().st_mode | stat.S_IEXEC)
    r = E.export_to_dyad(str(site), "My Site!", bridge=str(br)); assert r["ok"] and r["slug"] == "my-site" and r["files"] == 2 and r["git"]
    calls = log.read_text().splitlines(); assert calls[0].startswith("create My Site! --slug my-site") and sum(c.startswith("write my-site") for c in calls) == 2 and calls[-1].startswith("git my-site")
    for forbidden in ("run", "install", "delete", "scaffold"):
        with pytest.raises(PermissionError): E._call(str(br), forbidden, "x")
    monkeypatch.setenv("PSN_DYAD_BRIDGE", str(tmp_path / "missing")); assert "not configured" in E.export_to_dyad(str(site), "x", bridge=None)["status"]
