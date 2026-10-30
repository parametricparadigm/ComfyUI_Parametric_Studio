"""The crew's voices: a stub speech server stands in for the real one; nothing here touches a live port or a real profile."""
import importlib, json, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import crew, crew_api, llm_tiers, voice as V

KOKORO = "speaches-ai/Kokoro-82M-v1.0-ONNX-fp16"; DISTIL = "Systran/faster-distil-whisper-large-v3"; TINY = "Systran/faster-whisper-tiny"
EN = [{"id": v, "language": "en-gb" if v[0] == "b" else "en-us"} for v in sorted({c[0] for c in crew.CHARACTERS.values()})]
MODELS = [{"id": TINY, "task": "automatic-speech-recognition"}, {"id": DISTIL, "task": "automatic-speech-recognition"}, {"id": KOKORO, "task": "text-to-speech", "voices": EN + [{"id": "ff_siwis", "language": "fr-fr"}]}]

class Stub:
    """A tiny OpenAI-style speech server on a free port, recording what it was sent."""
    def __init__(self, models=MODELS, audio=b"ID3-fake-mp3", text="hello from the stub", speech_status=200, sleeping=None):
        stub = self; self.calls = []
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def _send(self, code, body, ctype="application/json"):
                self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                stub.calls.append(("GET", self.path, b"", ""))
                if self.path == "/v1/models": self._send(200, json.dumps({"data": models}).encode())
                elif self.path == "/is_sleeping" and sleeping is not None: self._send(200, json.dumps({"is_sleeping": sleeping}).encode())
                else: self._send(404, b"{}")
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0)); stub.calls.append(("POST", self.path, body, self.headers.get("Content-Type", "")))
                if self.path == "/v1/audio/speech": self._send(speech_status, audio if speech_status == 200 else b'{"detail":"nope"}', "audio/mp3" if speech_status == 200 else "application/json")
                elif self.path == "/v1/audio/transcriptions": self._send(200, json.dumps({"text": text}).encode())
                else: self._send(404, b"{}")
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"
    def posts(self, path): return [c for c in self.calls if c[0] == "POST" and c[1] == path]
    def close(self): self.srv.shutdown(); self.srv.server_close()

@pytest.fixture
def client(monkeypatch):
    """No real speech server or LLM can be reached: the local list is empty and the LLM probe is off unless a test turns it on."""
    importlib.reload(crew)   # another test file replaces crew's functions at import time
    monkeypatch.setattr(V, "LOCAL", []); monkeypatch.delenv("STUDIO_TTS_URL", raising=False); monkeypatch.setattr(llm_tiers, "endpoint", lambda *a, **k: None)
    V._found.update(at=0.0, value=None); app = FastAPI(); app.include_router(V.router); app.include_router(crew_api.router)
    yield TestClient(app)
    V._found.update(at=0.0, value=None)

@pytest.fixture
def server(monkeypatch):
    made = []
    def start(**kw):
        s = Stub(**kw); made.append(s); monkeypatch.setenv("STUDIO_TTS_URL", s.base + "/v1"); V._found.update(at=0.0, value=None); return s
    yield start
    for s in made: s.close()

def test_503_when_nothing_is_there(client):
    r = client.get("/api/voice"); assert r.status_code == 200 and r.json()["tts"] is None and r.json()["stt"] is None
    assert client.post("/api/voice/tts", json={"text": "hi", "member": "master"}).status_code == 503
    assert client.post("/api/voice/stt", files={"file": ("a.webm", b"xx", "audio/webm")}).status_code == 503

def test_status_says_what_is_available_and_prefers_distil_large(client, server):
    server(); d = client.get("/api/voice").json()
    assert d["tts"]["model"] == KOKORO and d["stt"]["model"] == DISTIL and d["local"] is True
    assert d["tts"]["voices"] == len(EN), "non-English voices are not counted"

def test_only_loopback_is_probed_by_default():
    assert all(V._is_local(u) for u in V.LOCAL) and V._is_local("http://localhost:8000/v1") and not V._is_local("https://api.example.com/v1")

