"""Small HTTP helpers shared by the connectors: JSON GET, and a download that never forwards credentials to a redirect target. `opener` is injectable so tests never touch the network."""
import json, os, hashlib, shutil, urllib.request, urllib.parse, urllib.error

class ConnectorError(RuntimeError): pass

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None

def default_opener(): return urllib.request.build_opener(_NoRedirect)

def get_json(url, headers=None, opener=None, timeout=30):
    try:
        with (opener or default_opener()).open(urllib.request.Request(url, headers={"User-Agent": "psn-connector/1", **(headers or {})}), timeout=timeout) as r: return json.loads(r.read(5_000_000) or b"{}")
    except urllib.error.HTTPError as e: raise ConnectorError(f"{url.split('?')[0]} -> HTTP {e.code}" + (" (rate limited: wait and retry)" if e.code == 429 else "")) from None
    except (urllib.error.URLError, ValueError) as e: raise ConnectorError(f"{url.split('?')[0]} failed: {type(e).__name__}") from None

def download(url, dest, sha256=None, token=None, opener=None, max_bytes=None, min_free_factor=2.0, timeout=60):
    """Stream `url` to `dest` (via dest+'.part'). The token is sent to the first host only; a redirect (to a pre-signed storage URL) is followed WITHOUT it. Returns the final path.
    Refuses when free disk is under min_free_factor x the announced size, when the size exceeds max_bytes, or when the SHA-256 differs from `sha256`."""
    op = opener or default_opener(); hdr = {"User-Agent": "psn-connector/1"}
    if token: hdr["Authorization"] = "Bearer " + token
    try:
        try: resp = op.open(urllib.request.Request(url, headers=hdr), timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                resp = op.open(urllib.request.Request(urllib.parse.urljoin(url, e.headers["Location"]), headers={"User-Agent": "psn-connector/1"}), timeout=timeout)   # no Authorization here
            elif e.code in (401, 403): raise ConnectorError("the service wants a login token for this file (set the token environment variable)") from None
            else: raise ConnectorError(f"download -> HTTP {e.code}") from None
    except urllib.error.URLError as e: raise ConnectorError(f"download failed: {type(e).__name__}") from None
    size = int(resp.headers.get("Content-Length") or 0)
    if max_bytes and size > max_bytes: raise ConnectorError(f"file is {size} bytes, over the limit {max_bytes}")
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    if size and shutil.disk_usage(os.path.dirname(os.path.abspath(dest))).free < size * min_free_factor: raise ConnectorError("not enough free disk space")
    h = hashlib.sha256(); part = dest + ".part"
    with resp, open(part, "wb") as f:
        while chunk := resp.read(1 << 20): f.write(chunk); h.update(chunk)
    if sha256 and h.hexdigest().lower() != sha256.lower(): os.remove(part); raise ConnectorError("SHA-256 does not match what the service reported; file discarded")
    os.replace(part, dest); return dest
