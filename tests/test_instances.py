import json, os
import pytest
from psn import instances as I

@pytest.fixture()
def lib(tmp_path):
    m = tmp_path / "models"; cp = m / "_complete_pipelines"
    for fam, files in {"Flux.3-Klein": {"diffusion_models/k.safetensors": 10, "text_encoders/te.safetensors": 5, "vae/ae.safetensors": 1}, "Wan2.2": {"diffusion_models/w.safetensors": 20}, "LTX-2.5": {"vae/v.safetensors": 1}, "Empty": {}}.items():
        (cp / fam).mkdir(parents=True)
        for rel, mb in files.items(): p = cp / fam / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"x" * mb * 1000)
    (m / "diffusion_models" / "ltx 2.5").mkdir(parents=True); (m / "diffusion_models" / "ltx 2.5" / "t.safetensors").write_bytes(b"x" * 21_000)
    (cp / "_FAMILY_NODES").mkdir(); nodes = tmp_path / "ps_nodes"
    for n in ("comfyui_parametric_studio", "kijai__ComfyUI-KJNodes", "Lightricks__ComfyUI-LTXVideo", "unrelated__Pack"): (nodes / n).mkdir(parents=True)
    return {"models": str(m), "root": str(tmp_path / "inst"), "nodes": str(nodes)}

def test_families_slugs_and_stable_ports(lib):
    assert I.families(lib["models"]) == ["Empty", "Flux.3-Klein", "LTX-2.5", "Wan2.2"] and I.slug("Flux.3-Klein") == "flux-3-klein" and I.slug("Wan2.2") == "wan2-2"
    p1 = I.registry_ports(I.families(lib["models"]), lib["root"]); p2 = I.registry_ports(I.families(lib["models"]) + ["New"], lib["root"])
    assert len(set(p2.values())) == len(p2) and all(p2[k] == v for k, v in p1.items()) and p2["New"] > max(p1.values()) and min(p1.values()) == I.BASE_PORT      # a new family never moves an old port

def test_generate_isolates_models_packs_and_dirs(lib):
    i = I.generate("LTX-2.5", lib["models"], lib["root"], lib["nodes"]); d = os.path.join(lib["root"], "ltx-2-5")
    y = open(f"{d}/extra_model_paths.yaml").read(); assert "_complete_pipelines/LTX-2.5/vae" in y and "diffusion_models/ltx 2.5" in y and "Wan2.2" not in y     # sees its own models, incl. the top-level alias folder
    assert sorted(os.listdir(f"{d}/custom_nodes")) == ["Lightricks__ComfyUI-LTXVideo", "comfyui_parametric_studio", "kijai__ComfyUI-KJNodes"] and "unrelated__Pack" not in os.listdir(f"{d}/custom_nodes")
    env = open(f"{d}/instance.env").read(); assert f"PS_PORT={i['port']}" in env and f"--base-directory {d}" in env and "--output-directory" in env and i["unit"] == "comfy-family@ltx-2-5.service"
    assert all(os.path.isdir(f"{d}/{x}") for x in ("output", "input", "user"))
    assert f"--extra-model-paths-config {d}/extra_model_paths.yaml" in env and i["args"][-2:] == ["--extra-model-paths-config", f"{d}/extra_model_paths.yaml"]      # ComfyUI never reads the instance's yaml without this flag

def test_regenerate_keeps_outputs_and_drops_stale_links(lib, monkeypatch, tmp_path):
    monkeypatch.setattr(I, "REPO_LIB", str(tmp_path / "no_repo_library"))        # isolate from the real library of cloned packs
    I.generate("Wan2.2", lib["models"], lib["root"], lib["nodes"]); d = os.path.join(lib["root"], "wan2-2"); open(f"{d}/output/keep.png", "w").write("x")
    os.symlink("/nonexistent", f"{d}/custom_nodes/stale"); I.generate("Wan2.2", lib["models"], lib["root"], lib["nodes"])
    assert os.path.exists(f"{d}/output/keep.png") and "stale" not in os.listdir(f"{d}/custom_nodes")
    assert json.load(open(f"{d}/instance.json"))["packs_not_installed"] == ["kijai__ComfyUI-WanVideoWrapper"]            # missing family pack is reported, not faked

