"""Use the studio from a phone. Best route: Tailscale Serve, which gives this machine a private HTTPS address on your tailnet while the studio stays bound to localhost; HTTPS is what lets a phone install the app and use the mic.
Fallback: a plain LAN address. Binding beyond localhost requires a pairing token, because this server can run graphs on your GPU; server.py enforces it. The token is only ever shown to a client on this machine."""
import json, os, shutil, socket, subprocess
from fastapi import APIRouter, Request

router = APIRouter()
LOOPBACK = ("127.0.0.1", "::1", "localhost")

def _run(cmd, timeout=4):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError): return ""

def tailscale_state(run=_run, which=shutil.which):
    """-> {installed, connected, https_url, serving}. https_url is this machine's MagicDNS name; serving says whether `tailscale serve` already forwards it here."""
    if not which("tailscale"): return {"installed": False, "connected": False, "https_url": None, "serving": False}
    try: st = json.loads(run(["tailscale", "status", "--json"]) or "{}")
    except ValueError: st = {}
    name = ((st.get("Self") or {}).get("DNSName") or "").rstrip("."); connected = st.get("BackendState") == "Running"
    return {"installed": True, "connected": connected, "https_url": f"https://{name}" if connected and name else None, "serving": bool(name and name in (run(["tailscale", "serve", "status"]) or ""))}

def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("10.255.255.255", 1)); ip = s.getsockname()[0]; s.close(); return ip
    except OSError: return None

@router.get("/api/phone")
def phone(request: Request):
    port = int(os.environ.get("STUDIO_PORT", "8310")); ts = tailscale_state(); host = os.environ.get("STUDIO_HOST", "127.0.0.1"); token = os.environ.get("STUDIO_TOKEN", ""); local = request.client is not None and request.client.host in LOOPBACK
    out = {"tailscale": ts, "serve_command": f"tailscale serve --bg {port}", "lan_enabled": host not in LOOPBACK, "lan_command": f"STUDIO_HOST=0.0.0.0 python -m studio.server", "url": ts["https_url"] if ts["serving"] else None}
    if out["lan_enabled"] and local and token and lan_ip(): out["lan_url"] = f"http://{lan_ip()}:{port}/?t={token}"
    return out