def test_a_remote_url_must_be_asked_for_and_is_reported(client, monkeypatch):
    monkeypatch.setenv("STUDIO_TTS_URL", "https://speech.example.com/v1/")
    seen = []
    def probe(base): seen.append(base); return [{"id": "tts-1", "task": "text-to-speech"}]
    s = V.speech(probe=probe); assert seen == ["https://speech.example.com/v1"] and s["tts"]["url"] == "https://speech.example.com/v1"
    V._found.update(at=0.0, value=None)

def test_tts_proxies_with_the_members_fixed_voice_and_strips_markdown(client, server):
    s = server(); r = client.post("/api/voice/tts", json={"text": "Hello **there** `you`", "member": "minimax-h3"})
    assert r.status_code == 200 and r.content == b"ID3-fake-mp3" and r.headers["content-type"] == "audio/mpeg" and r.headers["x-voice"] == "am_adam"
    sent = json.loads(s.posts("/v1/audio/speech")[0][2])
    assert sent == {"model": KOKORO, "voice": "am_adam", "input": "Hello there you", "response_format": "mp3", "speed": 0.86}

def test_tts_rejects_empty_and_caps_length(client, server):
    s = server(); assert client.post("/api/voice/tts", json={"text": " *** ", "member": "master"}).status_code == 400
    assert client.post("/api/voice/tts", json={"text": "x" * 9000, "member": "master"}).status_code == 200
    assert len(json.loads(s.posts("/v1/audio/speech")[0][2])["input"]) == V.MAX_TEXT

def test_tts_upstream_failure_and_empty_audio_are_503_so_the_ui_can_fall_back(client, server):
    server(speech_status=500); assert client.post("/api/voice/tts", json={"text": "hi", "member": "master"}).status_code == 503
    assert V._found["value"] is None, "a failed server is not remembered"
    server(audio=b""); assert client.post("/api/voice/tts", json={"text": "hi", "member": "master"}).status_code == 503

def test_stt_forwards_the_audio_to_distil_large(client, server):
    s = server(text=" Hello there. "); r = client.post("/api/voice/stt", files={"file": ("a b\r\nc.webm", b"\x1aE\xdf\xa3audio", "audio/webm;codecs=opus")})
    assert r.status_code == 200 and r.json() == {"text": "Hello there.", "model": DISTIL}
    body = s.posts("/v1/audio/transcriptions")[0][2]; ctype = s.posts("/v1/audio/transcriptions")[0][3]
    assert ctype.startswith("multipart/form-data") and b"\x1aE\xdf\xa3audio" in body and DISTIL.encode() in body and b'filename="ab' in body and b"\r\nc.webm" not in body and b"language" not in body

def test_stt_passes_a_clean_language_and_drops_a_bad_one(client, server):
    s = server(); client.post("/api/voice/stt", files={"file": ("a.webm", b"x", "audio/webm")}, data={"language": "en"}); assert b'name="language"\r\n\r\nen\r\n' in s.posts("/v1/audio/transcriptions")[0][2]
    client.post("/api/voice/stt", files={"file": ("a.webm", b"x", "audio/webm")}, data={"language": "en\r\nX: y"}); assert b"language" not in s.posts("/v1/audio/transcriptions")[1][2]

def test_stt_input_checks(client, server, monkeypatch):
    server(); assert client.post("/api/voice/stt", files={"file": ("a.webm", b"", "audio/webm")}).status_code == 400
    assert client.post("/api/voice/stt", files={"file": ("a.png", b"x", "image/png")}).status_code == 400
    monkeypatch.setattr(V, "MAX_AUDIO", 3); assert client.post("/api/voice/stt", files={"file": ("a.webm", b"xxxx", "audio/webm")}).status_code == 413

def test_a_server_without_task_fields_is_read_from_model_names():
    assert V._is({"id": "kokoro"}, "text-to-speech", V.TTS_NAME) and V._is({"id": "whisper-1"}, "automatic-speech-recognition", V.STT_NAME) and not V._is({"id": "gpt-4"}, "text-to-speech", V.TTS_NAME)