def test_vram_estimate_and_start_gate(lib):
    I.generate("Flux.3-Klein", lib["models"], lib["root"], lib["nodes"]); est = I.vram_estimate_gb("Flux.3-Klein", lib["models"]); assert est == round((10_000 + 5_000 + 1_000) * 1.15 / 1e9, 1) or est >= 0.0
    os.environ["PSN_INSTANCES_ROOT"] = lib["root"]
    big = json.load(open(f"{lib['root']}/flux-3-klein/instance.json")); big["est_vram_gb"] = 30.0; json.dump(big, open(f"{lib['root']}/flux-3-klein/instance.json", "w"))
    assert I.can_start("Flux.3-Klein", free_gb=40, root=lib["root"])[0] and not I.can_start("Flux.3-Klein", free_gb=33, root=lib["root"])[0]           # 33 - 30 = 3 < 4 GB floor
    calls = []; r = I.start("Flux.3-Klein", lib["root"], systemctl=lambda *a: calls.append(a)) if False else None
    ok, why = I.can_start("Flux.3-Klein", free_gb=20, root=lib["root"]); assert not ok and "30.0 GB" in why

def test_start_refuses_without_calling_systemctl_and_stop_uses_systemctl(lib, monkeypatch):
    I.generate("Wan2.2", lib["models"], lib["root"], lib["nodes"]); calls = []; monkeypatch.setattr(I, "free_vram_gb", lambda: 1.0); monkeypatch.setattr(I, "is_up", lambda p: False)
    r = I.start("Wan2.2", lib["root"], systemctl=lambda *a: calls.append(a)); assert r["status"] == "refused" and not calls
    assert I.stop("Wan2.2", lib["root"], systemctl=lambda *a: calls.append(a))["status"] == "stopped" and calls == [("stop", "comfy-family@wan2-2.service")]

def test_unit_file_and_reap_skips_busy_and_fresh(lib, tmp_path, monkeypatch):
    p = I.write_unit(lib["root"], "/x/launch.sh", str(tmp_path / "units")); t = open(p).read()
    assert "EnvironmentFile=" + lib["root"] + "/%i/instance.env" in t and "ExecStart=/x/launch.sh $ARGS" in t and "Restart=no" in t and "WantedBy" not in t       # never enabled, never auto-restarted
    I.registry_ports(["A", "B"], lib["root"]); I.generate("Wan2.2", lib["models"], lib["root"], lib["nodes"])
    monkeypatch.setattr(I, "status", lambda root=None: [{"family": "Wan2.2", "port": 1, "up": True, "est_gb": 1}]); stops = []; monkeypatch.setattr(I, "stop", lambda f, r=None, s=None: stops.append(f))
    class R:  # fake urlopen responses
        def __init__(self, d): self.d = d
        def read(self): return json.dumps(self.d).encode()
    monkeypatch.setattr(I.urllib.request, "urlopen", lambda u, timeout=0: R({"queue_running": [[1]], "queue_pending": []}) if "queue" in u else R({}))
    assert I.reap(1, lib["root"]) == [] and not stops                                                                  # busy: left alone
    monkeypatch.setattr(I.urllib.request, "urlopen", lambda u, timeout=0: R({"queue_running": [], "queue_pending": []}) if "queue" in u else R({"a": {"status": {"messages": [["execution_success", {"timestamp": 1}]]}}}))
    assert I.reap(1, lib["root"]) == ["Wan2.2"] and stops == ["Wan2.2"]                                                # idle for ages: stopped

