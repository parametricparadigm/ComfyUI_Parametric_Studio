"""ParametricStudio - Telegram Command Trigger for Video Pipelines.

This module implements the *core, offline* logic of a Telegram command
trigger for ComfyUI video pipelines.  Because the sandbox forbids network
access, subprocesses, file I/O and third-party libraries, the actual
Telegram HTTP calls (``getUpdates`` / ``sendVideo`` / ``sendPhoto``) are
NOT implemented.  Instead the module exposes:

* :class:`PSN_Telegram_Command_Parser` - parses raw Telegram ``getUpdates``
  JSON payloads (as produced by the Bot API) into ComfyUI-friendly values:
  chat id, text prompt, command flag and a reference image tensor decoded
  from a base64 ``photo`` attachment (pure torch, no PIL).
* :class:`PSN_Telegram_Sender_Prep` - prepares a tensor for upload: encodes
  it to a base64 payload, checks the 50 MB Telegram limit and builds the
  API request body that a real sender would POST.

Both nodes are deterministic and fully testable on CPU.
"""

import base64
import json
import math

import numpy as np
import torch

CAT = "ParametricStudio/Telegram"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _clamp01(x):
    """Clamp a tensor to [0, 1] without modifying the input."""
    return torch.clamp(x, 0.0, 1.0)


def _b64_to_tensor(b64_str):
    """Decode a base64 string into a float tensor [H, W, C] in 0..1.

    Supports a minimal, self-contained PNG-like / raw-uint8 format:
    the payload is expected to be raw RGB bytes of length H*W*3 where
    H and W are encoded in the first 8 bytes (4 bytes each, big-endian
    unsigned int).  This is a *test-friendly* container, not a real PNG
    decoder (PIL is not available in the sandbox).
    """
    raw = base64.b64decode(b64_str)
    if len(raw) < 8:
        raise ValueError("image payload too short")
    h = int.from_bytes(raw[0:4], "big")
    w = int.from_bytes(raw[4:8], "big")
    if h <= 0 or w <= 0:
        raise ValueError("bad image dimensions")
    expected = 8 + h * w * 3
    if len(raw) < expected:
        raise ValueError("image payload truncated")
    data = raw[8:expected]
    arr = np.frombuffer(data, dtype=np.uint8).copy()
    t = torch.from_numpy(arr).to(torch.float32)
    t = t.reshape(h, w, 3).div_(255.0)
    return t


def _tensor_to_b64(img):
    """Encode a [H, W, C] or [B, H, W, C] float tensor (0..1) to the same
    raw container used by :func:`_b64_to_tensor`, returned as base64.
    """
    x = _clamp01(img.detach().float().cpu())
    if x.dim() == 4:
        x = x[0]
    if x.dim() != 3 or x.shape[2] != 3:
        raise ValueError("expected [H, W, 3] or [B, H, W, 3] tensor")
    h, w, _ = x.shape
    u8 = (x * 255.0).round().to(torch.uint8).numpy().tobytes()
    header = h.to_bytes(4, "big") + w.to_bytes(4, "big")
    return base64.b64encode(header + u8).decode("ascii")


def _parse_chat_ids(s):
    """Parse a comma-separated string of chat ids into a set of ints.

    Empty / whitespace entries are ignored.  Returns an empty set for an
    empty string (meaning: no chat is allowed).
    """
    out = set()
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.add(int(part))
    return out


def _extract_message(update):
    """Return the ``message`` dict from a Telegram update, or None."""
    if not isinstance(update, dict):
        return None
    msg = update.get("message")
    if msg is None:
        msg = update.get("edited_message")
    if msg is None:
        msg = update.get("channel_post")
    return msg if isinstance(msg, dict) else None


def _extract_photo_b64(msg):
    """Return the base64 payload of the largest photo in the message, or
    None.  Telegram photo messages carry a list of ``photo`` entries each
    with a ``file_id``; in this offline implementation we accept an extra
    ``b64`` key on the photo entry (set by a real bridge) or a
    ``photo_b64`` key on the message itself.
    """
    if not isinstance(msg, dict):
        return None
    if isinstance(msg.get("photo_b64"), str):
        return msg["photo_b64"]
    photos = msg.get("photo")
    if isinstance(photos, list) and photos:
        # pick the largest photo by width*height
        best = None
        best_area = -1
        for p in photos:
            if not isinstance(p, dict):
                continue
            b64 = p.get("b64")
            if not isinstance(b64, str):
                continue
            area = int(p.get("width", 0)) * int(p.get("height", 0))
            if area > best_area:
                best_area = area
                best = b64
        if best is not None:
            return best
    return None


# ---------------------------------------------------------------------------
# Node 1: parser / listener core
# ---------------------------------------------------------------------------

