"""studio/live_api.py: per-node state from ComfyUI's websocket messages, with stubbed sockets and a stubbed /queue. Nothing here touches a live port."""
import json, socket, struct
import pytest
from studio import live_api as L
from studio.live_api import apply_event, apply_binary, read_frame

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    L.JOBS.clear(); L.S.update({"want": None, "client": None, "up": False, "thread": None, "seq": 0, "preview": None, "current": None, "last": None})
    monkeypatch.setattr(L, "follow", lambda c: L.S.update(want=c, client=c, up=True))     # no reader thread, no socket
    yield

def run(*msgs, now=100.0):
    for i, m in enumerate(msgs): apply_event(m, now=now + i, vram=lambda: 23.4)

def test_a_run_from_start_to_finish():
    p = "job1"
    run({"type": "execution_start", "data": {"prompt_id": p}}, {"type": "execution_cached", "data": {"nodes": ["1", "2"], "prompt_id": p}}, {"type": "executing", "data": {"node": "3", "display_node": "3", "prompt_id": p}}, {"type": "executing", "data": {"node": "11", "display_node": "11", "prompt_id": p}}, {"type": "progress", "data": {"value": 3, "max": 20, "node": "11", "prompt_id": p}})
    j = L.JOBS[p]; assert j["cached"] == ["1", "2"]; assert j["running"] == {"11": [3, 20]}; assert j["done"] == ["3"]; assert j["times"]["3"] == 1.0; assert j["vram"]["3"] == 23.4
    run({"type": "progress_state", "data": {"prompt_id": p, "nodes": {"11": {"state": "finished", "value": 20, "max": 20, "node_id": "11", "display_node_id": "11"}, "12": {"state": "running", "value": 0, "max": 1, "node_id": "12", "display_node_id": "12"}}}}, now=200.0)
    assert "11" in j["done"] and "12" in j["running"]; assert j["times"]["11"] > 90
    run({"type": "executed", "data": {"node": "12", "output": {}, "prompt_id": p}}, {"type": "execution_success", "data": {"prompt_id": p}}, now=210.0)
    assert j["status"] == "success" and j["running"] == {} and L.S["last"] == p

def test_expanded_nodes_report_under_their_display_id():
    run({"type": "progress_state", "data": {"prompt_id": "j", "nodes": {"5.0.1": {"state": "running", "value": 1, "max": 2, "node_id": "5.0.1", "display_node_id": "5"}}}})
    assert L.JOBS["j"]["running"] == {"5": [1, 2]}

def test_errors_and_interrupts():
    run({"type": "executing", "data": {"node": "7", "prompt_id": "e"}}, {"type": "execution_error", "data": {"prompt_id": "e", "node_id": "7"}})
    assert L.JOBS["e"]["error"] == "7" and L.JOBS["e"]["status"] == "error" and L.JOBS["e"]["running"] == {}
    run({"type": "executing", "data": {"node": "1", "prompt_id": "i"}}, {"type": "execution_interrupted", "data": {"prompt_id": "i"}})
    assert L.JOBS["i"]["status"] == "interrupted"

def test_status_messages_are_ignored_and_reconnect_message_has_no_prompt_id():
    run({"type": "status", "data": {"status": {}}}); assert L.JOBS == {}
    L.S["current"] = "cur"; run({"type": "executing", "data": {"node": "9"}}); assert L.JOBS["cur"]["running"] == {"9": [0, 0]}

def test_preview_frames():
    apply_binary(struct.pack(">II", 1, 1) + b"JPEGDATA"); assert L.S["preview"] == b"JPEGDATA" and L.S["mime"] == "image/jpeg" and L.S["seq"] == 1
    apply_binary(struct.pack(">II", 1, 2) + b"PNG"); assert L.S["mime"] == "image/png" and L.S["seq"] == 2
    apply_binary(struct.pack(">II", 3, 1) + b"other"); assert L.S["seq"] == 2, "other binary events are not previews"

def test_frame_parser_over_a_socketpair():
    a, b = socket.socketpair()
    try:
        a.sendall(bytes([0x81, 5]) + b"hello")                                                      # short text
        long = b"x" * 300; a.sendall(bytes([0x82, 126]) + struct.pack(">H", 300) + long)            # 16-bit length, binary
        mask = b"\x01\x02\x03\x04"; a.sendall(bytes([0x81, 0x83]) + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(b"abc")))   # masked
        assert read_frame(b) == (True, 1, b"hello"); assert read_frame(b) == (True, 2, long); assert read_frame(b) == (True, 1, b"abc")
    finally: a.close(); b.close()

def q(monkeypatch, running=None, pending=0):
    monkeypatch.setattr(L, "_get", lambda path, timeout=4: {"queue_running": [running] if running else [], "queue_pending": [0] * pending})

def test_live_idle_running_and_the_exact_queue_graph(monkeypatch):
    q(monkeypatch); assert L.live()["running"] is False
    g = {"1": {"class_type": "UNETLoader", "inputs": {}}}
    q(monkeypatch, [46, "J", g, {"client_id": "studio-abc"}, ["1"]], pending=2); out = L.live()
    assert out["running"] and out["job"] == "J" and out["graph"] == g and out["pending"] == 2 and out["mode"] == "nodes"
    assert "graph" not in L.live(have="J"), "a client that has the graph does not get it again"

def test_a_browser_tab_job_is_never_followed(monkeypatch):
    calls = []; monkeypatch.setattr(L, "follow", lambda c: calls.append(c))
    q(monkeypatch, [1, "K", {}, {"client_id": "0123abcd"}, []]); out = L.live(); assert out["mode"] == "pulse" and calls == []

def test_comfy_down(monkeypatch):
    def boom(*a, **k): raise OSError("down")
    monkeypatch.setattr(L, "_get", boom); assert L.live() == {"running": False, "comfy": False}

def test_preview_route_404_when_empty():
    from fastapi import HTTPException
    with pytest.raises(HTTPException): L.live_preview()
    L.S["preview"] = b"abc"; r = L.live_preview(); assert r.body == b"abc"

def test_every_workflow_class_has_an_explanation():
    import glob, os, re
    root = os.path.join(os.path.dirname(__file__), ".."); src = open(os.path.join(root, "studio", "web", "graph3d_math.js"), encoding="utf-8").read(); missing = set()
    for f in glob.glob(os.path.join(root, "workflows", "*.json")):
        try: d = json.load(open(f))
        except Exception: continue
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, dict) and v.get("class_type"):
                    c = v["class_type"]
                    if not re.search(r'(^|[\s{,"])' + re.escape(c) + r'"?: I\(', src): missing.add(c)
    assert not missing, sorted(missing)
