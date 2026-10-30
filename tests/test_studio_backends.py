import json, os, time
from studio import backends as B

class Out:
    def __init__(self, name): self.name, self.type, self.content_type = name, "output", "video/mp4"
    def to_file(self, p): open(p, "wb").write(b"mp4")
class Job:
    id = "job-1"; outputs = [Out("a.mp4")]
    def wait(self): return self
    def cancel(self): self.cancelled = True
class WF:
    def __init__(self, g): self.g, self.sets = g, []
    def set_input(self, n, f, v): self.sets.append((n, f, v))
class Client:
    def __init__(self): self.seen = None; self.workflows = self; self.assets = self
    def from_json(self, g): self.seen = WF(g); return self.seen
    def from_file(self, p): return "ASSET:" + os.path.basename(p)
    def submit(self, wf): return Job()

def wait_done(jid):
    for _ in range(100):
        if B.status(jid)["status"] != "running": return B.status(jid)
        time.sleep(0.02)
    raise AssertionError("job did not finish")

def test_default_is_local_and_no_credits(monkeypatch):
    monkeypatch.delenv("STUDIO_BACKEND", raising=False); assert not B.use_sdk() and B.target() == {"backend": "local", "target": "local", "spends_credits": False}

def test_targets_and_no_secret(monkeypatch):
    monkeypatch.setenv("STUDIO_BACKEND", "sdk"); monkeypatch.setenv("COMFY_API_KEY", "comfyui-secret"); monkeypatch.delenv("COMFY_BASE_URL", raising=False)
    t = B.target(); assert t["target"] == "cloud" and t["spends_credits"] and t["key_set"] and "comfyui-secret" not in json.dumps(t)
    monkeypatch.setenv("COMFY_BASE_URL", "https://x.run.comfy.app"); assert B.target()["target"] == "deployment"
    monkeypatch.setenv("COMFY_BASE_URL", "http://127.0.0.1:8397"); t = B.target(); assert t["target"] == "self-hosted" and not t["spends_credits"]

def test_submit_uploads_become_assets_and_outputs_are_collected(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "OUT", tmp_path / "out"); (tmp_path / "clip.mp4").write_bytes(b"x"); c = Client()
    g = {"3": {"class_type": "LoadVideo", "inputs": {"file": "clip.mp4", "n": 1}}, "4": {"class_type": "Other", "inputs": {"text": "hi"}}}
    jid = B.submit(g, ["clip.mp4", None], str(tmp_path), {"goal": "recast", "prompt": "p"}, client=c)
    assert c.seen.sets == [("3", "file", "ASSET:clip.mp4")]
    s = wait_done(jid); assert s["status"] == "done" and s["files"][0]["url"] == f"/api/sdk_output/{jid}/a.mp4" and s["files"][0]["kind"] == "video" and "job" not in s and "client" not in s
    assert (tmp_path / "out" / jid / "a.mp4").read_bytes() == b"mp4" and B.history()[-1]["goal"] == "recast"

def test_missing_upload_fails_before_submit(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError): B.submit({}, ["nope.png"], str(tmp_path), client=Client())

def test_output_route_refuses_traversal():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException): B.sdk_output("unknown", "a.mp4")
    B.JOBS["j"] = {"status": "done", "files": []}
    with pytest.raises(HTTPException): B.sdk_output("j", "../../secret")