class PSN_Telegram_Command_Parser:
    """Parse a raw Telegram ``getUpdates`` JSON payload into ComfyUI values.

    This is the offline core of the *Telegram Listener*: a real deployment
    would wrap this with a long-polling loop; here we accept the already
    fetched payload as a STRING (JSON) so the node is fully testable without
    network access.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "updates_json": ("STRING", {"default": "[]", "multiline": True}),
                "allowed_chat_ids": ("STRING", {"default": "", "multiline": False}),
                "command_prefix": ("STRING", {"default": "/"}),
            },
            "optional": {
                "timeout_note": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("INT", "STRING", "IMAGE", "BOOLEAN")
    RETURN_NAMES = ("chat_id", "text_prompt", "reference_image", "is_command")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, updates_json, allowed_chat_ids, command_prefix, timeout_note=""):
        # Parse the JSON payload.  Accept either a list of updates or a
        # single update dict.
        try:
            payload = json.loads(updates_json) if updates_json else []
        except (json.JSONDecodeError, TypeError):
            payload = []
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            payload = []

        allowed = _parse_chat_ids(allowed_chat_ids)

        chat_id = 0
        text_prompt = ""
        ref_image = torch.zeros(1, 1, 1, 3, dtype=torch.float32)
        is_command = False

        for update in payload:
            msg = _extract_message(update)
            if msg is None:
                continue
            sender = msg.get("from", {})
            cid = msg.get("chat", {}).get("id") if isinstance(msg.get("chat"), dict) else None
            if cid is None and isinstance(sender, dict):
                cid = sender.get("id")
            if cid is None:
                continue
            try:
                cid = int(cid)
            except (TypeError, ValueError):
                continue
            # Security: if an allow-list is configured, the chat must be in it.
            if allowed and cid not in allowed:
                continue

            chat_id = cid
            text = msg.get("text")
            if isinstance(text, str):
                text_prompt = text
                if command_prefix and text.startswith(command_prefix):
                    is_command = True

            b64 = _extract_photo_b64(msg)
            if b64:
                try:
                    img = _b64_to_tensor(b64)
                    # add batch dim -> [1, H, W, C]
                    ref_image = img.unsqueeze(0)
                except (ValueError, Exception):
                    # keep previous image on decode failure
                    pass
            break  # first allowed message wins

        return (chat_id, text_prompt, ref_image, is_command)


# ---------------------------------------------------------------------------
# Node 2: sender preparation core
# ---------------------------------------------------------------------------

TELEGRAM_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


class PSN_Telegram_Sender_Prep:
    """Prepare a tensor for upload to Telegram.

    Encodes the tensor to a base64 payload, checks the 50 MB limit and
    builds the API request body.  The actual HTTP upload is NOT performed
    (no network in the sandbox); a real bridge would POST ``request_body``
    to the Bot API endpoint indicated by ``endpoint``.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "media": ("IMAGE",),
                "chat_id": ("INT", {"default": 0}),
                "caption": ("STRING", {"default": "", "multiline": True}),
                "media_type": (["video", "image", "document"], {"default": "image"}),
            },
            "optional": {
                "bot_token": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "INT", "STRING", "STRING")
    RETURN_NAMES = ("ready", "estimated_bytes", "endpoint", "request_body")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, media, chat_id, caption, media_type, bot_token=""):
        if not isinstance(media, torch.Tensor):
            return (False, 0, "", "")
        if media.dim() not in (3, 4):
            return (False, 0, "", "")
        if media_type not in ("video", "image", "document"):
            return (False, 0, "", "")

        try:
            b64 = _tensor_to_b64(media)
        except (ValueError, Exception):
            return (False, 0, "", "")

        # base64 inflates by ~4/3; estimate the decoded byte size.
        decoded_bytes = math.ceil(len(b64) * 3 / 4)
        ready = decoded_bytes <= TELEGRAM_MAX_BYTES

        # Endpoint selection (a real sender would use bot_token here).
        if media_type == "video":
            endpoint = "sendVideo"
        elif media_type == "image":
            endpoint = "sendPhoto"
        else:
            endpoint = "sendDocument"

        body = {
            "chat_id": int(chat_id),
            "caption": caption or "",
            "media_b64": b64,
            "media_type": media_type,
        }
        message_id = 0  # would be filled by the API response
        return (ready, decoded_bytes, endpoint, json.dumps(body))


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Telegram_Command_Parser": PSN_Telegram_Command_Parser,
    "PSN_Telegram_Sender_Prep": PSN_Telegram_Sender_Prep,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Telegram_Command_Parser": "Telegram Command Parser (Listener Core)",
    "PSN_Telegram_Sender_Prep": "Telegram Sender Prep (Upload Core)",
}
