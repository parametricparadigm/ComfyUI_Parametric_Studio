"""What the public release promises: no partner nodes in the open edition, a safe-for-work check on what people type, nothing private or excluded in the tree. No live ports: everything is stubbed."""
import importlib.util, json, subprocess, sys
from pathlib import Path
import pytest
from fastapi import HTTPException
from studio import apps as A, edits as E, sfw
ROOT = Path(__file__).resolve().parent.parent
def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
CHECKS = _load("repo_checks", ".github/scripts/repo_checks.py"); ASM = _load("assemble_public", "scripts/assemble_public.py")
OI = {"BriaRemoveVideoBackground": {"api_node": True, "input": {}}, "SaveImage": {"output_node": True, "input": {}}}
APP = {"extra": {"linearMode": True, "linearData": {"inputs": [], "outputs": []}}, "nodes": [{"id": 1, "type": "SaveImage"}]}
PARTNER = {"extra": {"linearMode": True, "linearData": {"inputs": [], "outputs": []}}, "nodes": [{"id": 1, "type": "sub"}], "definitions": {"subgraphs": [{"id": "sub", "nodes": [{"id": 2, "type": "BriaRemoveVideoBackground"}]}]}}

def test_open_edition_hides_partner_apps_and_an_extended_edition_can_show_them(tmp_path, monkeypatch):
    (tmp_path / "open.app.json").write_text(json.dumps(APP)); (tmp_path / "paid.app.json").write_text(json.dumps(PARTNER))
    monkeypatch.setattr(A, "_dirs", lambda: [str(tmp_path)]); monkeypatch.delenv("PSN_EDITION", raising=False)
    assert set(A.find_apps(OI)) == {"open"}
    monkeypatch.setenv("PSN_EDITION", "extended"); assert {"open", "paid"} <= set(A.find_apps(OI))

def test_partner_edit_tool_is_hidden_even_when_the_flag_cannot_be_read(tmp_path, monkeypatch):
    (tmp_path / "t.json").write_text(json.dumps(APP)); monkeypatch.setattr(E, "_path", lambda name: str(tmp_path / "t.json")); monkeypatch.delenv("PSN_EDITION", raising=False)
    monkeypatch.setattr(E.A, "object_info", lambda: {}); monkeypatch.setattr(E.A, "describe", lambda *a: {"ready": True, "runnable": True, "inputs": [], "missing_models": [], "unknown_nodes": []})
    ids = {r["id"] for r in E.catalogue({})}; assert "bgremove" not in ids and "void" in ids
    with pytest.raises(HTTPException) as e: E._find("bgremove")
    assert e.value.status_code == 404

def test_gemini_node_is_not_registered_in_the_open_edition(monkeypatch):
    src = (ROOT / "psn_nodes" / "gen" / "__init__.py").read_text(); assert '"psn_gemini_prompt_crafter"' in src and "EXTENDED_ONLY" in src

@pytest.mark.parametrize("text", ["a nude portrait", "NSFW scene", "something erotic"])
def test_sfw_check_stops_flagged_text_with_a_kind_message(text):
    with pytest.raises(HTTPException) as e: sfw.check("a fox", text)
    assert e.value.status_code == 400 and "reword" in e.value.detail

def test_sfw_check_leaves_ordinary_prompts_alone():
    sfw.check("a fox in Essex at golden hour", "", None, 5)

def test_generate_refuses_flagged_prompt_before_touching_comfyui(monkeypatch):
    from studio import server as S
    monkeypatch.setattr(S, "comfy", lambda *a, **k: pytest.fail("ComfyUI must not be called"))
    with pytest.raises(HTTPException) as e: S._graph("image", {"prompt": "a nude figure"})
    assert e.value.status_code == 400

def test_negative_prompt_may_name_what_to_keep_out(monkeypatch):
    from studio import server as S
    monkeypatch.setattr(S, "comfy", lambda *a, **k: {})
    S._graph("image", {"prompt": "a fox", "negative": "nsfw, nude"})

def test_schedule_will_not_fire_a_flagged_job(monkeypatch, tmp_path):
    from studio import schedule as SC
    monkeypatch.setattr(SC, "CONF", tmp_path); SC.save([{"id": "j", "enabled": True, "max_per_day": 3, "runs_today": 0, "goal": "image", "prompt": "a nude figure", "options": {}}])
    assert SC.fire("j", post=lambda *a: pytest.fail("must not post"), idle=lambda: True) == "skipped: not safe-for-work"

def test_borderline_pack_items_are_gone():
    raw = (ROOT / "studio" / "packs" / "packs.json").read_text()
    assert not any(x in raw for x in ("pin-up curls", "latex-look gloss", "blood-splatter makeup", "owner 20"))

