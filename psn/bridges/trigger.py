"""Named-workflow trigger server (original): lets a phone/bot/script start PRE-APPROVED workflows over HTTP. Never accepts raw graphs.
A workflow is <dir>/<name>.json (API-format template with {{param}} placeholders) plus optional <name>.params.json (schema). Requests: POST /run/<name> {"params": {...}} with 'Authorization: Bearer <token>'.
Off unless config 'trigger' is enabled; binds 127.0.0.1 by default (use your Tailscale IP to reach it from the phone)."""
import hmac, json, os, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import policy as P

NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

def validate_params(schema, params):
    """schema = {name: {"type": "int|float|string|bool|choice", "min","max","max_len","choices","default"}} -> clean dict. Unknown params are rejected."""
    if not isinstance(params, dict): raise P.BridgeError("params must be an object")
    extra = set(params) - set(schema)
    if extra: raise P.BridgeError(f"unknown parameters: {sorted(extra)}")
    out = {}
    for k, sp in schema.items():
        if k not in params:
            if "default" in sp: out[k] = sp["default"]; continue
            raise P.BridgeError(f"missing parameter '{k}'")
        v, t = params[k], sp.get("type", "string")
        if t == "int":
            if isinstance(v, bool) or not isinstance(v, int): raise P.BridgeError(f"{k}: integer expected")
        elif t == "float":
            if isinstance(v, bool) or not isinstance(v, (int, float)): raise P.BridgeError(f"{k}: number expected")
        elif t == "bool":
            if not isinstance(v, bool): raise P.BridgeError(f"{k}: true/false expected")
        elif t == "choice":
            if v not in sp.get("choices", []): raise P.BridgeError(f"{k}: not an allowed choice")
        elif t == "string":
            if not isinstance(v, str) or len(v) > int(sp.get("max_len", 500)): raise P.BridgeError(f"{k}: text up to {sp.get('max_len', 500)} characters expected")
        else: raise P.BridgeError(f"{k}: unknown type")
        if t in ("int", "float"):
            if "min" in sp and v < sp["min"] or "max" in sp and v > sp["max"]: raise P.BridgeError(f"{k}: out of range")
        out[k] = v
    return out

def render(template, params):
    """Substitute {{name}} inside STRING VALUES of the parsed template (never in keys or structure); a value that is exactly '{{name}}' keeps the parameter's type."""
    def sub(x):
        if isinstance(x, dict): return {k: sub(v) for k, v in x.items()}
        if isinstance(x, list): return [sub(v) for v in x]
        if isinstance(x, str):
            m = re.fullmatch(r"\{\{(\w+)\}\}", x)
            if m and m.group(1) in params: return params[m.group(1)]
            return re.sub(r"\{\{(\w+)\}\}", lambda mm: str(params.get(mm.group(1), mm.group(0))), x)
        return x
    return sub(template)

def load_workflow(directory, name):
    if not NAME.match(name): raise P.BridgeError("bad workflow name")
    p = os.path.join(os.path.realpath(directory), name + ".json")
    if not os.path.isfile(p): raise P.BridgeError("unknown workflow")
    sp = p[:-5] + ".params.json"
    return json.load(open(p)), (json.load(open(sp)) if os.path.isfile(sp) else {})

def make_server(cfg, queue_fn=None):
    """Returns an unstarted ThreadingHTTPServer. queue_fn(prompt)->{"prompt_id":..}; default queues on the local ComfyUI given by config trigger.comfy."""
    s = P.section(cfg, "trigger"); token = s.get("token", ""); wf_dir = s.get("workflows_dir", "")
    if len(token) < 16: raise P.BridgeError("trigger.token must be at least 16 characters")
    host, port = (s.get("listen") or "127.0.0.1:8480").rsplit(":", 1); rate = s.get("rate_per_min", 10)
    if queue_fn is None:
        comfy = s.get("comfy", "127.0.0.1:8200")
        def queue_fn(prompt):
            st, body = P.request("POST", f"http://{comfy}/prompt", json.dumps({"prompt": prompt}).encode(), {"Content-Type": "application/json"}, [comfy], [comfy])
            if st != 200: raise P.BridgeError(f"ComfyUI rejected the workflow ({st})")
            return json.loads(body)
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj): b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def _auth(self):
            got = (self.headers.get("Authorization") or "")[7:] if (self.headers.get("Authorization") or "").startswith("Bearer ") else ""
            return hmac.compare_digest(got.encode(), token.encode())
        def do_GET(self):
            if not self._auth(): return self._send(401, {"error": "unauthorized"})
            if self.path == "/workflows": return self._send(200, {"workflows": sorted(f[:-5] for f in os.listdir(wf_dir) if f.endswith(".json") and not f.endswith(".params.json"))})
            self._send(404, {"error": "not found"})
        def do_POST(self):
            if not self._auth(): return self._send(401, {"error": "unauthorized"})
            if not P.limiter("trigger", rate).allow(): return self._send(429, {"error": "rate limit"})
            m = re.fullmatch(r"/run/([A-Za-z0-9_-]{1,64})", self.path)
            if not m: return self._send(404, {"error": "not found"})
            n = int(self.headers.get("Content-Length") or 0)
            if n > 65536: return self._send(413, {"error": "body too large"})
            try:
                data = json.loads(self.rfile.read(n) or b"{}"); tpl, schema = load_workflow(wf_dir, m.group(1)); params = validate_params(schema, data.get("params", {}))
                self._send(200, {"ok": True, **queue_fn(render(tpl, params))})
            except (P.BridgeError, json.JSONDecodeError, AttributeError) as e: self._send(400, {"error": str(e)[:200]})
        def log_message(self, *a): pass
    return ThreadingHTTPServer((host, int(port)), H)

if __name__ == "__main__":
    srv = make_server(P.load_config()); print("PSN trigger server on", srv.server_address); srv.serve_forever()
