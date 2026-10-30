import json, os
import pytest, torch
from safetensors.torch import save_file
from psn import modelsort_agent as A, instances
from psn.subagents.runner import Result
from psn.subagents import ROLES

def mk(path, shape=(8, 8), name="a.weight"):
    os.makedirs(os.path.dirname(path), exist_ok=True); save_file({name: torch.zeros(*shape).half()}, path); open(path, "ab").write(b"\0" * 1_200_000)       # padded past the 1 MB floor (header length stays valid)
@pytest.fixture()
def lib(tmp_path, monkeypatch):
    root = tmp_path / "f"
    mk(str(root / "chatter" / "model.safetensors")); open(root / "chatter" / "MODEL.md", "w").write("Chatterbox TTS model, voice cloning text to speech")
    mk(str(root / "multi" / "BiRefNet" / "birefnet.safetensors")); mk(str(root / "multi" / "moge" / "moge.safetensors")); mk(str(root / "multi" / "NODES" / "skip.safetensors")); open(root / "multi" / "README_MODEL_NOTES.md", "w").write("BiRefNet: background removal\nmoge: depth")
    mk(str(root / "repo" / "unet" / "w.safetensors")); mk(str(root / "repo" / "vae" / "v.safetensors")); json.dump({"_class_name": "SomePipeline"}, open(root / "repo" / "model_index.json", "w"))
    mk(str(root / "loose.safetensors"))
    m = tmp_path / "models"; (m / "_complete_pipelines" / "SDXL").mkdir(parents=True); monkeypatch.setattr(instances, "MODELS", str(m)); monkeypatch.setattr(A.MS, "MODELS", str(m)); monkeypatch.setenv("HOME", str(tmp_path))
    return root, m
def test_units_split_models_skip_junk_and_keep_repos_whole(lib):
    root, _ = lib; u = {x["name"]: len(x["files"]) for x in A.find_units(str(root))}
    assert u == {"f/chatter": 1, "f/multi/BiRefNet": 1, "f/multi/moge": 1, "f/repo": 2, "f/loose.safetensors": 1}                  # NODES skipped; repo with model_index.json kept whole; loose file is its own unit
def good(role, task, ctx=None, **k):
    src = ctx["source"]; fam = "Chatterbox" if "Chatterbox" in src else "BiRefNet" if "BiRefNet" in src else "SDXL" if "SomePipeline" in src else "Mystery"; ev = "Chatterbox TTS model" if fam == "Chatterbox" else ("birefnet.safetensors" if fam == "BiRefNet" else "SomePipeline" if fam == "SDXL" else "loose.safetensors")
    return Result(True, role, {"family": fam, "new_family": fam not in ctx["labels"], "group": "tts-voice" if fam == "Chatterbox" else "segmentation-matting" if fam == "BiRefNet" else "image", "kind": "x", "confidence": "high" if fam != "Mystery" else "low", "evidence": [ev, "NAME: " + src.split("\n")[0][6:]]})
def test_sorting_links_only_confident_decisions_and_undo_removes_exactly_those(lib):
    root, m = lib; rows, plan, made = A.sort_folders([str(root)], apply=True, runner=good, models=str(m))
    by = {r["unit"]: r for r in rows}; assert by["f/chatter"]["family"] == "Chatterbox" and by["f/chatter"]["new_family"] and by["f/repo"]["family"] == "SDXL" and not by["f/repo"]["new_family"]
    assert os.path.islink(m / "_complete_pipelines/_tools/Chatterbox/weights/model.safetensors") and os.path.exists(m / "_complete_pipelines/_tools/Chatterbox/NOTES/chatter_MODEL.md")           # tool family: weights/ + notes
    assert os.path.islink(m / "_complete_pipelines/SDXL/diffusion_models/w.safetensors") or os.path.islink(m / "_complete_pipelines/SDXL/vae/v.safetensors")                         # comfy group: role folders
    assert not (m / "_complete_pipelines/Mystery").exists()                                                                                                                       # low confidence: reported, not linked
    assert (root / "chatter" / "model.safetensors").exists() and not os.path.islink(root / "chatter" / "model.safetensors")                                                        # sources untouched
    mp = sorted(f for f in os.listdir(os.environ["HOME"] + "/Documents") if f.startswith("MODEL_SORT_LINKS"))[-1]; n = A.undo(os.environ["HOME"] + "/Documents/" + mp); assert n == len(made) and not os.path.lexists(m / "_complete_pipelines/_tools/Chatterbox/weights/model.safetensors")
def test_dry_run_creates_nothing(lib):
    root, m = lib; rows, plan, made = A.sort_folders([str(root)], apply=False, runner=good, models=str(m)); assert plan and made == [] and not (m / "_complete_pipelines/_tools").exists()
def test_sorter_role_rejects_invented_evidence_and_unknown_families():
    v = ROLES["model_sorter"].verify; ctx = {"source": "NAME: x\nFILES:\nbirefnet.safetensors 0.2 GB", "labels": ["SDXL"]}; ok = {"family": "BiRefNet", "new_family": True, "group": "segmentation-matting", "kind": "k", "confidence": "medium", "evidence": ["birefnet.safetensors"]}
    assert v(ok, ctx) == [] and any("not found" in p for p in v({**ok, "evidence": ["made up line"]}, ctx)) and any("not an existing family" in p for p in v({**ok, "new_family": False}, ctx)) and any("already exists" in p for p in v({**ok, "family": "SDXL"}, ctx))
    assert any("two evidence" in p for p in v({**ok, "confidence": "high"}, ctx)) and any("group must be" in p for p in v({**ok, "group": "banana"}, ctx)) and any("short name" in p for p in v({**ok, "family": "../etc"}, ctx))

def test_canonical_names_and_report_roundtrip(lib, tmp_path, monkeypatch):
    (tmp_path / "kb" / "families" / "chatterbox").mkdir(parents=True); monkeypatch.setenv("PSN_KB_ROOT", str(tmp_path / "kb"))      # the label comes from the knowledge base; never read the real one
    root, m = lib; rows = [{"family": "sapiens2", "new_family": True}, {"family": "Sapiens2", "new_family": True}, {"family": "sdxl", "new_family": True}]
    out = A.canonicalize(rows, ["SDXL"]); assert [r["family"] for r in out] == ["sapiens2", "sapiens2", "SDXL"] and out[2]["new_family"] is False
    rep = tmp_path / "r.json"; json.dump([{"unit": "f/chatter", "path": str(root / "chatter"), "ok": True, "family": "Chatterbox", "new_family": True, "group": "tts-voice", "confidence": "high", "evidence": ["x"], "kind": "k", "files": 1, "gb": 0.0, "problems": []}], open(rep, "w"))
    rows, plan, made = A.apply_report(str(rep), str(m), apply=True); assert made and os.path.islink(m / "_complete_pipelines/_tools/chatterbox/weights/model.safetensors")
def test_new_family_without_a_denoiser_stays_out_of_the_main_list(lib):
    root, m = lib; row = {"unit": "u", "path": str(root / "loose.safetensors"), "ok": True, "family": "Interp", "new_family": True, "group": "video", "confidence": "high", "weights": [str(root / "loose.safetensors")]}
    plan = A.plan_links([dict(row, weights=[str(root / "chatter" / "model.safetensors")])], str(m)); assert plan and "_tools/Interp" in plan[0][1] or "Interp" in plan[0][1]