def test_excluded_paths_fail_the_public_check(tmp_path):
    (tmp_path / "studio").mkdir(); (tmp_path / "studio" / "atlas.json").write_text("{}")
    assert any("excluded path" in p for p in CHECKS.public_problems(tmp_path, ["studio/atlas.json"], deny=[]))
    for f in ("docs/superpowers/x.md", "docs/SUBMISSION.md", "docs/DEMO_SCRIPT.md", ".superpowers/a", "studio/skills/a.md", "extended_candidates/a.py", "tests/gen_built/x/.cache/y"): assert CHECKS.excluded(f), f
    for f in ("README.md", "studio/server.py", "docs/CREDITS.md", "tests/gen_built/x/y.py"): assert not CHECKS.excluded(f), f

def test_private_strings_are_found_and_reports_name_only_file_and_pattern(tmp_path):
    secret, box = "mine" + "@corp-mail.net", "/" + "mnt/fast/models"
    (tmp_path / "a.py").write_text(f"x = '{secret}'\ny = '{box}'\nz = 'listed-token'\n"); (tmp_path / "b.bin").write_bytes(b"\0\0" + box.encode() + b"\0")
    out = CHECKS.public_problems(tmp_path, ["a.py", "b.bin"], deny=[b"listed-token"]); text = "\n".join(out)
    assert "a.py:1: email address" in text and "a.py:2: box path" in text and "a.py: listed private string #1" in text and "b.bin: box path inside a binary file" in text
    assert secret not in text and "listed-token" not in text and box not in text

def test_allow_list_keeps_private_paths_out_and_reports_strangers():
    keep, drop, off = ASM.select(["README.md", "studio/server.py", "studio/atlas.json", "studio/skills/a.md", "extended_candidates/a.py", "docs/SUBMISSION.md", "docs/superpowers/p.md", ".superpowers/n", "notes.txt", "studio/__pycache__/a.pyc"], CHECKS.excluded)
    assert keep == ["README.md", "studio/server.py"] and off == ["notes.txt"] and len(drop) == 7

def test_fresh_commit_has_one_commit_no_remote_and_a_neutral_author(tmp_path):
    (tmp_path / "a.txt").write_text("x"); assert ASM.fresh_commit(tmp_path) == ""
    run = lambda *a: subprocess.run(["git", "-C", str(tmp_path), *a], capture_output=True, text=True).stdout.strip()
    assert run("rev-list", "--count", "HEAD") == "1" and run("remote") == "" and run("log", "-1", "--format=%ae").endswith(".invalid")

def test_assemble_refuses_an_output_inside_the_checkout(capsys):
    assert ASM.main(["--dry-run", "--out", str(ROOT / "build")]) == 2

def test_a_clean_clone_answers_crew_questions_from_the_notes_in_the_repo(monkeypatch):
    import asyncio
    from studio import crew, crew_api as C
    root = ROOT / "studio" / "crew_notes"; monkeypatch.setattr(C, "KB_ROOT", str(root))
    def no_llm(messages): raise RuntimeError("no language model is running")
    monkeypatch.setattr(crew, "default_chat", no_llm)
    members = {m["id"]: m for m in C._get_roster()}; assert len([m for m in members.values() if m["tier"] == "family"]) >= 25 and members["minimax-h3"]["has_dossier"]
    r = asyncio.run(C.ask_crew(C.AskRequest(who="minimax-h3", question="What guidance scale should I use and which checkpoint?")))
    assert r["result"]["supported"] and r["result"]["quotes"] and r["result"]["from_notes_only"]
    r = asyncio.run(C.ask_crew(C.AskRequest(who="auto", question="How do I set the guidance scale on MiniMax-H3?")))
    assert r["member"]["id"] and r["result"]["member"] == r["member"]["id"]

def test_crew_notes_hold_only_clean_fact_files():
    root = ROOT / "studio" / "crew_notes"; files = [f for f in root.rglob("*") if f.is_file()]; assert len(files) > 50
    assert {f.name for f in files} <= {"PITFALLS.md", "PLAYBOOK.md", "PROMPTING.md", "RECIPES.md", "README.md"}
    for f in files:
        text = f.read_text(encoding="utf-8"); assert not sfw.BAD.search(text), f
        assert not CHECKS.public_problems(ROOT, [str(f.relative_to(ROOT))], deny=[]), f

def _clean_install_gaps(goal, names):
    """Graph file names that the resolver cannot map onto the files this goal's manifest entry installs."""
    import os, re
    from studio.goals import GOALS, WF
    from studio.names import resolve_names
    g = json.load(open(os.path.join(WF, GOALS[goal]["template"]))); oi = {}
    for n in g.values():
        for k, v in (n.get("inputs") or {}).items():
            if isinstance(v, str) and "${" not in v and re.search(r"\.(safetensors|ckpt|pt|pth|gguf|bin|onnx)$", v): oi.setdefault(n["class_type"], {"input": {"required": {}}})["input"]["required"][k] = [list(names), {}]
    return sorted(r["was"] for r in resolve_names(g, oi)[1] if r["now"] is None)

