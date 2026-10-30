"""ComfyUI wrappers for the free bridges (original). Every node is OFF until the matching section of ~/.config/parametric_studio/bridges.json (chmod 600) sets "enabled": true.
Notification-type nodes never raise: a failed message must not break a render, they return (status, ok=False). Secrets are never shown in outputs."""
import io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn.bridges import policy as P, clients as C, osc as O
from .logic import ANY

CAT = "ParametricStudio/Bridges"

def _cfg(): return P.load_config(os.environ.get("PSN_BRIDGE_CONFIG"))

def _png(image):
    import numpy as np
    from PIL import Image
    a = image[0].cpu().numpy() if hasattr(image[0], "cpu") else np.asarray(image[0]); a = (np.clip(a, 0, 1) * 255).astype("uint8")
    b = io.BytesIO(); Image.fromarray(a[..., :3]).save(b, "PNG"); return b.getvalue()

def _tensor(png):
    import numpy as np, torch
    from PIL import Image
    return torch.from_numpy(np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), dtype="float32")[None] / 255.0)

def _safe(fn):
    try: return fn()
    except P.BridgeError as e: return "error: " + str(e)

class PSN_NtfyNotify:
    """Free phone push notification via ntfy (ntfy.sh or your own server, e.g. over Tailscale)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"message": ("STRING", {"multiline": True, "default": "Render finished"}), "title": ("STRING", {"default": "Parametric Studio"}), "priority": ("INT", {"default": 3, "min": 1, "max": 5})}}
    RETURN_TYPES = ("STRING", "BOOLEAN"); RETURN_NAMES = ("status", "ok"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True
    def run(self, message, title, priority):
        s = _safe(lambda: (C.ntfy_publish(_cfg(), message, title, priority), "sent")[1]); return (s, s == "sent")

class PSN_TelegramSend:
    """Send text or an image to an allow-listed Telegram chat (free Bot API; token lives in the config file, not the workflow)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"chat_id": ("INT", {"default": 0, "min": -10**15, "max": 10**15}), "text": ("STRING", {"multiline": True, "default": ""})}, "optional": {"image": ("IMAGE",)}}
    RETURN_TYPES = ("STRING", "BOOLEAN"); RETURN_NAMES = ("status", "ok"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True
    def run(self, chat_id, text, image=None):
        s = _safe(lambda: (C.telegram_send(_cfg(), chat_id, text=text, image_bytes=_png(image) if image is not None else None, caption=text), "sent")[1]); return (s, s == "sent")

class PSN_TelegramPoll:
    """Check for new commands from allow-listed chats. Only commands listed in commands_json map to NAMED workflows: {"video": "wan_t2v"}."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"offset": ("INT", {"default": 0, "min": 0, "max": 2**62}), "commands_json": ("STRING", {"multiline": True, "default": "{}"})}}
    RETURN_TYPES = ("INT", "STRING", "INT", "STRING"); RETURN_NAMES = ("next_offset", "commands_json", "ignored", "status"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, offset, commands_json):
        try: r = C.telegram_poll(_cfg(), offset, json.loads(commands_json or "{}")); return (r["next_offset"], json.dumps(r["commands"]), r["ignored"], "ok")
        except (P.BridgeError, json.JSONDecodeError) as e: return (offset, "[]", 0, "error: " + str(e))

class PSN_DiscordWebhook:
    """Post text and/or an image to a Discord webhook (free)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"content": ("STRING", {"multiline": True, "default": ""})}, "optional": {"image": ("IMAGE",)}}
    RETURN_TYPES = ("STRING", "BOOLEAN"); RETURN_NAMES = ("status", "ok"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True
    def run(self, content, image=None):
        s = _safe(lambda: (C.discord_send(_cfg(), content, _png(image) if image is not None else None), "sent")[1]); return (s, s == "sent")

class PSN_SlackSend:
    """Post text to a Slack incoming webhook (free)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"text": ("STRING", {"multiline": True, "default": ""})}}
    RETURN_TYPES = ("STRING", "BOOLEAN"); RETURN_NAMES = ("status", "ok"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True
    def run(self, text):
        s = _safe(lambda: (C.slack_send(_cfg(), text), "sent")[1]); return (s, s == "sent")

class PSN_OSCSend:
    """Send an OSC message over UDP (localhost only): TouchDesigner, Resolume, Unreal, Max, VCV..."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"host": ("STRING", {"default": "127.0.0.1"}), "port": ("INT", {"default": 9000, "min": 1, "max": 65535}), "address": ("STRING", {"default": "/psn/status"}), "args_json": ("STRING", {"default": "[1]"})}}
    RETURN_TYPES = ("STRING", "BOOLEAN"); RETURN_NAMES = ("status", "ok"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True
    def run(self, host, port, address, args_json):
        try: O.send(host, port, address, json.loads(args_json or "[]")); return ("sent", True)
        except (O.OSCError, json.JSONDecodeError, OSError) as e: return ("error: " + str(e), False)

class PSN_OSCReceive:
    """Wait for one OSC message on a localhost UDP port (times out)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"port": ("INT", {"default": 9001, "min": 1, "max": 65535}), "timeout_s": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 60.0})}}
    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN"); RETURN_NAMES = ("address", "args_json", "got"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, port, timeout_s):
        try: r = O.receive(port, timeout_s)
        except (O.OSCError, OSError): r = None
        return (r[0], json.dumps(r[1]), True) if r else ("", "[]", False)

class PSN_RemoteQueue:
    """Queue an API-format graph on a remote ComfyUI (Tailscale/LAN host from the config file) and wait for it. Optionally validates the graph first."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"prompt_json": ("STRING", {"multiline": True, "default": "{}"}), "timeout_s": ("INT", {"default": 600, "min": 5, "max": 3600})}}
    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING", "STRING"); RETURN_NAMES = ("ok", "prompt_id", "outputs_json", "status"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True
    def run(self, prompt_json, timeout_s):
        try: r = C.remote_queue(_cfg(), json.loads(prompt_json), timeout_s=timeout_s); return (r["ok"], r["prompt_id"], json.dumps(r["outputs"]), "done" if r["ok"] else r.get("note", "failed"))
        except (P.BridgeError, json.JSONDecodeError) as e: return (False, "", "{}", "error: " + str(e))

class PSN_FolderRoundtrip:
    """Send an image to an editor via a folder (works with Krita, GIMP, Photoshop...): writes <dir>/out/<name>.png and waits for the edited file in <dir>/in/."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"image": ("IMAGE",), "directory": ("STRING", {"default": "/tmp/psn_roundtrip"}), "name": ("STRING", {"default": "image"}), "wait_s": ("INT", {"default": 300, "min": 1, "max": 3600})}}
    RETURN_TYPES = ("IMAGE", "BOOLEAN"); RETURN_NAMES = ("edited", "got_edit"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, image, directory, name, wait_s):
        b = C.folder_roundtrip(directory, _png(image), name, wait_s); return (_tensor(b), True) if b else (image, False)

NODE_CLASS_MAPPINGS = {c.__name__: c for c in (PSN_NtfyNotify, PSN_TelegramSend, PSN_TelegramPoll, PSN_DiscordWebhook, PSN_SlackSend, PSN_OSCSend, PSN_OSCReceive, PSN_RemoteQueue, PSN_FolderRoundtrip)}
NODE_DISPLAY_NAME_MAPPINGS = {k: "PSN " + k[4:].replace("_", " ") for k in NODE_CLASS_MAPPINGS}

# ---------------------------------------------------------------- second batch: restricted HTTP, delivery folder
from psn.bridges import http_api as _H, deliver as _D

class PSN_HttpRequest:
    """JSON request to ONE configured API (config section http_api: base_url, optional headers/allowed_hosts). No redirects, size/rate limits, secrets redacted."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"method": (["GET", "POST", "PUT", "DELETE"],), "path": ("STRING", {"default": "/"}), "payload_json": ("STRING", {"multiline": True, "default": ""})}}
    RETURN_TYPES = ("INT", "STRING", "BOOLEAN"); RETURN_NAMES = ("status", "response_json", "ok"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, method, path, payload_json):
        try: r = _H.request_json(_cfg(), method, path, json.loads(payload_json) if payload_json.strip() else None); return (r["status"], json.dumps(r["data"]), r["ok"])
        except (P.BridgeError, json.JSONDecodeError) as e: return (0, json.dumps({"error": str(e)}), False)

class PSN_DeliverToFolder:
    """Save images into a watched delivery folder (Eagle, DaVinci Resolve, Nuke, Krita...). Only under the roots in config section deliver; names sanitised; never overwrites; optional sidecar JSON."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"image": ("IMAGE",), "name": ("STRING", {"default": "image"}), "subfolder": ("STRING", {"default": ""}), "meta_json": ("STRING", {"multiline": True, "default": "{}"})}}
    RETURN_TYPES = ("STRING", "BOOLEAN"); RETURN_NAMES = ("path_or_error", "ok"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True
    def run(self, image, name, subfolder, meta_json):
        try:
            import numpy as np
            files = [(f"{name}_{i}.png" if len(image) > 1 else f"{name}.png", _png(image[i:i + 1])) for i in range(len(image))]
            return (", ".join(_D.deliver(_cfg(), files, subfolder, json.loads(meta_json or "{}"))), True)
        except (P.BridgeError, json.JSONDecodeError) as e: return ("error: " + str(e), False)

NODE_CLASS_MAPPINGS.update({"PSN_HttpRequest": PSN_HttpRequest, "PSN_DeliverToFolder": PSN_DeliverToFolder})
NODE_DISPLAY_NAME_MAPPINGS.update({"PSN_HttpRequest": "PSN Http Request (restricted)", "PSN_DeliverToFolder": "PSN Deliver To Folder"})
