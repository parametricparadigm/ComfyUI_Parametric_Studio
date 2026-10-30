import json
from fastapi.testclient import TestClient

def client(host="1.2.3.4"):
    import studio.server as s
    return TestClient(s.app, client=(host, 5000), follow_redirects=False)

def test_no_token_means_no_guard(monkeypatch):
    monkeypatch.delenv("STUDIO_TOKEN", raising=False); assert client().get("/api/goals").status_code == 200

def test_remote_needs_token_and_cookie_sticks(monkeypatch):
    monkeypatch.setenv("STUDIO_TOKEN", "sekret")
    c = client(); r = c.get("/api/goals"); assert r.status_code == 401 and "pairing" in r.text.lower() and "sekret" not in r.text
    assert c.get("/api/goals?t=wrong").status_code == 401
    r = c.get("/api/goals?t=sekret"); assert r.status_code == 200 and "studio_token" in r.headers.get("set-cookie", "") and "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/api/goals").status_code == 200   # the cookie now carries it
    assert client().get("/", headers={"x-studio-token": "sekret"}).status_code in (200, 304)

def test_localhost_passes_and_token_only_shown_locally(monkeypatch):
    monkeypatch.setenv("STUDIO_TOKEN", "sekret"); monkeypatch.setenv("STUDIO_HOST", "0.0.0.0")
    r = client("127.0.0.1").get("/api/phone"); assert r.status_code == 200 and r.json()["lan_enabled"]
    if r.json().get("lan_url"): assert "sekret" in r.json()["lan_url"]
    r = client().get("/api/phone?t=sekret"); assert r.status_code == 200 and "lan_url" not in r.json()

def test_tailscale_state_variants():
    from studio.phone import tailscale_state as T
    assert T(which=lambda n: None)["installed"] is False
    st = json.dumps({"BackendState": "Running", "Self": {"DNSName": "box.tail1.ts.net."}})
    run = lambda c, timeout=4: st if "--json" in c else ""
    r = T(run=run, which=lambda n: "/usr/bin/tailscale"); assert r["https_url"] == "https://box.tail1.ts.net" and r["connected"] and not r["serving"]
    run2 = lambda c, timeout=4: st if "--json" in c else "https://box.tail1.ts.net (tailnet only)\n|-- / proxy http://127.0.0.1:8310"
    assert T(run=run2, which=lambda n: "x")["serving"]
    assert T(run=lambda c, timeout=4: "", which=lambda n: "x")["connected"] is False

def test_manifest_and_service_worker_are_served():
    c = client("127.0.0.1"); m = c.get("/manifest.json").json(); assert m["display"] == "standalone" and any(i.get("purpose") == "maskable" for i in m["icons"])
    assert c.get("/sw.js").status_code == 200 and c.get("/icons/icon-192.png").status_code == 200

def test_text_is_compressed_and_media_is_not():
    c = client("127.0.0.1")
    r = c.get("/style.css", headers={"accept-encoding": "br"}); assert r.status_code == 200 and r.headers.get("content-encoding") == "br" and r.headers["vary"] == "Accept-Encoding"
    r = c.get("/style.css", headers={"accept-encoding": "gzip"}); assert r.headers.get("content-encoding") == "gzip" and b"--a1" in r.content
    assert "content-encoding" not in c.get("/style.css", headers={"accept-encoding": "identity"}).headers
    assert "content-encoding" not in c.get("/icons/icon-192.png", headers={"accept-encoding": "br"}).headers
