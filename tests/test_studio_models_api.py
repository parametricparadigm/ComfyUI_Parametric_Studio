"""Models readiness and downloads. huggingface_hub, the disk and ComfyUI are stubbed: nothing here touches the network, a real account or a real models folder."""
import hashlib, threading, time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import apps as A, models_api as M

GB = 2**30
MAN = {"demo": {"note": "Demo model", "files": [
    {"role": "unet", "repo": "o/r", "path": "split/diffusion_models/big.safetensors", "dest": "diffusion_models/big.safetensors", "size_gb": 3.0, "sha256": "", "gated": False},
    {"role": "text_encoder", "repo": "o/r", "path": "split/text_encoders/enc.safetensors", "dest": "text_encoders/enc.safetensors", "size_gb": 1.0, "sha256": "", "gated": False},
    {"role": "vae", "repo": "gate/keeper", "path": "vae/v.safetensors", "dest": "vae/v.safetensors", "size_gb": 0.5, "sha256": "", "gated": True}]}}
OI = {"UNETLoader": {"input": {"required": {"unet_name": [["other/big.safetensors"], {}]}}}, "CLIPLoader": {"input": {"required": {"clip_name": [["nothing.safetensors"], {}]}}}, "VAELoader": {"input": {"required": {"vae_name": [["nothing.safetensors"], {}]}}}}

@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_MODELS_ROOT", str(tmp_path / "models")); monkeypatch.setenv("STUDIO_STATE_DIR", str(tmp_path / "state")); monkeypatch.delenv("STUDIO_ALLOW_DOWNLOAD", raising=False)
    M._M.clear(); M._M["m"] = MAN; M._DL.clear(); M._DL["state"] = "idle"; M._CANCEL.clear(); M._SAMP.clear()
    monkeypatch.setattr(M, "GOALS", {"demo": {}, "unlisted": {}}); monkeypatch.setattr(M.A, "object_info", lambda: OI); monkeypatch.setattr(M, "free_bytes", lambda p: 500 * GB); monkeypatch.setattr(M.E, "TOOLS", [])
    app = FastAPI(); app.include_router(M.router); return TestClient(app)

