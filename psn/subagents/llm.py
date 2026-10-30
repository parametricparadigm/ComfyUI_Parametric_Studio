"""OpenAI-compatible chat client (standard library). Open edition: loopback endpoints only (a paid or remote host is refused here); set PSN_EDITION=extended to allow others.
Endpoints: {"name": {"url": ".../v1", "model": "id"}}; default is the local Qwen on :8002, override with a JSON file named by $PSN_SUBAGENT_ENDPOINTS."""
import json, os, base64, mimetypes, urllib.request, urllib.parse, urllib.error

DEFAULT_ENDPOINTS = {"qwen": {"url": "http://127.0.0.1:8002/v1", "model": "qwen38-27b-fp8"}}

def endpoints():
    p = os.environ.get("PSN_SUBAGENT_ENDPOINTS")
    return {**DEFAULT_ENDPOINTS, **(json.load(open(p)) if p and os.path.exists(p) else {})}

def check_local(url):
    host = urllib.parse.urlparse(url).hostname or ""
    if host in ("127.0.0.1", "localhost", "::1") or os.environ.get("PSN_EDITION") == "extended": return url
    raise PermissionError(f"endpoint host '{host}' is not loopback: the Open edition only uses local models (set PSN_EDITION=extended for others)")

def _post(url, body, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def image_part(path):
    mt = mimetypes.guess_type(path)[0] or "image/png"
    return {"type": "image_url", "image_url": {"url": f"data:{mt};base64," + base64.b64encode(open(path, "rb").read()).decode()}}

_NO_CONSTRAIN = set()     # endpoints that rejected a json_schema response_format: not asked again

def chat(endpoint, messages, temperature=0.2, max_tokens=2000, thinking=False, timeout=600, transport=None, response_format=None):
    """-> (text, completion_tokens). `endpoint` is a name from endpoints() or a dict; `transport(url, body)` replaces the HTTP call (tests)."""
    ep = endpoints()[endpoint] if isinstance(endpoint, str) else endpoint
    url = check_local(ep["url"]).rstrip("/") + "/chat/completions"
    body = {"model": ep["model"], "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "chat_template_kwargs": {"enable_thinking": bool(thinking)}}
    if response_format and os.environ.get("PSN_CONSTRAIN", "1") != "0" and url not in _NO_CONSTRAIN:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "schema": response_format, "strict": True}}
    try: r = (transport or _post)(url, body, timeout)
    except urllib.error.HTTPError as e:
        if e.code != 400 or "response_format" not in body: raise
        _NO_CONSTRAIN.add(url); body.pop("response_format"); r = (transport or _post)(url, body, timeout)      # the server cannot enforce this schema: carry on, the verifier still checks
    msg = r["choices"][0]["message"]; text = (msg.get("content") or "").strip()
    return text, int((r.get("usage") or {}).get("completion_tokens", len(text) // 4))
