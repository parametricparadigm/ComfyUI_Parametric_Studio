"""ParametricStudio - Real-Time TouchDesigner Visuals.

Core (offline, torch/stdlib only):
  - PSN_TD_FrameEncode: encode an IMAGE tensor to a deterministic byte payload
    (header + raw RGBA bytes) and report its size. This is the exact payload
    that a real OSC-blob / WebSocket-binary transport would send to TouchDesigner.
  - PSN_TD_Control_Parse: parse an incoming OSC-style control message
    ("/control/<command> <value>") into a command string and a float value.

NOT implemented (needs network / external libs, forbidden here):
  - Actual OSC (python-osc) or WebSocket (websocket-client) transmission.
  - Blocking listener socket for PSN_TD_Control_In (no network allowed).
    Instead the parsing logic is exposed as a pure function so it can be
    unit-tested and wired to a real listener later.
"""

import struct
import torch

CAT = "ParametricStudio/TouchDesigner"

_MAGIC = b"PSND"


def _as_tensor(image):
    """Coerce input to a float torch tensor (never in place)."""
    if isinstance(image, torch.Tensor):
        return image
    raise TypeError("image must be a torch.Tensor")


def encode_frame(image, channel="video_in"):
    """Encode an IMAGE tensor [B,H,W,C] in 0..1 to a byte payload.

    Layout:
      4s  magic b"PSNTD1"
      4s  channel (padded/truncated to 4 bytes)
      4B  B (uint32 LE)
      4B  H (uint32 LE)
      4B  W (uint32 LE)
      4B  C (uint32 LE)
      ... raw uint8 RGBA bytes (B*H*W*C)

    Returns (payload: bytes, meta: dict).
    """
    x = _as_tensor(image)
    if x.dim() != 4:
        raise ValueError("image must be [B,H,W,C], got %d dims" % x.dim())
    B, H, W, C = x.shape
    if C not in (1, 3, 4):
        raise ValueError("channels must be 1, 3 or 4, got %d" % C)
    # clamp to 0..1 and scale to uint8; clone so we never touch the input
    xc = x.detach().float().clamp(0.0, 1.0)
    u8 = (xc * 255.0 + 0.5).to(torch.uint8).contiguous()
    raw = u8.numpy().tobytes()
    ch = channel.encode("utf-8")[:4].ljust(4, b"\x00")
    header = _MAGIC + ch + struct.pack("<IIII", B, H, W, C)
    # header is 4 (magic) + 4 (channel) + 16 (dims) = 24 bytes
    assert len(header) == 24, "header must be 24 bytes, got %d" % len(header)
    payload = header + raw
    meta = {
        "magic": _MAGIC.decode("ascii"),
        "channel": ch.rstrip(b"\x00").decode("utf-8", "replace"),
        "B": B, "H": H, "W": W, "C": C,
        "raw_bytes": len(raw),
        "total_bytes": len(payload),
    }
    return payload, meta


def decode_frame(payload):
    """Inverse of encode_frame. Returns (tensor [B,H,W,C] float 0..1, meta)."""
    if len(payload) < 24:
        raise ValueError("payload too short")
    magic = payload[:4]
    if magic != _MAGIC:
        raise ValueError("bad magic %r" % magic)
    ch = payload[4:8].rstrip(b"\x00").decode("utf-8", "replace")
    B, H, W, C = struct.unpack("<IIII", payload[8:24])
    raw = payload[24:]
    if len(raw) != B * H * W * C:
        raise ValueError("raw size mismatch: %d != %d" % (len(raw), B * H * W * C))
    u8 = torch.frombuffer(raw, dtype=torch.uint8).reshape(B, H, W, C)
    x = u8.float() / 255.0
    meta = {"channel": ch, "B": B, "H": H, "W": W, "C": C}
    return x, meta


def parse_control_message(message):
    """Parse an OSC-style control message string.

    Accepted forms:
      "/control/<command>"            -> value 0.0
      "/control/<command> <number>"    -> value float
      "/control/<command> <number> <extra...>" -> value float, extras ignored

    Returns (command: str, value: float).
    Raises ValueError on malformed input.
    """
    if not isinstance(message, str):
        raise TypeError("message must be str")
    s = message.strip()
    if not s.startswith("/"):
        raise ValueError("message must start with '/'")
    parts = s.split()
    if len(parts) < 1:
        raise ValueError("empty message")
    path = parts[0]
    segs = [p for p in path.split("/") if p]
    if len(segs) < 2 or segs[0] != "control":
        raise ValueError("path must be /control/<command>")
    command = segs[1]
    value = 0.0
    if len(parts) >= 2:
        try:
            value = float(parts[1])
        except ValueError:
            raise ValueError("value must be a number, got %r" % parts[1])
    return command, value


class PSN_TD_FrameEncode:
    """Encode an IMAGE tensor into the byte payload that would be streamed to
    TouchDesigner over OSC-blob or WebSocket-binary. Returns the payload size
    and a boolean 'frame_sent' (True when encoding succeeded, i.e. the frame
    is ready to transmit)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "channel": ("STRING", {"default": "video_in"}),
                "protocol": (["osc", "websocket"],),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "INT", "STRING")
    RETURN_NAMES = ("frame_sent", "payload_bytes", "channel")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, channel="video_in", protocol="osc"):
        if protocol not in ("osc", "websocket"):
            raise ValueError("protocol must be 'osc' or 'websocket'")
        payload, meta = encode_frame(image, channel=channel)
        # In a real deployment we would hand `payload` to python-osc / websocket.
        # Here we only report that the frame is ready and how big it is.
        return (True, meta["total_bytes"], meta["channel"])


class PSN_TD_Control_Parse:
    """Parse an incoming OSC-style control message from TouchDesigner into a
    command string and a float value. (The actual socket listener is not
    implemented here because network access is not allowed in this sandbox.)"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "message": ("STRING", {"default": "/control/stop"}),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("command", "value")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, message):
        command, value = parse_control_message(message)
        return (command, value)


NODE_CLASS_MAPPINGS = {
    "PSN_TD_FrameEncode": PSN_TD_FrameEncode,
    "PSN_TD_Control_Parse": PSN_TD_Control_Parse,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TD_FrameEncode": "TD Stream Out (Frame Encode)",
    "PSN_TD_Control_Parse": "TD Control In (Parse)",
}
