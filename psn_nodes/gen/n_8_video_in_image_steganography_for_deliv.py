"""PSN Video-in-PNG Steganography (pure-logic, secure-by-design).

This module implements the *byte-level* steganography logic for embedding a
short video preview inside a PNG image by appending the video bytes after the
PNG IEND chunk. It is intentionally pure Python (standard library only) and
does NOT touch the filesystem, network, GPU, or ComfyUI/torch internals.

Inputs and outputs are plain values:
  * PNG / video payloads are passed as ``bytes`` (or ``str`` for the offset).
  * The combined payload is returned as ``bytes``.
  * The extraction offset is returned as a ``str`` (decimal integer) so it can
    be wired into a ComfyUI ``INT`` input.

The real ComfyUI node would wrap these helpers to read/write actual files and
to hand the combined bytes to an image save node. Here we only do the safe,
deterministic byte manipulation and validation.

Security notes:
  * We validate that the PNG actually ends with an IEND chunk before appending.
  * We never execute, eval, or open anything.
  * We cap the maximum allowed payload size to avoid accidental OOM.
"""

from __future__ import annotations

import struct
from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# PNG signature (8 bytes)
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# IEND chunk: length(4) + "IEND" + CRC(4)
_IEND_TYPE = b"IEND"
_IEND_CHUNK = struct.pack(">I", 0) + _IEND_TYPE + struct.pack(">I", 0)

# Hard cap on combined payload size (bytes) to prevent OOM in the real node.
MAX_PAYLOAD_BYTES = 256 * 1024 * 1024  # 256 MiB

# Category for ComfyUI node registration.
CAT = "ParametricStudio/Video"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _to_bytes(value: Any) -> bytes:
    """Coerce a plain value into bytes without any I/O."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, str):
        # Allow base64-ish or plain text payloads; we just encode as UTF-8.
        return value.encode("utf-8")
    raise TypeError("Expected bytes/bytearray/str, got %r" % type(value).__name__)


def _validate_png(png_bytes: bytes) -> None:
    """Ensure the payload looks like a PNG and ends with an IEND chunk."""
    if not isinstance(png_bytes, (bytes, bytearray)):
        raise TypeError("PNG payload must be bytes/bytearray")
    png_bytes = bytes(png_bytes)
    if len(png_bytes) < len(_PNG_SIGNATURE) + len(_IEND_CHUNK):
        raise ValueError("PNG payload too small to contain signature and IEND")
    if not png_bytes.startswith(_PNG_SIGNATURE):
        raise ValueError("PNG payload does not start with PNG signature")
    if not png_bytes.endswith(_IEND_CHUNK):
        raise ValueError("PNG payload does not end with IEND chunk")


def _validate_video(video_bytes: bytes) -> None:
    """Basic sanity check on the video payload (non-empty, size cap)."""
    if not isinstance(video_bytes, (bytes, bytearray)):
        raise TypeError("Video payload must be bytes/bytearray")
    video_bytes = bytes(video_bytes)
    if len(video_bytes) == 0:
        raise ValueError("Video payload is empty")
    if len(video_bytes) > MAX_PAYLOAD_BYTES:
        raise ValueError("Video payload exceeds MAX_PAYLOAD_BYTES")


def _validate_offset(offset: Any) -> int:
    """Parse and validate the extraction offset (int or decimal string)."""
    if isinstance(offset, bool):
        raise TypeError("Offset must be an int or decimal string, not bool")
    if isinstance(offset, int):
        value = offset
    elif isinstance(offset, str):
        try:
            value = int(offset.strip())
        except (ValueError, AttributeError):
            raise ValueError("Offset string is not a valid integer: %r" % offset)
    else:
        raise TypeError("Offset must be an int or decimal string")
    if value < 0:
        raise ValueError("Offset must be non-negative")
    return value


def encode_video_in_png(png_bytes: bytes, video_bytes: bytes) -> Tuple[bytes, int]:
    """Append video bytes after the PNG IEND chunk.

    Returns:
        (combined_bytes, offset) where offset is the byte index at which the
        video payload begins in the combined stream.
    """
    _validate_png(png_bytes)
    _validate_video(video_bytes)
    png_bytes = bytes(png_bytes)
    video_bytes = bytes(video_bytes)

    combined = png_bytes + video_bytes
    if len(combined) > MAX_PAYLOAD_BYTES:
        raise ValueError("Combined payload exceeds MAX_PAYLOAD_BYTES")

    offset = len(png_bytes)
    return combined, offset


def decode_video_from_png(combined_bytes: bytes, offset: Any) -> bytes:
    """Extract the video payload from a combined PNG+video stream.

    The offset is the byte index where the video begins (i.e. right after the
    PNG IEND chunk). We validate that the bytes at ``offset - len(IEND)``
    actually form an IEND chunk to guard against mis-wired offsets.
    """
    if not isinstance(combined_bytes, (bytes, bytearray)):
        raise TypeError("Combined payload must be bytes/bytearray")
    combined_bytes = bytes(combined_bytes)
    offset = _validate_offset(offset)

    if offset > len(combined_bytes):
        raise ValueError("Offset exceeds combined payload length")
    if offset == len(combined_bytes):
        raise ValueError("Offset points to end of payload; no video bytes present")

    # Verify the IEND chunk immediately precedes the offset.
    iend_start = offset - len(_IEND_CHUNK)
    if iend_start < 0:
        raise ValueError("Offset is too small to contain a preceding IEND chunk")
    if combined_bytes[iend_start:offset] != _IEND_CHUNK:
        raise ValueError("Bytes preceding offset do not form a valid IEND chunk")

    video_bytes = combined_bytes[offset:]
    if len(video_bytes) == 0:
        raise ValueError("No video bytes found after IEND chunk")
    return video_bytes


# ---------------------------------------------------------------------------
# ComfyUI-style node classes
# ---------------------------------------------------------------------------

class PSN_Video_In_PNG_Encode:
    """Embed a video clip into a PNG by appending its bytes after IEND."""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "png_bytes": ("BYTES", {"forceInput": True}),
                "video_bytes": ("BYTES", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("BYTES", "STRING")
    RETURN_NAMES = ("combined_png", "extraction_offset")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, png_bytes: bytes, video_bytes: bytes) -> Tuple[bytes, str]:
        combined, offset = encode_video_in_png(png_bytes, video_bytes)
        return (combined, str(offset))


class PSN_Video_In_PNG_Decode:
    """Extract the embedded video bytes from a combined PNG+video stream."""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "combined_png": ("BYTES", {"forceInput": True}),
                "offset": ("INT", {"default": 0, "min": 0, "max": 10**12, "step": 1}),
            }
        }

    RETURN_TYPES = ("BYTES",)
    RETURN_NAMES = ("video_bytes",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, combined_png: bytes, offset: int) -> Tuple[bytes,]:
        video_bytes = decode_video_from_png(combined_png, offset)
        return (video_bytes,)


# ---------------------------------------------------------------------------
# ComfyUI registration mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Video_In_PNG_Encode": PSN_Video_In_PNG_Encode,
    "PSN_Video_In_PNG_Decode": PSN_Video_In_PNG_Decode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_In_PNG_Encode": "PSN Video In PNG Encode",
    "PSN_Video_In_PNG_Decode": "PSN Video In PNG Decode",
}
