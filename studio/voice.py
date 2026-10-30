"""The crew's voices: text to speech and speech to text, proxied to an OpenAI-compatible speech server on this machine (speaches with Kokoro and Whisper on the author's box).
Nothing leaves localhost by default: only the local address below is probed, and only STUDIO_TTS_URL, which you set yourself, can point anywhere else. 503 when no server is there; the web UI then falls back to the browser's own speech (see prime_ui.js)."""
import json, os, re, time, urllib.error, urllib.parse, urllib.request, uuid
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from studio import crew

LOCAL = ["http://127.0.0.1:8000/v1"]
MAX_TEXT, MAX_AUDIO = 1500, 25 * 2**20
NONE = "no speech server is running on this machine"
TTS_NAME = re.compile(r"kokoro|piper|xtts|orpheus|tts|speech", re.I); STT_NAME = re.compile(r"whisper|parakeet|canary|stt|asr", re.I)   # for servers whose /models has no task field

def _models_at(base, timeout=1.5):
    with urllib.request.urlopen(base + "/models", timeout=timeout) as r: return json.load(r).get("data", [])

def _is(m, task, name): return m.get("task") == task or (not m.get("task") and bool(name.search(str(m.get("id", "")))))

def _voices(m):
    """English voice names a TTS model offers: Kokoro's other voices garble English, so they are never picked. [] = the server does not list any."""
    out = []
    for v in m.get("voices") or []:
        if isinstance(v, str): out.append(v)
        elif isinstance(v, dict) and str(v.get("language", "en")).lower().startswith("en"): out.append(v.get("id") or v.get("name"))
    return [v for v in out if v]

_found = {"at": 0.0, "value": None}
def speech(probe=_models_at, now=time.time):
    """Find what can speak and listen: {"tts": {url, model, voices} or None, "stt": {url, model} or None}. Order: STUDIO_TTS_URL, then the local address. A hit is remembered for 30 s."""
    if _found["value"] and now() - _found["at"] < 30: return _found["value"]
    env = os.environ.get("STUDIO_TTS_URL", "").rstrip("/"); out = {"tts": None, "stt": None}
    for base in ([env] if env else []) + LOCAL:
        try: models = probe(base)
        except Exception: continue
        tts = [m for m in models if _is(m, "text-to-speech", TTS_NAME)]; stt = [m for m in models if _is(m, "automatic-speech-recognition", STT_NAME)]
        if tts and not out["tts"]: out["tts"] = {"url": base, "model": tts[0]["id"], "voices": _voices(tts[0])}
        if stt and not out["stt"]: out["stt"] = {"url": base, "model": os.environ.get("STUDIO_STT_MODEL") or sorted(stt, key=lambda m: ("distil" not in m["id"] or "large" not in m["id"], "large" not in m["id"]))[0]["id"]}   # prefer distil-large, then any large; STUDIO_STT_MODEL overrides
    if out["tts"] or out["stt"]: _found.update(at=now(), value=out)
    return out

def _is_local(url): return (urllib.parse.urlparse(url).hostname or "") in ("127.0.0.1", "localhost", "::1")

def llm_state(endpoint=None):
    """Can the crew think right now? "awake", "asleep" (vLLM put to sleep so a render can use its VRAM: its chat route hangs until it wakes, while /v1/models keeps answering) or "none" (nothing is running). Only read: this never sleeps or wakes anything."""
    from studio import llm_tiers
    ep = (endpoint or llm_tiers.endpoint)()
    if not ep: return "none"
    root = re.sub(r"/v1/?$", "", ep["url"])
    try:
        with urllib.request.urlopen(root + "/is_sleeping", timeout=1.5) as r: return "asleep" if json.load(r).get("is_sleeping") else "awake"
    except Exception: return "awake"   # only vLLM has this route; other servers do not sleep

router = APIRouter()
class Speak(BaseModel): text: str; member: str = "master"

def _clean(text): return re.sub(r"\s+", " ", re.sub(r"[`*_#>~]+", "", text)).strip()[:MAX_TEXT]

def _lost(what):
    _found.update(at=0.0, value=None); raise HTTPException(503, f"the speech server could not {what}") from None

@router.get("/api/voice")
def status():
    s = speech(); urls = [x["url"] for x in s.values() if x]
    return {"tts": s["tts"] and {"model": s["tts"]["model"], "voices": len(s["tts"]["voices"])}, "stt": s["stt"] and {"model": s["stt"]["model"]}, "local": all(_is_local(u) for u in urls), "llm": llm_state()}

@router.post("/api/voice/tts")
def tts(b: Speak):
    text = _clean(b.text)
    if not text: raise HTTPException(400, "nothing to say")
    s = speech()["tts"]
    if not s: raise HTTPException(503, NONE)
    name, pace = crew.voice(b.member, s["voices"])
    req = urllib.request.Request(s["url"] + "/audio/speech", json.dumps({"model": s["model"], "voice": name, "input": text, "response_format": "mp3", "speed": pace}).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: audio = r.read()
    except (urllib.error.URLError, OSError): _lost("speak")
    if not audio: _lost("speak")
    return Response(audio, media_type="audio/mpeg", headers={"X-Voice": name, "Cache-Control": "no-store"})

@router.post("/api/voice/stt")
def stt(file: UploadFile = File(...), language: str = Form("")):
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    if ctype and not re.fullmatch(r"(audio/[\w.+-]+|video/webm|application/octet-stream)", ctype): raise HTTPException(400, "send audio")
    data = file.file.read(MAX_AUDIO + 1)
    if not data: raise HTTPException(400, "no audio")
    if len(data) > MAX_AUDIO: raise HTTPException(413, "audio over 25 MB")
    s = speech()["stt"]
    if not s: raise HTTPException(503, NONE)
    fname = re.sub(r"[^\w.-]", "", file.filename or "") or "speech.webm"; b = uuid.uuid4().hex
    fields = {"model": s["model"], "response_format": "json", **({"language": language} if re.fullmatch(r"[a-z]{2,3}", language or "") else {})}
    body = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()) + f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{fname}"\r\nContent-Type: {ctype or "application/octet-stream"}\r\n\r\n'.encode() + data + f"\r\n--{b}--\r\n".encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(s["url"] + "/audio/transcriptions", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=120) as r: out = json.load(r)
    except (urllib.error.URLError, OSError, ValueError): _lost("listen")
    return {"text": str(out.get("text", "")).strip(), "model": s["model"]}