def test_llm_state_reads_the_real_sleep_flag(client):
    assert V.llm_state(lambda: None) == "none"
    s = Stub(sleeping=True); assert V.llm_state(lambda: {"url": s.base + "/v1", "model": "x"}) == "asleep"; assert client.get("/api/voice").json()["llm"] == "none"; s.close()
    s = Stub(sleeping=False); assert V.llm_state(lambda: {"url": s.base + "/v1", "model": "x"}) == "awake"; s.close()
    s = Stub(); assert V.llm_state(lambda: {"url": s.base + "/v1", "model": "x"}) == "awake", "a server without the route does not sleep"; s.close()

def test_default_chat_fails_fast_while_the_llm_sleeps(client, monkeypatch):
    s = Stub(sleeping=True); monkeypatch.setattr(llm_tiers, "endpoint", lambda *a, **k: {"url": s.base + "/v1", "model": "x"})
    with pytest.raises(RuntimeError, match="asleep"): crew.default_chat([{"role": "user", "content": "hi"}])
    assert not s.posts("/v1/chat/completions"), "a sleeping server is never sent a chat: it would hang"; s.close()

def test_ask_answers_from_the_notes_word_for_word_while_the_llm_sleeps(client, tmp_path, monkeypatch):
    monkeypatch.setattr(crew_api, "KB_ROOT", _kb(tmp_path)); s = Stub(sleeping=True); monkeypatch.setattr(llm_tiers, "endpoint", lambda *a, **k: {"url": s.base + "/v1", "model": "x"})
    r = client.post("/api/crew/ask", json={"who": "flux-2-klein", "question": "How many steps for Klein?"}).json()["result"]; s.close()
    assert r["from_notes_only"] is True and r["supported"] is True and "20 steps" in r["quotes"][0]["quote"]

# ---------- the characters
ROSTER_IDS = ["3d-trellis-hunyuan3d-sam3d-mesh", "anima", "audio-fx-separation-foley-models", "chroma", "cogvideox-mochi-cosmos-svd-animatediff-older-video", "depth-normals-pose", "dreamx-creator", "faces-identity-portrait-animation", "flux-1-dev-schnell-kontext-fill", "flux-2-klein", "hidream", "hunyuanvideo-framepack", "kandinsky-omnigen-ovis-hunyuanimage", "krea-2", "ltx-video-ltx-2", "minimax-h3", "music-song-models", "pony-illustrious-noobai", "prism-longcat-void-joyai-video", "qwen-image-qwen-image-edit", "sam-segmentation-matting", "sd-1-5", "sd3-sd3-5", "sdxl", "tts-voice-models", "upscale-restore-models", "vlm-captioning-tagging", "wan-version-not-stated", "wan-2-1", "wan-2-2", "z-image-lumina2", "text-encoders", "vae", "vision", "lora", "controlnet", "upscaler", "master"]

def test_every_member_has_a_distinct_voice_and_a_first_line():
    assert sorted(crew.CHARACTERS) == sorted(ROSTER_IDS) and len(ROSTER_IDS) == 38
    pairs = [c[:2] for c in crew.CHARACTERS.values()]; assert len(set(pairs)) == 38, "no two members sound the same"
    assert all(c[0][:3] in ("af_", "am_", "bf_", "bm_") and 0.8 <= c[1] <= 1.2 and c[2].strip() for c in crew.CHARACTERS.values())
    by_voice = {}
    for v, s in pairs: by_voice.setdefault(v, []).append(s)
    assert all(max(s) - min(s) >= 0.14 for s in by_voice.values() if len(s) > 1), "a shared voice must differ clearly in pace"

def test_hash_fallback_is_stable_and_respects_what_the_server_has():
    a = ["voice_a", "voice_b", "voice_c"]
    assert crew.voice("master", a)[0] in a and crew.voice("master", a) == crew.voice("master", list(reversed(a))), "stable whatever the order"
    assert crew.voice("master") == ("af_heart", 1.0) and crew.voice("master", ["af_heart", "x"]) == ("af_heart", 1.0)
    new = crew.voice("brand-new-member"); assert new[0] in {c[0] for c in crew.CHARACTERS.values()} and new == crew.voice("brand-new-member")
    assert crew.hello("brand-new-member") and crew.hello("master").startswith("Hi, I'm Comfy Prime")