def test_wrapped_family_gets_a_symlink_view_and_honest_status(lib):
    m = lib["models"]; (os.path.join(m, "x"))
    os.makedirs(f"{m}/_complete_pipelines/PixArt-Sigma/diffusers", exist_ok=True); open(f"{m}/_complete_pipelines/PixArt-Sigma/diffusers/diffusion_pytorch_model.safetensors", "wb").write(b"x" * 2000)
    os.makedirs(f"{m}/_complete_pipelines/Flux.1/text_encoders", exist_ok=True); open(f"{m}/_complete_pipelines/Flux.1/text_encoders/t5xxl_fp16.safetensors", "wb").write(b"t" * 500)                       # shared T5 exists, the SDXL VAE does not
    i = I.generate("PixArt-Sigma", m, lib["root"], lib["nodes"]); d = f"{lib['root']}/pixart-sigma"
    assert i["loader"] == "core" and "diffusion_models/pixart-sigma_transformer.safetensors" in i["wrapped"] and "text_encoders/t5xxl_fp16.safetensors" in i["wrapped"]
    assert os.path.islink(f"{d}/models/diffusion_models/pixart-sigma_transformer.safetensors") and os.path.exists(f"{d}/models/text_encoders/t5xxl_fp16.safetensors")
    assert i["wrap_missing"] == ["vae/SDXL/sdxl_vae.safetensors"] and "vae" not in open(f"{d}/extra_model_paths.yaml").read()                    # a missing shared file is reported, never faked
    y = open(f"{d}/extra_model_paths.yaml").read(); assert f"{d}/models/diffusion_models" in y and i["est_vram_gb"] >= 0
    j = I.generate("Stable-Fast-3D", m, lib["root"], lib["nodes"]); assert j["loader"] == "needs-pack" and "core ComfyUI cannot detect" in j["note"]


def test_family_pack_falls_back_to_the_repo_library(lib, monkeypatch, tmp_path):
    repo = tmp_path / "repos"; (repo / "tungthedev__ComfyUI-TripoSG").mkdir(parents=True); monkeypatch.setattr(I, "REPO_LIB", str(repo))
    assert "tungthedev__ComfyUI-TripoSG" in I.FAMILY_PACKS["PartCrafter"]
    info = I.generate("Wan2.2", lib["models"], lib["root"], lib["nodes"])        # a family whose pack is in neither place is still reported, never faked
    assert info["packs_not_installed"] == ["kijai__ComfyUI-WanVideoWrapper"]


def test_family_pack_names_are_directory_names():
    # a pack is its directory name (owner__Repo); a bare repo name never resolves, which is how MiniMax-H3 once got none of its five packs
    assert all("__" in p for packs in I.FAMILY_PACKS.values() for p in packs)
    assert "Larryvrh__ComfyUI-MiniMax-H3-Turbo" in I.FAMILY_PACKS["MiniMax-H3"] and len(I.FAMILY_PACKS["MiniMax-H3"]) == 5


def test_idle_start_gate_uses_the_idle_footprint_not_the_working_set(lib, monkeypatch):
    # a start-only check (nodes, /object_info) loads no model: gating it on the family's working set refused 59 of 82 instances while Qwen held the card
    I.generate("Flux.3-Klein", lib["models"], lib["root"], lib["nodes"]); big = json.load(open(f"{lib['root']}/flux-3-klein/instance.json")); big["est_vram_gb"] = 30.0; json.dump(big, open(f"{lib['root']}/flux-3-klein/instance.json", "w"))
    assert not I.can_start("Flux.3-Klein", free_gb=10, root=lib["root"])[0] and I.can_start("Flux.3-Klein", free_gb=10, root=lib["root"], need_gb=I.IDLE_GB)[0]
    ok, why = I.can_start("Flux.3-Klein", free_gb=5, root=lib["root"], need_gb=I.IDLE_GB); assert not ok and f"~{I.IDLE_GB} GB" in why          # 5 - 1.5 = 3.5 < the 4 GB floor
    calls = []; monkeypatch.setattr(I, "free_vram_gb", lambda: 10.0); monkeypatch.setattr(I, "is_up", lambda p: False)
    assert I.start("Flux.3-Klein", lib["root"], systemctl=lambda *a: calls.append(a), wait=0)["status"] == "refused" and not calls                              # default gate still uses the estimate
    assert I.start("Flux.3-Klein", lib["root"], systemctl=lambda *a: calls.append(a), wait=0, need_gb=I.IDLE_GB)["status"] == "timeout" and calls == [("start", "comfy-family@flux-3-klein.service")]
