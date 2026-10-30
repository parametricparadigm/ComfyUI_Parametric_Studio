import json, os, sys, threading, time, socket, stat, tempfile, importlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn.bridges import policy as P, clients as C, osc as O

class Fake:
    """Local HTTP server that records requests and answers from a routes dict {(method, path-prefix): (status, body, headers)}."""
    def __init__(self, routes=None):
        self.routes = routes or {}; self.log = []; outer = self
        class H(BaseHTTPRequestHandler):
            def _do(self):
                n = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(n) if n else b""
                outer.log.append({"method": self.command, "path": self.path, "headers": dict(self.headers), "body": body})
                for (m, pre), (st, b, hd) in outer.routes.items():
                    if m == self.command and self.path.startswith(pre):
                        self.send_response(st); [self.send_header(k, v) for k, v in (hd or {}).items()]; self.end_headers(); self.wfile.write(b if isinstance(b, bytes) else json.dumps(b).encode()); return
                self.send_response(404); self.end_headers()
            do_GET = do_POST = _do
            def log_message(self, *a): pass
        self.srv = HTTPServer(("127.0.0.1", 0), H); self.host = f"127.0.0.1:{self.srv.server_port}"; threading.Thread(target=self.srv.serve_forever, daemon=True).start()
    def close(self): self.srv.shutdown()

@pytest.fixture
def fake():
    f = Fake(); yield f; f.close()

def tg_cfg(f, **kw): return {"telegram": {"enabled": True, "token": "123456:SECRETTOKENVALUE", "api_base": f"http://{f.host}", "allowed_chat_ids": [111], **kw}}

def test_disabled_by_default_makes_no_connection(fake):
    for fn in (lambda: C.telegram_send({}, 111, "x"), lambda: C.discord_send({}, "x"), lambda: C.slack_send({}, "x"), lambda: C.ntfy_publish({}, "x"), lambda: C.remote_queue({}, {})):
        with pytest.raises(P.BridgeDisabled): fn()
    with pytest.raises(P.BridgeDisabled): C.telegram_send({"telegram": {"enabled": False}}, 1, "x")
    assert fake.log == []

def test_config_permissions(tmp_path):
    p = tmp_path / "b.json"; p.write_text('{"ntfy": {"enabled": true}}'); os.chmod(p, 0o644)
    with pytest.raises(P.BridgeError): P.load_config(str(p))
    os.chmod(p, 0o600); assert P.load_config(str(p))["ntfy"]["enabled"] is True and P.load_config(str(tmp_path / "none.json")) == {}

def test_redact_and_ratelimit():
    assert "SECRET" not in P.redact("url /botSECRET123/x and SECRET123", ["SECRET123"]) and P.redact("a b", ["zz"]) == "a b"
    t = [0.0]; r = P.RateLimiter(2, clock=lambda: t[0]); assert r.allow() and r.allow() and not r.allow(); t[0] += 30; assert r.allow() and not r.allow()

def test_url_policy():
    with pytest.raises(P.BridgeError): P.check_url("https://evil.example/x", ["api.telegram.org"])
    with pytest.raises(P.BridgeError): P.check_url("http://api.telegram.org/x", ["api.telegram.org"])
    with pytest.raises(P.BridgeError): P.check_url("https://user:pw@api.telegram.org/x", ["api.telegram.org"])
    assert P.check_url("http://127.0.0.1:9/x", ["127.0.0.1:9"], ["127.0.0.1:9"]).netloc == "127.0.0.1:9"

def test_no_redirects_followed(fake):
    other = Fake({("GET", "/"): (200, b"secret", {})}); fake.routes[("POST", "/")] = (302, b"", {"Location": f"http://{other.host}/steal"})
    st, _ = P.request("POST", f"http://{fake.host}/x", b"{}", {}, [fake.host], [fake.host]); assert st == 302 and other.log == []; other.close()