def test_a_member_the_server_has_no_voice_for_still_speaks(client, server):
    s = server(models=[{"id": KOKORO, "task": "text-to-speech", "voices": [{"id": "only_one", "language": "en-us"}]}])
    assert client.post("/api/voice/tts", json={"text": "hi", "member": "master"}).headers["x-voice"] == "only_one"

def test_lookups_cannot_be_walked_out_of_the_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(crew, "_CREW_WEB", str(tmp_path)); (tmp_path / "abc.webp").write_bytes(b"x"); (tmp_path / "abc.idle.mp4").write_bytes(b"x")
    assert crew.portrait("abc") == "crew/abc.webp" and crew.portrait("nope") is None and crew.portrait("../abc") is None and crew.motion("../abc") is None
    assert crew.motion("abc") is None, "the talking loop is what makes a member animated"; (tmp_path / "abc.talk.mp4").write_bytes(b"x"); assert crew.motion("abc") == {"idle": "crew/abc.idle.mp4", "talk": "crew/abc.talk.mp4"}
    (tmp_path / "abc.idle.mp4").unlink(); assert crew.motion("abc") == {"idle": None, "talk": "crew/abc.talk.mp4"}

# ---------- /api/crew and /api/crew/ask as the dock uses them
def _kb(tmp_path):
    d = tmp_path / "model_families" / "10-Flux.2-Klein" / "dossier"; d.mkdir(parents=True); (d / "notes.md").write_text("Klein uses 4 steps in fast mode and 20 steps in quality mode.\n")
    return str(tmp_path)

def test_crew_lists_faces_and_voices(client, tmp_path, monkeypatch):
    monkeypatch.setattr(crew_api, "KB_ROOT", _kb(tmp_path)); m = {x["id"]: x for x in client.get("/api/crew").json()["members"]}
    assert m["master"]["name"] == "Comfy Prime" and m["master"]["voice"] == "af_heart" and m["flux-2-klein"]["voice"] == "am_fenrir" and m["flux-2-klein"]["hello"].startswith("Hey!")
    assert all(set(x) >= {"id", "name", "tier", "family", "portrait", "motion", "voice", "hello"} for x in m.values())

def test_ask_routes_auto_to_a_real_member_and_keeps_verified_quotes(client, tmp_path, monkeypatch):
    monkeypatch.setattr(crew_api, "KB_ROOT", _kb(tmp_path)); seen = []
    def chat(msgs): seen.append(msgs); return json.dumps({"answer": "Four in fast mode.", "quotes": [{"file": str(tmp_path / "model_families" / "10-Flux.2-Klein" / "dossier" / "notes.md"), "quote": "Klein uses 4 steps in fast mode"}]})
    monkeypatch.setattr(crew, "default_chat", chat)
    r = client.post("/api/crew/ask", json={"who": "auto", "question": "How many steps for Flux.2-Klein?"}); assert r.status_code == 200, r.text
    d = r.json(); assert d["member"]["id"] == "flux-2-klein" and d["result"]["supported"] is True and d["result"]["quotes"][0]["quote"].startswith("Klein uses 4") and seen
    r = client.post("/api/crew/ask", json={"who": "auto", "question": "How do steps work here?"}).json(); assert r["member"]["id"] == "master" and r["result"]["answer"] == "Four in fast mode."
    r = client.post("/api/crew/ask", json={"who": "flux-2-klein", "question": "Zebra quantum?"}).json(); assert r["result"]["supported"] is False and r["result"]["problems"] == ["No relevant chunks found"]

def test_art_manifest_covers_the_roster_when_built():
    """Once scripts/build_crew_art.py has run, every member has a 512 px face and its prompt and seed are on record."""
    man = os.path.join(crew._CREW_WEB, "portraits.json")
    if not os.path.exists(man): pytest.skip("portraits not built yet")
    d = json.load(open(man)); assert d["goal"] == "image"
    from PIL import Image
    missing = [i for i in ROSTER_IDS if i not in d["members"]]
    for i in d["members"]:
        assert d["members"][i]["prompt"] and isinstance(d["members"][i]["seed"], int), i
        with Image.open(os.path.join(crew._CREW_WEB, f"{i}.webp")) as im: assert im.size == (512, 512), i
    if missing: pytest.skip(f"{len(missing)} of 38 portraits still rendering")