def test_music_works_after_a_clean_install():
    m = json.loads((ROOT / "studio" / "models_manifest.json").read_text())["goals"]["music"]
    assert not _clean_install_gaps("music", [Path(f["dest"]).name for f in m["files"]])
    from studio.names import resolve_names
    g = {"3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "minimax_music3_text_encoder_pruned_bf16.safetensors"}}}; oi = {"CLIPLoader": {"input": {"required": {"clip_name": [["minimax_music3_text_encoder_pruned_int8_convrot.safetensors"], {}]}}}}
    assert resolve_names(g, oi)[1][0]["now"] == "minimax_music3_text_encoder_pruned_int8_convrot.safetensors"      # someone who already has the smaller build keeps working

def test_music_is_labelled_with_its_upstream_licence():
    from studio.goals import GOALS
    assert GOALS["music"]["license_class"] == "community" and "community" in GOALS["music"]["license"].lower()
    assert "Apache" not in json.loads((ROOT / "studio" / "models_manifest.json").read_text())["goals"]["music"]["note"]
    assert "MiniMax H3 is licensed under the MiniMax H3 Community License Agreement" in (ROOT / "NOTICE").read_text(encoding="utf-8")

def test_every_goal_in_the_manifest_resolves_on_a_clean_install():
    from studio.goals import GOALS
    goals = json.loads((ROOT / "studio" / "models_manifest.json").read_text())["goals"]
    gaps = {g: _clean_install_gaps(g, [Path(f["dest"]).name for f in goals[g]["files"]]) for g in GOALS if g in goals}
    assert not {g: v for g, v in gaps.items() if v}

def test_paths_order_env_then_settings_then_comfyui_then_home(tmp_path, monkeypatch):
    from psn import paths
    for k in ("STUDIO_MODELS_ROOT", "PSN_MODELS_ROOT", "STUDIO_OUTPUT_DIR", "STUDIO_COMFY_INPUT"): monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path)); monkeypatch.setenv("PSN_SETTINGS", str(tmp_path / "none.env")); monkeypatch.setattr(paths, "ask_comfy", lambda timeout=2: {"models": "/srv/comfy/models", "output": "/srv/comfy/output", "input": "/srv/comfy/input"})
    assert paths.models_root() == str(tmp_path / "ComfyUI" / "models") and paths.output_dir() == str(tmp_path / "ComfyUI" / "output") and paths.comfy_input() == str(tmp_path / "ComfyUI" / "input")      # no network unless asked
    assert paths.models_root(True) == "/srv/comfy/models" and paths.output_dir(True) == "/srv/comfy/output" and paths.comfy_input(True) == "/srv/comfy/input"
    s = tmp_path / "s.env"; s.write_text("# box\nSTUDIO_MODELS_ROOT=/srv/box/models\nexport STUDIO_OUTPUT_DIR=\"/srv/box/out\"\n"); monkeypatch.setenv("PSN_SETTINGS", str(s))
    assert paths.models_root(True) == "/srv/box/models" and paths.output_dir(True) == "/srv/box/out" and paths.comfy_input(True) == "/srv/comfy/input"
    monkeypatch.setenv("STUDIO_MODELS_ROOT", "/srv/env/models"); assert paths.models_root(True) == "/srv/env/models"

def test_paths_read_what_comfyui_reports(monkeypatch):
    import io
    from psn import paths
    bodies = {"/system_stats": {"system": {"argv": ["main.py", "--output-directory", "/srv/o"]}}, "/internal/folder_paths": {"checkpoints": ["/srv/ComfyUI/models/checkpoints", "/srv/lib/checkpoints"]}}
    monkeypatch.setitem(paths._asked, "d", None); monkeypatch.setattr(paths.urllib.request, "urlopen", lambda url, timeout=2: io.BytesIO(json.dumps(bodies["/" + url.split("/", 3)[3]]).encode()))
    assert paths.ask_comfy() == {"output": "/srv/o", "models": "/srv/ComfyUI/models", "input": "/srv/ComfyUI/input"}; paths._asked["d"] = None

def test_no_box_path_is_left_in_python_defaults():
    box = CHECKS.PRIVATE
    for top in ("psn", "studio", "scripts", "psn_nodes"):
        for f in (ROOT / top).rglob("*.py"):
            if "/skills/" not in str(f) and f.name != "repo_checks.py": assert not box.search(f.read_text(encoding="utf-8", errors="ignore")), f