def fake_download(content=b"x" * 64, hold=None, fail=None):
    def dl(f, stage, progress, cancelled):
        if fail: raise fail
        p = stage / f["path"]; p.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(4):
            if hold: hold.wait(5)
            if cancelled(): raise M.Cancelled()
            progress(len(content) // 4)
        p.write_bytes(content); return str(p)
    return dl

def wait_for(states, timeout=5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if M.status()["state"] in states: return M.status()
        time.sleep(0.02)
    raise AssertionError(f"still {M.status()}")

def test_readiness_counts_a_nested_file_as_installed_and_sums_only_the_missing(api):
    d = api.get("/api/models/readiness").json(); g = d["goals"]["demo"]
    assert g["known"] and not g["ready"] and g["files"] == 3 and g["missing"] == 2          # other/big.safetensors satisfies diffusion_models/big.safetensors
    assert g["total_gb"] == 4.5 and g["missing_gb"] == 1.5 and g["gated"] and g["license_url"] == "https://huggingface.co/gate/keeper"
    assert [i["present"] for i in g["items"]] == [True, False, False] and d["goals"]["unlisted"] == {"id": "unlisted", "kind": "goal", "known": False}
    assert d["root"].endswith("models") and d["reserve_gb"] == 25 and d["download"]["state"] == "idle"

def test_a_close_name_that_is_another_variant_is_not_a_match():
    assert A.variant_ok("minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "minimax_h3/minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors")
    assert not A.variant_ok("lightx2v_T2V_14B_distill.safetensors", "lightx2v_I2V_14B_distill.safetensors") and not A.variant_ok("wan_fun_high_noise_14B.safetensors", "wan_fun_low_noise_14B.safetensors")

def test_download_fetches_only_what_is_missing_into_the_models_folder(api, monkeypatch, tmp_path):
    monkeypatch.setattr(M, "hf_download", fake_download())
    r = api.post("/api/models/download", json={"goal": "demo"}); assert r.status_code == 200 and r.json() == {"started": True, "files": 2, "need_gb": 1.5}
    s = wait_for({"done", "error"}); assert s["state"] == "done", s
    root = tmp_path / "models"; assert (root / "text_encoders/enc.safetensors").read_bytes() == b"x" * 64 and (root / "vae/v.safetensors").exists()
    assert not (root / "diffusion_models/big.safetensors").exists()                           # the nested copy ComfyUI already lists was not fetched again
    assert not (root / "text_encoders/.psn_part/o__r").exists()                               # the staging folder is cleaned up
    assert api.post("/api/models/download", json={"goal": "demo"}).json()["started"] is False  # nothing is missing now

def test_progress_speed_and_one_download_at_a_time_and_cancel(api, monkeypatch):
    hold = threading.Event(); monkeypatch.setattr(M, "hf_download", fake_download(hold=hold))
    assert api.post("/api/models/download", json={"goal": "demo"}).status_code == 200
    s = wait_for({"running"}); assert s["total"] == int(1.5 * GB) and s["file"] and s["count"] == 2
    assert api.post("/api/models/download", json={"goal": "demo"}).status_code == 409           # one at a time
    assert api.post("/api/models/download/cancel").json()["state"] == "cancelling"
    hold.set(); assert wait_for({"cancelled", "done", "error"})["state"] == "cancelled"
    assert api.get("/api/models/download").json()["state"] == "cancelled"

def test_refuses_when_the_disk_would_drop_under_the_need_plus_25_gb(api, monkeypatch, tmp_path):
    monkeypatch.setattr(M, "free_bytes", lambda p: int(26 * GB)); monkeypatch.setattr(M, "hf_download", fake_download())
    r = api.post("/api/models/download", json={"goal": "demo"}); assert r.status_code == 507 and "not enough disk space" in r.json()["detail"] and "26" in r.json()["detail"]
    assert M.status()["state"] == "idle" and not (tmp_path / "models/vae/v.safetensors").exists()

def test_a_gated_repo_says_to_accept_the_licence_and_log_in(api, monkeypatch):
    class GatedRepoError(Exception): pass
    monkeypatch.setattr(M, "hf_download", fake_download(fail=GatedRepoError("401 gated")))
    api.post("/api/models/download", json={"goal": "demo"}); s = wait_for({"needs_license", "error", "done"})
    assert s["state"] == "needs_license" and s["license_url"] == "https://huggingface.co/o/r" and "accept the licence" in s["error"] and "hf auth login" in s["error"] and "token" in s["error"]

def test_a_bad_checksum_is_removed_and_reported(api, monkeypatch, tmp_path):
    M._M["m"] = {"demo": {"files": [{**MAN["demo"]["files"][1], "sha256": hashlib.sha256(b"other").hexdigest()}]}}
    monkeypatch.setattr(M, "hf_download", fake_download()); api.post("/api/models/download", json={"goal": "demo"}); s = wait_for({"error", "done"})
    assert s["state"] == "error" and "checksum mismatch" in s["error"] and not (tmp_path / "models/text_encoders/enc.safetensors").exists()

def test_download_switch_and_bad_requests(api, monkeypatch):
    assert api.post("/api/models/download", json={}).status_code == 400 and api.post("/api/models/download", json={"goal": "nope"}).status_code == 400
    assert api.post("/api/models/download", json={"goal": "unlisted"}).status_code == 409 and api.post("/api/models/download", json={"edit": "nope"}).status_code in (400, 503)
    monkeypatch.setenv("STUDIO_ALLOW_DOWNLOAD", "0"); assert api.post("/api/models/download", json={"goal": "demo"}).status_code == 403

def test_edit_tool_files_come_from_its_template_links_and_sizes_are_looked_up(api, monkeypatch):
    desc = {"models": ["a.safetensors", "b.safetensors"], "missing_models": ["b.safetensors"], "unknown_nodes": [], "runnable": False, "hints": {"b.safetensors": {"url": "https://huggingface.co/o/r/resolve/main/sub/b.safetensors?download=true", "directory": "loras"}, "a.safetensors": {"url": "https://huggingface.co/o/r/resolve/main/a.safetensors", "directory": "vae"}}}
    monkeypatch.setattr(M.E, "TOOLS", [("t", "c", "Tool", "tpl", "blurb")]); monkeypatch.setattr(M.E, "_find", lambda tid: (None, "p")); monkeypatch.setattr(M.A, "describe", lambda *a: desc)
    monkeypatch.setattr(M, "hf_sizes", lambda items: {(r, v, p): (2 * GB, "ab" * 32) for r, v, p in items})
    M.fill_sizes([], wait=True); fs, d = M.edit_files("t", OI); miss = [f for f in fs if not f["present"]]
    assert [f["name"] for f in miss] == ["b.safetensors"] and miss[0]["repo"] == "o/r" and miss[0]["path"] == "sub/b.safetensors" and miss[0]["dest"] == "loras/b.safetensors"
    M.fill_sizes(miss, wait=True); assert miss[0]["size"] == 2 * GB and M.summary("edit", "t", fs)["missing_gb"] == 2.0
    assert M.parse_hf("https://example.com/o/r/resolve/main/x.safetensors") is None

def test_attach_tests_a_comfyui_lists_what_it_lacks_and_switches_the_studio(api, monkeypatch, tmp_path):
    stats = {"system": {"comfyui_version": "9.9"}, "devices": [{"name": "Test GPU", "vram_total": 24 * GB, "vram_free": 20 * GB}]}
    monkeypatch.setattr(M, "fetch_json", lambda url, t: stats if url.endswith("/system_stats") else OI); monkeypatch.setattr(M, "GOALS", {"demo": {"label": "Demo", "template": "nope.json"}})
    r = api.post("/api/models/attach/test", json={"url": "http://127.0.0.1:8188/"}).json()
    assert r["ok"] and r["gpu"] == {"name": "Test GPU", "vram_total_gb": 24.0, "vram_free_gb": 20.0} and r["nodes"] == 3 and r["version"] == "9.9" and r["goals"][0]["missing_models"] == ["enc.safetensors", "v.safetensors"] and r["ready_goals"] == 0
    assert api.post("/api/models/attach/test", json={"url": "http://example.com"}).status_code == 400 and api.post("/api/models/attach/test", json={"url": "ftp://x"}).status_code == 400   # remote hosts and other schemes refused
    monkeypatch.setattr(M.AT, "CONFIG_DIR", tmp_path / "cfg"); monkeypatch.setattr(M.AT, "CONFIG_FILE", tmp_path / "cfg" / "attach.json"); monkeypatch.setattr(M.A, "COMFY", "http://127.0.0.1:8200"); monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:8200")       # setenv first, so the test leaves the environment as it found it
    u = api.post("/api/models/attach", json={"url": "http://127.0.0.1:8188"}).json(); assert u["switched"] and M.A.COMFY == "http://127.0.0.1:8188" and M.os.environ["COMFYUI_URL"] == "http://127.0.0.1:8188" and api.get("/api/models/attach").json()["saved"] == "http://127.0.0.1:8188"
    monkeypatch.setattr(M, "fetch_json", lambda url, t: (_ for _ in ()).throw(OSError("down"))); assert api.post("/api/models/attach", json={"url": "http://127.0.0.1:9"}).status_code == 502
    M.switch(M.ORIGINAL["url"])