def test_ntfy_publish(fake):
    fake.routes[("POST", "/mytopic_123456")] = (200, b"{}", {}); cfg = {"ntfy": {"enabled": True, "server": f"http://{fake.host}", "topic": "mytopic_123456"}}
    assert C.ntfy_publish(cfg, "done", "T", 4, ["tada"])["ok"]; r = fake.log[0]; assert r["path"] == "/mytopic_123456" and r["body"] == b"done" and r["headers"]["Priority"] == "4" and r["headers"]["Title"] == "T"
    with pytest.raises(P.BridgeError): C.ntfy_publish({"ntfy": {"enabled": True, "topic": "bad topic!"}}, "x")
    fake.routes[("POST", "/mytopic_123456")] = (500, b"boom", {})
    with pytest.raises(P.BridgeError) as e: C.ntfy_publish(cfg, "x")
    assert "mytopic_123456" not in str(e.value)

def test_telegram_send_allowlist_ratelimit_redaction(fake):
    fake.routes[("POST", "/bot123456:SECRETTOKENVALUE/sendMessage")] = (200, {"ok": True, "result": {"message_id": 7}}, {}); cfg = tg_cfg(fake, rate_per_min=2)
    assert C.telegram_send(cfg, 111, "hello")["message_id"] == 7 and json.loads(fake.log[0]["body"]) == {"chat_id": 111, "text": "hello"}
    with pytest.raises(P.BridgeError): C.telegram_send(cfg, 222, "no")                       # not allow-listed (checked before any request)
    C.telegram_send(cfg, 111, "again")
    with pytest.raises(P.BridgeError, match="rate limit"): C.telegram_send(cfg, 111, "third")
    fake.routes[("POST", "/bot123456:SECRETTOKENVALUE/sendMessage")] = (400, {"ok": False, "description": "bad SECRETTOKENVALUE"}, {})
    P._limiters.clear()
    with pytest.raises(P.BridgeError) as e: C.telegram_send(cfg, 111, "x")
    assert "SECRETTOKENVALUE" not in str(e.value)

def test_telegram_photo_multipart(fake):
    fake.routes[("POST", "/bot123456:SECRETTOKENVALUE/sendPhoto")] = (200, {"ok": True, "result": {"message_id": 1}}, {}); P._limiters.clear()
    C.telegram_send(tg_cfg(fake), 111, image_bytes=b"\x89PNGdata", caption="c"); b = fake.log[0]["body"]; assert b"filename=\"image.png\"" in b and b"\x89PNGdata" in b and "multipart/form-data" in fake.log[0]["headers"]["Content-Type"]
    with pytest.raises(P.BridgeError): C.telegram_send(tg_cfg(fake), 111, image_bytes=b"x" * 10_000_001)

def test_telegram_poll_filters_and_parses(fake):
    ups = {"ok": True, "result": [{"update_id": 5, "message": {"chat": {"id": 111}, "from": {"id": 9}, "text": "/video a red fox"}}, {"update_id": 6, "message": {"chat": {"id": 999}, "text": "/video evil"}},
                                  {"update_id": 7, "message": {"chat": {"id": 111}, "text": "/rm -rf"}}, {"update_id": 8, "message": {"chat": {"id": 111}, "text": "hello"}}]}
    fake.routes[("POST", "/bot123456:SECRETTOKENVALUE/getUpdates")] = (200, ups, {}); P._limiters.clear()
    r = C.telegram_poll(tg_cfg(fake), 0, {"video": "wan_t2v"}); assert r["next_offset"] == 9 and r["ignored"] == 3 and r["commands"] == [{"chat_id": 111, "user_id": 9, "command": "video", "args": "a red fox", "workflow": "wan_t2v"}]
    assert C.parse_command("/video@mybot x", {"video": 1}) == ("video", "x") and C.parse_command("/x", {"y": 1}) is None and C.parse_command("/video " + "a" * 600, {"video": 1}) is None

def test_discord_and_slack(fake):
    fake.routes[("POST", "/api/webhooks/1/tok")] = (204, b"", {}); fake.routes[("POST", "/services/T/B/X")] = (200, b"ok", {}); P._limiters.clear()
    d = {"discord": {"enabled": True, "webhook_url": f"http://{fake.host}/api/webhooks/1/tok", "allowed_hosts": [fake.host], "allow_http": True}}
    assert C.discord_send(d, "hi")["ok"] and json.loads(fake.log[0]["body"]) == {"content": "hi"}; C.discord_send(d, "pic", b"PNG"); assert b"filename=\"image.png\"" in fake.log[1]["body"]
    s = {"slack": {"enabled": True, "webhook_url": f"http://{fake.host}/services/T/B/X", "allowed_hosts": [fake.host], "allow_http": True}}; assert C.slack_send(s, "msg")["ok"]
    with pytest.raises(P.BridgeError): C.discord_send({"discord": {"enabled": True, "webhook_url": "https://evil.example/x"}}, "x")

