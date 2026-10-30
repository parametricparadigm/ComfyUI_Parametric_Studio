"""Free outbound/inbound bridges (original). Telegram Bot API, Discord/Slack webhooks, ntfy push, remote ComfyUI over HTTP (Tailscale/LAN), folder round-trip (any editor: Krita/GIMP/Photoshop), all via the stdlib and policy.py."""
import json, os, re, time, urllib.parse
from . import policy as P

def _clip(s, n): return (s if len(s) <= n else s[: n - 1] + "…")

# ---------------------------------------------------------------- Telegram (free Bot API)
def _tg(cfg, method, payload=None, files=None, timeout=15):
    s = P.section(cfg, "telegram"); base = s.get("api_base", "https://api.telegram.org").rstrip("/"); token = s.get("token") or ""
    if len(token) < 10: raise P.BridgeError("telegram token missing in config")
    host = base.split("//", 1)[1]; secrets = P.secrets_of(s)
    if not P.limiter("telegram", s.get("rate_per_min", 20)).allow(): raise P.BridgeError("rate limit reached for telegram")
    url = f"{base}/bot{token}/{method}"
    if files: body, ct = P.multipart({k: str(v) for k, v in (payload or {}).items()}, files); hdr = {"Content-Type": ct}
    else: body, hdr = json.dumps(payload or {}).encode(), {"Content-Type": "application/json"}
    st, resp = P.request("POST", url, body, hdr, [host], [host] if base.startswith("http://") else [], timeout, secrets=secrets)
    try: d = json.loads(resp or b"{}")
    except json.JSONDecodeError: d = {}
    if st != 200 or not d.get("ok"): raise P.BridgeError(P.redact(f"telegram error {st}: {d.get('description', '')}", secrets))
    return d

def telegram_send(cfg, chat_id, text=None, image_bytes=None, caption=None):
    s = P.section(cfg, "telegram")
    if int(chat_id) not in {int(x) for x in s.get("allowed_chat_ids", [])}: raise P.BridgeError("chat id is not in allowed_chat_ids")
    if image_bytes is not None:
        if len(image_bytes) > 10_000_000: raise P.BridgeError("image larger than 10 MB")
        d = _tg(cfg, "sendPhoto", {"chat_id": int(chat_id), "caption": _clip(caption or "", 1000)}, {"photo": ("image.png", image_bytes, "image/png")})
    else: d = _tg(cfg, "sendMessage", {"chat_id": int(chat_id), "text": _clip(text or "", 4096)})
    return {"ok": True, "message_id": d.get("result", {}).get("message_id")}

def parse_command(text, commands):
    """'/video a red fox' -> ('video', 'a red fox') only if 'video' is a configured command; else None. Commands map to NAMED workflows, never to raw graphs."""
    m = re.match(r"^/([A-Za-z0-9_]{1,32})(?:@\w+)?(?:\s+(.{0,500}))?$", (text or "").strip(), re.S)
    if not m or m.group(1) not in (commands or {}): return None
    return m.group(1), (m.group(2) or "").strip()

def telegram_poll(cfg, offset=0, commands=None):
    s = P.section(cfg, "telegram"); allowed = {int(x) for x in s.get("allowed_chat_ids", [])}
    d = _tg(cfg, "getUpdates", {"offset": int(offset), "timeout": 0, "limit": 20}); out, ignored, nxt = [], 0, int(offset)
    for u in d.get("result", [])[:20]:
        nxt = max(nxt, int(u.get("update_id", 0)) + 1); m = u.get("message") or {}; chat = (m.get("chat") or {}).get("id")
        if chat is None or int(chat) not in allowed: ignored += 1; continue
        c = parse_command(m.get("text", ""), commands)
        if not c: ignored += 1; continue
        out.append({"chat_id": int(chat), "user_id": (m.get("from") or {}).get("id"), "command": c[0], "args": c[1], "workflow": (commands or {}).get(c[0])})
    return {"next_offset": nxt, "commands": out, "ignored": ignored}

# ---------------------------------------------------------------- Discord / Slack webhooks, ntfy push (all free)
def discord_send(cfg, content=None, image_bytes=None, filename="image.png"):
    s = P.section(cfg, "discord"); url = s.get("webhook_url", ""); secrets = P.secrets_of(s); host = url.split("//", 1)[-1].split("/", 1)[0] if "//" in url else ""
    allowed = s.get("allowed_hosts") or ["discord.com", "discordapp.com"]
    if not P.limiter("discord", s.get("rate_per_min", 20)).allow(): raise P.BridgeError("rate limit reached for discord")
    http_ok = [host] if url.startswith("http://") and s.get("allow_http") else []
    if image_bytes is not None:
        if len(image_bytes) > 8_000_000: raise P.BridgeError("image larger than 8 MB")
        body, ct = P.multipart({"content": _clip(content or "", 2000)}, {"file": (re.sub(r"[^A-Za-z0-9_.-]", "_", filename), image_bytes, "image/png")}); hdr = {"Content-Type": ct}
    else: body, hdr = json.dumps({"content": _clip(content or "", 2000)}).encode(), {"Content-Type": "application/json"}
    st, _ = P.request("POST", url, body, hdr, allowed, http_ok, secrets=secrets)
    if st not in (200, 204): raise P.BridgeError(f"discord error {st}")
    return {"ok": True}

