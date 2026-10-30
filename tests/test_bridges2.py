import json, os, sys, threading, urllib.request, urllib.error
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn.bridges import policy as P, http_api as H, deliver as D, trigger as T
from tests.test_bridges import Fake

def test_http_api_restricted(tmp_path):
    f = Fake({("GET", "/v1/ping"): (200, {"pong": True}, {}), ("POST", "/v1/echo"): (200, {"got": 1}, {})}); P._limiters.clear()
    cfg = {"http_api": {"enabled": True, "base_url": f"http://{f.host}", "allow_http": True, "headers": {"X-Key": "supersecretkey1"}}}
    assert H.request_json(cfg, "GET", "/v1/ping")["data"] == {"pong": True} and f.log[0]["headers"]["X-Key"] == "supersecretkey1"
    assert H.request_json(cfg, "POST", "/v1/echo", {"a": 1})["ok"]
    for bad in ("v1/ping", "/../etc", "//evil.example/x", "/a@b"):
        with pytest.raises(P.BridgeError): H.request_json(cfg, "GET", bad)
    with pytest.raises(P.BridgeError): H.request_json(cfg, "PATCH", "/x")
    with pytest.raises(P.BridgeDisabled): H.request_json({}, "GET", "/x")
    f.close()

def test_deliver_sanitises_and_confines(tmp_path):
    cfg = {"deliver": {"enabled": True, "roots": [str(tmp_path)]}}
    p = D.deliver(cfg, [("my pic?.png", b"A"), ("my pic?.png", b"B")], "shots/../../evil", {"seed": 5}); assert len(p) == 2 and p[0] != p[1] and all(x.startswith(str(tmp_path)) for x in p) and json.load(open(p[0] + ".json"))["seed"] == 5
    assert D.deliver(cfg, [("x.exe;rm", b"1")])[0].endswith(".bin") and not os.path.exists(os.path.join(os.path.dirname(str(tmp_path)), "evil"))
    with pytest.raises(P.BridgeError): D.deliver({"deliver": {"enabled": True, "roots": []}}, [("a.png", b"1")])
    with pytest.raises(P.BridgeError): D.deliver({"deliver": {"enabled": True, "roots": [str(tmp_path)], "max_mb": 0}}, [("a.png", b"1")])

def test_param_validation_and_render():
    sch = {"prompt": {"type": "string", "max_len": 20}, "steps": {"type": "int", "min": 1, "max": 30, "default": 20}, "cfg": {"type": "float", "min": 0, "max": 10}, "mode": {"type": "choice", "choices": ["a", "b"]}, "hd": {"type": "bool", "default": False}}
    ok = T.validate_params(sch, {"prompt": "a fox", "cfg": 3, "mode": "a"}); assert ok["steps"] == 20 and ok["hd"] is False
    for bad in ({"prompt": "x" * 21, "cfg": 1, "mode": "a"}, {"prompt": "x", "cfg": 11, "mode": "a"}, {"prompt": "x", "cfg": 1, "mode": "z"}, {"prompt": "x", "cfg": 1, "mode": "a", "evil": 1}, {"prompt": "x", "cfg": True, "mode": "a"}, {"cfg": 1, "mode": "a"}, {"prompt": 5, "cfg": 1, "mode": "a"}, {"prompt": "x", "cfg": 1, "mode": "a", "steps": 99}):
        with pytest.raises(P.BridgeError): T.validate_params(sch, bad)
    g = T.render({"1": {"class_type": "KSampler", "inputs": {"steps": "{{steps}}", "text": "photo of {{prompt}}!"}}}, {"steps": 12, "prompt": '"}, "2": {"class_type": "Evil'})
    assert g["1"]["inputs"]["steps"] == 12 and set(g) == {"1"} and "Evil" in g["1"]["inputs"]["text"]          # injection stays inside the string value

def _post(url, token, body=None):
    req = urllib.request.Request(url, json.dumps(body or {}).encode(), {"Authorization": "Bearer " + token, "Content-Type": "application/json"} if token else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r: return r.status, json.load(r)
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")

def test_trigger_server(tmp_path):
    (tmp_path / "fox.json").write_text(json.dumps({"1": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{prompt}}"}}})); (tmp_path / "fox.params.json").write_text(json.dumps({"prompt": {"type": "string", "max_len": 30}}))
    queued = []; cfg = {"trigger": {"enabled": True, "token": "t" * 24, "listen": "127.0.0.1:0", "workflows_dir": str(tmp_path), "rate_per_min": 6}}; P._limiters.clear()
    srv = T.make_server(cfg, queue_fn=lambda g: (queued.append(g), {"prompt_id": "p1"})[1]); threading.Thread(target=srv.serve_forever, daemon=True).start(); base = f"http://127.0.0.1:{srv.server_address[1]}"
    assert _post(base + "/run/fox", None, {"params": {"prompt": "red fox"}})[0] == 401 and _post(base + "/run/fox", "wrong" * 5, {})[0] == 401
    st, r = _post(base + "/run/fox", "t" * 24, {"params": {"prompt": "red fox"}}); assert st == 200 and r["prompt_id"] == "p1" and queued[0]["1"]["inputs"]["text"] == "red fox"
    assert _post(base + "/run/nope", "t" * 24, {})[0] == 400 and _post(base + "/run/..%2fetc", "t" * 24, {})[0] == 404 and _post(base + "/other", "t" * 24, {})[0] == 404
    assert _post(base + "/run/fox", "t" * 24, {"params": {"prompt": "x" * 99}})[0] == 400
    assert _post(base + "/run/fox", "t" * 24, {"graph": {"1": {}}, "params": {"prompt": "ok"}})[0] == 200       # raw graphs are ignored, only params are used
    assert _post(base + "/run/fox", "t" * 24, {"params": {"prompt": "ok"}})[0] == 429
    srv.shutdown()

def test_trigger_requires_config():
    with pytest.raises(P.BridgeDisabled): T.make_server({})
    with pytest.raises(P.BridgeError): T.make_server({"trigger": {"enabled": True, "token": "short"}})
    with pytest.raises(P.BridgeError): T.load_workflow("/tmp", "../etc/passwd")

def test_new_nodes_are_off_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("PSN_BRIDGE_CONFIG", str(tmp_path / "none.json")); from psn_nodes import bridges as B
    assert B.PSN_HttpRequest().run("GET", "/x", "")[2] is False and "PSN_HttpRequest" in B.NODE_CLASS_MAPPINGS and "PSN_DeliverToFolder" in B.NODE_CLASS_MAPPINGS
