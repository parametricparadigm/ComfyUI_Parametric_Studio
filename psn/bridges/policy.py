"""Security policy shared by every bridge (original design). Principles: OFF by default; secrets only in a chmod-600 config file (never in a workflow); exact host allow-lists; HTTPS unless a host is explicitly
allowed for plain HTTP (LAN/Tailscale); no redirects; bounded sizes and rates; secrets redacted from every error."""
import os, json, time, uuid, urllib.parse, urllib.request, urllib.error

DEFAULT_CONFIG = os.environ.get("PSN_BRIDGE_CONFIG") or os.path.expanduser("~/.config/parametric_studio/bridges.json")

class BridgeError(Exception): pass
class BridgeDisabled(BridgeError): pass

def load_config(path=None):
    """{} if the file does not exist. Refuses a config readable by group/others (it holds tokens)."""
    path = path or DEFAULT_CONFIG
    if not os.path.exists(path): return {}
    if os.stat(path).st_mode & 0o077: raise BridgeError(f"{path} must not be readable by others: run chmod 600 on it")
    try: return json.load(open(path))
    except json.JSONDecodeError as e: raise BridgeError(f"config is not valid JSON: {e}")

def section(cfg, name):
    s = (cfg or {}).get(name) or {}
    if not s.get("enabled"): raise BridgeDisabled(f"the {name} bridge is disabled (set \"enabled\": true for \"{name}\" in {DEFAULT_CONFIG})")
    return s

def secrets_of(s):
    """Secret values plus their meaningful fragments (a bot token 'id:secret' may be echoed in parts; a webhook URL's path alone identifies it)."""
    import re
    out = []
    for k, v in s.items():
        if v and k in ("token", "webhook_url", "api_key", "topic") and len(str(v)) >= 6:
            v = str(v); out.append(v); out += [x for x in re.split(r"[:/]", v) if len(x) >= 8]
    return out

def redact(text, secrets):
    text = str(text)
    for sec in sorted(set(secrets), key=len, reverse=True):
        text = text.replace(sec, "***")
        text = text.replace(urllib.parse.quote(sec, safe=""), "***")
    return text

class RateLimiter:
    """Token bucket: `per_minute` actions per minute (burst = per_minute)."""
    def __init__(self, per_minute, clock=time.monotonic):
        self.rate = max(1, int(per_minute)) / 60.0; self.cap = max(1, int(per_minute)); self.tokens = float(self.cap); self.clock = clock; self.t = clock()
    def allow(self):
        now = self.clock(); self.tokens = min(self.cap, self.tokens + (now - self.t) * self.rate); self.t = now
        if self.tokens >= 1: self.tokens -= 1; return True
        return False

_limiters = {}
def limiter(name, per_minute):
    key = (name, int(per_minute))
    if key not in _limiters: _limiters[key] = RateLimiter(per_minute)
    return _limiters[key]

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
_opener = urllib.request.build_opener(_NoRedirect)

def check_url(url, allowed_hosts, allow_http_hosts=()):
    u = urllib.parse.urlparse(url)
    if u.username or u.password: raise BridgeError("credentials in URLs are not allowed")
    host = (u.netloc or "").lower()
    if host not in {h.lower() for h in allowed_hosts}: raise BridgeError(f"host '{host}' is not in the allow-list")
    if u.scheme != "https" and not (u.scheme == "http" and host in {h.lower() for h in allow_http_hosts}): raise BridgeError("HTTPS is required for this host")
    return u

def request(method, url, data=None, headers=None, allowed_hosts=(), allow_http_hosts=(), timeout=15, max_resp=1_000_000, secrets=()):
    """-> (status, body bytes). Raises BridgeError with secrets redacted. Never follows redirects."""
    try:
        check_url(url, allowed_hosts, allow_http_hosts)
        req = urllib.request.Request(url, data=data, method=method, headers=dict(headers or {}, **{"User-Agent": "parametric-studio-bridge"}))
        try:
            with _opener.open(req, timeout=timeout) as r: return r.status, r.read(max_resp + 1)[:max_resp]
        except urllib.error.HTTPError as e: return e.code, e.read(max_resp + 1)[:max_resp]
    except BridgeError as e: raise BridgeError(redact(e, secrets))
    except Exception as e: raise BridgeError(redact(f"{type(e).__name__}: {e}", secrets))

def multipart(fields, files):
    """-> (body, content_type). files = {name: (filename, bytes, content_type)}."""
    b = uuid.uuid4().hex; out = []
    for k, v in fields.items(): out.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (fn, data, ct) in files.items(): out.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + data + b"\r\n")
    out.append(f"--{b}--\r\n".encode()); return b"".join(out), f"multipart/form-data; boundary={b}"