def slack_send(cfg, text):
    s = P.section(cfg, "slack"); url = s.get("webhook_url", ""); secrets = P.secrets_of(s); host = url.split("//", 1)[-1].split("/", 1)[0] if "//" in url else ""
    if not P.limiter("slack", s.get("rate_per_min", 20)).allow(): raise P.BridgeError("rate limit reached for slack")
    st, _ = P.request("POST", url, json.dumps({"text": _clip(text or "", 3000)}).encode(), {"Content-Type": "application/json"}, s.get("allowed_hosts") or ["hooks.slack.com"], [host] if url.startswith("http://") and s.get("allow_http") else [], secrets=secrets)
    if st != 200: raise P.BridgeError(f"slack error {st}")
    return {"ok": True}

def ntfy_publish(cfg, message, title=None, priority=3, tags=None):
    """Free phone push notifications (ntfy.sh or your own ntfy server, e.g. over Tailscale). The topic acts like a password: keep it secret and long."""
    s = P.section(cfg, "ntfy"); server = s.get("server", "https://ntfy.sh").rstrip("/"); topic = s.get("topic", ""); secrets = P.secrets_of(s)
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", topic): raise P.BridgeError("ntfy topic must be 6-64 letters, digits, - or _")
    host = server.split("//", 1)[1]
    if not P.limiter("ntfy", s.get("rate_per_min", 30)).allow(): raise P.BridgeError("rate limit reached for ntfy")
    hdr = {"Priority": str(max(1, min(int(priority), 5)))}
    if title: hdr["Title"] = re.sub(r"[^\x20-\x7e]", "?", title)[:100]
    if tags: hdr["Tags"] = re.sub(r"[^A-Za-z0-9_,+-]", "", ",".join(tags))[:100]
    st, _ = P.request("POST", f"{server}/{topic}", _clip(message or "", 4000).encode(), hdr, [host], [host] if server.startswith("http://") else [], secrets=secrets)
    if st != 200: raise P.BridgeError(f"ntfy error {st}")
    return {"ok": True}

# ---------------------------------------------------------------- remote ComfyUI (Tailscale/LAN), free
def remote_queue(cfg, prompt, object_info=None, wait=True, timeout_s=600, poll_s=2.0):
    s = P.section(cfg, "remote_comfy"); host = s.get("host", ""); secrets = P.secrets_of(s); hdr = {"Content-Type": "application/json"}
    if s.get("api_key"): hdr["Authorization"] = "Bearer " + s["api_key"]
    if object_info is not None:
        from ..graph import GraphBuilder
        errs = GraphBuilder.from_prompt(prompt).validate(object_info)
        if errs: raise P.BridgeError("graph failed validation: " + "; ".join(errs[:5]))
    scheme = "https" if s.get("https") else "http"; base = f"{scheme}://{host}"; allow = [host]; http = [host] if scheme == "http" else []
    if not P.limiter("remote_comfy", s.get("rate_per_min", 30)).allow(): raise P.BridgeError("rate limit reached for remote_comfy")
    st, body = P.request("POST", base + "/prompt", json.dumps({"prompt": prompt}).encode(), hdr, allow, http, secrets=secrets)
    if st != 200: raise P.BridgeError(f"remote rejected the graph ({st}): {body[:300].decode('utf-8', 'replace')}")
    pid = json.loads(body)["prompt_id"]; t0 = time.time()
    while wait and time.time() - t0 < timeout_s:
        st, body = P.request("GET", f"{base}/history/{pid}", None, hdr, allow, http, secrets=secrets); h = json.loads(body or b"{}")
        if pid in h and h[pid].get("outputs") is not None and h[pid].get("status", {}).get("completed") is not None:
            return {"ok": h[pid]["status"].get("status_str") == "success", "prompt_id": pid, "outputs": h[pid]["outputs"]}
        time.sleep(poll_s)
    return {"ok": False, "prompt_id": pid, "outputs": {}, "note": "not waiting or timed out"}

# ---------------------------------------------------------------- folder round-trip (works with Krita, GIMP, Photoshop or any editor)
def _safe_name(name): return re.sub(r"[^A-Za-z0-9_-]", "_", name)[:60] or "image"

def folder_roundtrip(directory, image_bytes, name="image", wait_s=300, poll_s=1.0):
    """Write <dir>/out/<name>.png, then wait for an edited <dir>/in/<name>*.png and return its bytes (or None on timeout)."""
    base = os.path.realpath(directory); out_d, in_d = os.path.join(base, "out"), os.path.join(base, "in"); os.makedirs(out_d, exist_ok=True); os.makedirs(in_d, exist_ok=True)
    nm = _safe_name(name); open(os.path.join(out_d, nm + ".png"), "wb").write(image_bytes); t0 = time.time(); start = time.time() - 1
    while time.time() - t0 <= wait_s:
        for f in sorted(os.listdir(in_d)):
            p = os.path.join(in_d, f)
            if f.startswith(nm) and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and os.path.getmtime(p) >= start and os.path.getsize(p) < 50_000_000 and os.path.realpath(p).startswith(in_d + os.sep):
                time.sleep(0.2); return open(p, "rb").read()
        time.sleep(poll_s)
    return None
