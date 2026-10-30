"""Restricted JSON HTTP client (original): a node-friendly way to call a free/own API without SSRF. Only the configured base URL host, JSON in/out, no redirects, size/rate limits, secrets in headers redacted."""
import json
from . import policy as P

def request_json(cfg, method, path, payload=None, timeout=15):
    s = P.section(cfg, "http_api"); base = s.get("base_url", "").rstrip("/"); secrets = P.secrets_of(s) + [str(v) for v in (s.get("headers") or {}).values() if len(str(v)) >= 6]
    if not base.startswith(("http://", "https://")): raise P.BridgeError("http_api.base_url must start with http:// or https://")
    host = base.split("//", 1)[1].split("/", 1)[0]; method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE"): raise P.BridgeError("method not allowed")
    if not path.startswith("/") or ".." in path or "//" in path or "@" in path: raise P.BridgeError("bad path")
    if not P.limiter("http_api", s.get("rate_per_min", 30)).allow(): raise P.BridgeError("rate limit reached for http_api")
    hdr = {"Accept": "application/json", **{str(k): str(v) for k, v in (s.get("headers") or {}).items()}}
    body = None
    if payload is not None: body = json.dumps(payload).encode(); hdr["Content-Type"] = "application/json"
    if body and len(body) > 1_000_000: raise P.BridgeError("payload larger than 1 MB")
    st, resp = P.request(method, base + path, body, hdr, s.get("allowed_hosts") or [host], [host] if base.startswith("http://") and s.get("allow_http") else [], timeout, secrets=secrets)
    try: data = json.loads(resp.decode("utf-8", "replace")) if resp else None
    except json.JSONDecodeError: data = {"text": resp[:2000].decode("utf-8", "replace")}
    return {"status": st, "ok": 200 <= st < 300, "data": data}
