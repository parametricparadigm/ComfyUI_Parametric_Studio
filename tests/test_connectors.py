import io, json, hashlib, urllib.error, pytest
from psn.connectors import civitai, hf, net, registry

class Resp(io.BytesIO):
    def __init__(self, b, headers=None): super().__init__(b); self.headers = headers or {"Content-Length": str(len(b))}
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

class FakeOpener:
    def __init__(self, routes): self.routes = routes; self.calls = []
    def open(self, req, timeout=0):
        self.calls.append((req.full_url, dict(req.header_items())))
        r = self.routes[req.full_url.split("?")[0]]
        if isinstance(r, Exception): raise r
        return r() if callable(r) else Resp(r)

def redirect(to): return urllib.error.HTTPError("u", 302, "found", {"Location": to}, None)

MODEL = {"items": [
    {"id": 1, "name": "Good", "type": "LORA", "nsfw": False, "allowCommercialUse": "{Image}", "creator": {"username": "a"}, "stats": {"downloadCount": 9},
     "modelVersions": [{"id": 11, "name": "v1", "baseModel": "Flux.1 D", "files": [
         {"name": "good.safetensors", "sizeKB": 2048, "hashes": {"SHA256": "ab" * 32}, "downloadUrl": "https://civitai.com/api/download/models/11", "primary": True, "metadata": {"format": "SafeTensor"}},
         {"name": "bad.ckpt", "sizeKB": 1, "metadata": {"format": "PickleTensor"}, "downloadUrl": "x"},
         {"name": "scan.safetensors", "sizeKB": 1, "pickleScanResult": "Danger", "metadata": {"format": "SafeTensor"}, "downloadUrl": "y"}]}]},
    {"id": 2, "name": "Mature", "type": "LORA", "nsfw": True, "modelVersions": [{"id": 22, "files": [{"name": "m.safetensors", "metadata": {"format": "SafeTensor"}}]}]},
    {"id": 3, "name": "NoFiles", "type": "LORA", "nsfw": False, "modelVersions": [{"id": 33, "files": [{"name": "x.ckpt", "metadata": {"format": "PickleTensor"}}]}]}]}

def test_civitai_search_is_sfw_and_keeps_only_safe_safetensors():
    op = FakeOpener({"https://civitai.com/api/v1/models": json.dumps(MODEL).encode()})
    items = civitai.search("flux", types=["LORA"], opener=op)
    assert "nsfw=false" in op.calls[0][0] and "primaryFileOnly=true" in op.calls[0][0]
    assert [i["id"] for i in items] == [1]
    assert [f["name"] for f in items[0]["versions"][0]["files"]] == ["good.safetensors"] and items[0]["versions"][0]["files"][0]["size_mb"] == 2.0

def test_fetch_needs_confirm_and_checks_hash_and_never_forwards_token(tmp_path, monkeypatch):
    body = b"weights" * 10; good = hashlib.sha256(body).hexdigest()
    file = {"name": "w.safetensors", "url": "https://civitai.com/api/download/models/11", "sha256": good}
    with pytest.raises(net.ConnectorError): civitai.fetch(file, str(tmp_path))
    op = FakeOpener({"https://civitai.com/api/download/models/11": redirect("https://store.example/blob"), "https://store.example/blob": body})
    p = civitai.fetch(file, str(tmp_path), confirm=True, token="SECRET", opener=op)
    assert open(p, "rb").read() == body and not (tmp_path / "w.safetensors.part").exists()
    assert op.calls[0][1].get("Authorization") == "Bearer SECRET" and "Authorization" not in op.calls[1][1]
    bad = dict(file, sha256="00" * 32); op2 = FakeOpener({"https://civitai.com/api/download/models/11": body})
    with pytest.raises(net.ConnectorError, match="SHA-256"): civitai.fetch(bad, str(tmp_path / "x"), confirm=True, opener=op2)
    assert not list((tmp_path / "x").glob("*"))

def test_login_required_and_rate_limit_messages(tmp_path):
    op = FakeOpener({"https://civitai.com/api/download/models/11": urllib.error.HTTPError("u", 401, "no", {}, None)})
    with pytest.raises(net.ConnectorError, match="login token"): net.download("https://civitai.com/api/download/models/11", str(tmp_path / "a"), opener=op)
    op = FakeOpener({"https://civitai.com/api/v1/models": urllib.error.HTTPError("u", 429, "slow", {}, None)})
    with pytest.raises(net.ConnectorError, match="rate limited"): civitai.search("x", opener=op)

def test_hf_search_drops_gated_private_and_mature():
    data = [{"id": "o/ok", "downloads": 5, "likes": 1, "pipeline_tag": "text-to-image", "tags": ["license:apache-2.0"]}, {"id": "o/gated", "gated": "auto", "tags": []},
            {"id": "o/priv", "private": True, "tags": []}, {"id": "o/nsfw", "tags": ["not-for-all-audiences"]}]
    out = hf.search("flux", pipeline_tag="text-to-image", opener=FakeOpener({"https://huggingface.co/api/models": json.dumps(data).encode()}))
    assert [m["id"] for m in out] == ["o/ok"] and out[0]["license"] == "apache-2.0"

def test_hf_fetch_dry_run_default_and_confirm_gate():
    seen = []
    dl = lambda **kw: seen.append(kw) or "ok"
    assert hf.fetch("o/r", filename="a.safetensors", downloader=dl) == "ok" and seen[0]["dry_run"] is True
    with pytest.raises(net.ConnectorError): hf.fetch("o/r", filename="a", dry_run=False, downloader=dl)
    hf.fetch("o/r", allow_patterns=["*.json"], dry_run=False, confirm=True, downloader=dl); assert seen[1]["allow_patterns"] == ["*.json"] and "filename" not in seen[1]

def test_registry_keeps_remote_off_in_open_edition(monkeypatch):
    monkeypatch.delenv("PSN_ALLOW_FREE_REMOTE", raising=False)
    assert set(registry.available("open")) == {"civitai", "huggingface"}
    assert set(registry.CONNECTORS) >= {"ai_horde", "pollinations", "cloudflare_workers_ai"}