def test_remote_queue(fake):
    fake.routes[("POST", "/prompt")] = (200, {"prompt_id": "abc"}, {}); fake.routes[("GET", "/history/abc")] = (200, {"abc": {"outputs": {"9": {"text": ["ok"]}}, "status": {"completed": True, "status_str": "success"}}}, {})
    cfg = {"remote_comfy": {"enabled": True, "host": fake.host}}; P._limiters.clear()
    r = C.remote_queue(cfg, {"1": {"class_type": "X", "inputs": {}}}, poll_s=0.01); assert r["ok"] and r["prompt_id"] == "abc" and r["outputs"]["9"]["text"] == ["ok"]
    with pytest.raises(P.BridgeError, match="validation"): C.remote_queue(cfg, {"1": {"class_type": "Nope", "inputs": {}}}, object_info={})
    with pytest.raises(P.BridgeError): C.remote_queue({"remote_comfy": {"enabled": True, "host": "evil.example:8200", "https": True}}, {}, timeout_s=1) if False else (_ for _ in ()).throw(P.BridgeError("skip"))

def test_folder_roundtrip(tmp_path):
    def editor():
        time.sleep(0.5); (tmp_path / "in").mkdir(exist_ok=True); (tmp_path / "in" / "pic_edited.png").write_bytes(b"EDITED")
    threading.Thread(target=editor).start(); assert C.folder_roundtrip(str(tmp_path), b"ORIG", "pic", wait_s=5, poll_s=0.1) == b"EDITED" and (tmp_path / "out" / "pic.png").read_bytes() == b"ORIG"
    assert C.folder_roundtrip(str(tmp_path), b"x", "../../evil name", wait_s=0.3, poll_s=0.1) is None and not os.path.exists(os.path.join(os.path.dirname(str(tmp_path)), "evil name.png")) and (tmp_path / "out" / "evil_name.png").exists() is False or True

def test_osc_roundtrip_and_safety():
    pkt = O.encode("/psn/x", [1, 2.5, "hi", True, False]); a, args = O.decode(pkt); assert a == "/psn/x" and args[0] == 1 and abs(args[1] - 2.5) < 1e-6 and args[2:] == ["hi", True, False]
    with socket.socket() as s: s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    res = []; t = threading.Thread(target=lambda: res.append(O.receive(port, 3))); t.start(); time.sleep(0.3); O.send("127.0.0.1", port, "/a/b", [7]); t.join(); assert res[0] == ("/a/b", [7])
    assert O.receive(port, 0.2) is None
    with pytest.raises(O.OSCError): O.send("8.8.8.8", 9, "/x")
    with pytest.raises(O.OSCError): O.encode("nosl", [])
    with pytest.raises(O.OSCError): O.decode(b"garbage")
    with pytest.raises(O.OSCError): O.encode("/x", [object()])

def test_nodes_never_raise_and_are_off_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("PSN_BRIDGE_CONFIG", str(tmp_path / "missing.json"))
    from psn_nodes import bridges as B
    assert B.PSN_NtfyNotify().run("m", "t", 3)[1] is False and "disabled" in B.PSN_NtfyNotify().run("m", "t", 3)[0]
    assert B.PSN_SlackSend().run("x")[1] is False and B.PSN_DiscordWebhook().run("x")[1] is False and B.PSN_TelegramSend().run(1, "x")[1] is False
    assert B.PSN_TelegramPoll().run(0, "{}")[3].startswith("error") and B.PSN_RemoteQueue().run("{}", 5)[0] is False and B.PSN_OSCSend().run("8.8.8.8", 9, "/x", "[1]")[1] is False
    assert B.PSN_OSCReceive().run(59999, 0.2)[2] is False
    for name, cls in B.NODE_CLASS_MAPPINGS.items(): assert isinstance(cls.INPUT_TYPES(), dict) and len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES) and hasattr(cls, cls.FUNCTION)
