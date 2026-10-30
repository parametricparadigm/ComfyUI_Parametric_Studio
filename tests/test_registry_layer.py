import json, os
import pytest
from psn import readiness, proof, catalogue

@pytest.fixture()
def lib(tmp_path, monkeypatch):
    m = tmp_path / "models"; (m / "diffusion_models").mkdir(parents=True); (m / "_complete_pipelines" / "FamA" / "vae").mkdir(parents=True)
    (m / "diffusion_models" / "a.safetensors").write_bytes(b"x" * 2000); (m / "diffusion_models" / "a.safetensors.sha256-ok").write_text("ok")
    (m / "_complete_pipelines" / "FamA" / "vae" / "v.safetensors").write_bytes(b"y" * 500)
    monkeypatch.setenv("PSN_STATE_DIR", str(tmp_path / "state")); monkeypatch.setattr(proof, "STATE", str(tmp_path / "state")); return str(m)
G = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "a.safetensors", "weight_dtype": "default"}}, "2": {"class_type": "VAELoader", "inputs": {"vae_name": "v.safetensors"}},
     "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "missing_te.safetensors", "type": "x"}}, "4": {"class_type": "UNETLoader", "inputs": {"unet_name": "${unet}"}}, "5": {"class_type": "KSampler", "inputs": {}}}

def test_required_models_skips_placeholders_and_non_loaders():
    r = readiness.required_models(G); assert [x["value"] for x in r] == ["a.safetensors", "v.safetensors", "missing_te.safetensors"]

def test_readiness_finds_present_missing_and_hashes(lib):
    rep = readiness.check(G, lib, hint_map={"missing_te.safetensors": "org/repo"}); assert not rep["ready"] and [m["value"] for m in rep["missing"]] == ["missing_te.safetensors"] and rep["missing"][0]["hint"] == "org/repo"
    a = next(m for m in rep["models"] if m["value"] == "a.safetensors"); assert a["present"] and a["hash_verified"] and a["size_gb"] == 0.0
    assert next(m for m in rep["models"] if m["value"] == "v.safetensors")["present"]                  # found inside a family pipeline folder
    ok = {k: v for k, v in G.items() if k != "3"}; assert readiness.check(ok, lib, hint_map={})["ready"] and "READY" in readiness.render_md("w", readiness.check(ok, lib, hint_map={}))
    assert "MISSING" in readiness.render_md("w", rep) and "org/repo" in readiness.render_md("w", rep)

def test_proof_levels_expire_when_evidence_goes_stale(lib, tmp_path):
    ok = {k: v for k, v in G.items() if k != "3"}; rep = readiness.check(ok, lib, hint_map={}); assert proof.level("wf", ok)[0] == "recipe"
    proof.record_load_test("wf", ok, [], rep); assert proof.level("wf", ok)[0] == "load-tested"
    out = tmp_path / "o.mp4"; out.write_bytes(b"video"); proof.record_run("wf", ok, [str(out)], seconds=12.5, notes="demo")
    lv, why = proof.level("wf", ok); assert lv == "verified" and "1 output" in why
    os.utime(out, (1_700_000_000, 1_700_000_000)); old = proof.record_run("wf", ok, [str(out)]); assert old["ts"].startswith("2023-11-1") and old["recorded"] > old["ts"]            # the run time is the output's own time
    changed = json.loads(json.dumps(ok)); changed["5"]["inputs"]["steps"] = 9; assert proof.level("wf", changed)[0] == "recipe"           # edited workflow: neither label applies to the new version
    out.write_bytes(b"VIDEO!"); assert proof.level("wf", ok)[0] == "load-tested" and "gone or changed" in proof.level("wf", ok)[1]          # output tampered: falls back
    out.unlink(); assert proof.level("wf", ok)[0] == "load-tested"
    with pytest.raises(ValueError, match="no output files"): proof.record_run("wf", ok, [str(out)])
    bad = readiness.check(G, lib, hint_map={}); proof.record_load_test("wf2", G, [], bad); assert proof.level("wf2", G)[0] == "recipe"       # missing model: cannot be load-tested

def test_catalogue_rows_and_markdown(lib, tmp_path):
    wd = tmp_path / "wf"; wd.mkdir(); (wd / "demo_api.json").write_text(json.dumps({k: v for k, v in G.items() if k in ("1", "2")}))
    oi = {"UNETLoader": {"input": {"required": {"unet_name": ["STRING"], "weight_dtype": ["STRING"]}}, "output": ["MODEL"]}, "VAELoader": {"input": {"required": {"vae_name": ["STRING"]}}, "output": ["VAE"]}}
    rows = catalogue.build(str(wd), oi, {}, lib); assert rows[0]["id"] == "demo_api" and rows[0]["ready"] and rows[0]["proof"] == "load-tested" and rows[0]["nodes"] == 2
    md = catalogue.to_md(rows); assert "| `demo_api` |" in md and "**load-tested**" in md
    rows2 = catalogue.build(str(wd), {"UNETLoader": {"input": {"required": {}}, "output": ["MODEL"]}}, {}, lib); assert rows2[0]["validation_problems"] and rows2[0]["proof"] == "recipe"
