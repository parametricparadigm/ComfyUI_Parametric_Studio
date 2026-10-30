"""PSN steganography nodes (pure-logic, secure-by-design).

This module implements the *logic* of the Steganography for Watermarking spec
without touching GPU/torch/ComfyUI internals or any file/network I/O.

Because the spec's real payload is an IMAGE tensor (torch) and the listed
dependencies (``stegano``, ``numpy``) are not in the allowed standard-library
set, the nodes operate on *plain values* only:

  * ``image`` is accepted as a STRING that encodes the pixel grid as JSON text
    (a list of rows, each row a list of integer channel values in 0..255).
    This is a stand-in for the real IMAGE tensor so the embedding/extraction
    algorithm can be exercised and tested with the standard library alone.
  * ``secret_data`` is a plain STRING (e.g. JSON metadata).
  * ``embedding_key`` is a plain STRING produced by the encoder.

The encoder embeds the secret into the least-significant bits of the pixel
values (LSB method) and returns the watermarked image (same JSON shape) plus a
key that records the payload length and a checksum. The decoder reverses the
process and reports an integrity check.

Only the pure-logic, secure-by-design part is implemented: message/payload
formatting, config validation, allow-list checks and parsing. No sockets, no
files, no network, no subprocess, no eval/exec.
"""

import json
import hashlib

CAT = "ParametricStudio/Steganography"

# Allowed embedding methods (allow-list).
_METHODS = ("LSB", "DCT", "Audio")

# Only LSB is implemented in this pure-logic build; the others are accepted by
# the allow-list but reported as unsupported so callers get a clear reason.
_SUPPORTED = ("LSB",)


def _psn_parse_image(image):
    """Parse the JSON-encoded pixel grid into a list of rows of ints.

    Returns (rows, error). ``rows`` is None when ``error`` is not None.
    """
    if not isinstance(image, str):
        return None, "image must be a JSON string"
    try:
        data = json.loads(image)
    except (ValueError, TypeError):
        return None, "image is not valid JSON"
    if not isinstance(data, list) or not data:
        return None, "image must be a non-empty JSON list of rows"
    rows = []
    for row in data:
        if not isinstance(row, list):
            return None, "each row must be a JSON list"
        out_row = []
        for v in row:
            if isinstance(v, bool) or not isinstance(v, int):
                return None, "pixel values must be integers"
            if v < 0 or v > 255:
                return None, "pixel values must be in 0..255"
            out_row.append(v)
        rows.append(out_row)
    return rows, None


def _psn_image_to_json(rows):
    return json.dumps(rows)


def _psn_bits_from_bytes(payload_bytes):
    """Convert bytes to a list of 0/1 ints (MSB first)."""
    bits = []
    for b in payload_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits


def _psn_bytes_from_bits(bits):
    """Convert a list of 0/1 ints (MSB first) back to bytes."""
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        out.append(byte)
    return bytes(out)


def _psn_checksum(payload_bytes):
    return hashlib.sha256(payload_bytes).hexdigest()[:16]


def _psn_encode(rows, secret_data, strength):
    """Embed ``secret_data`` into ``rows`` using LSB.

    Returns (new_rows, key, error).
    """
    if not isinstance(secret_data, str):
        return None, None, "secret_data must be a string"
    if not isinstance(strength, (int, float)) or isinstance(strength, bool):
        return None, None, "strength must be a number"
    if strength < 0.0 or strength > 1.0:
        return None, None, "strength must be in 0.0..1.0"

    payload = secret_data.encode("utf-8")
    checksum = _psn_checksum(payload)
    # Header: 4 bytes big-endian payload length, then 16 bytes checksum (hex ascii), then payload.
    header = len(payload).to_bytes(4, "big") + checksum.encode("ascii")
    full = header + payload
    bits = _psn_bits_from_bytes(full)

    # Flatten pixel positions (row-major).
    total_pixels = sum(len(r) for r in rows)
    if total_pixels < len(bits):
        return None, None, "image too small to embed payload"

    # strength controls how many of the LSBs we actually flip per pixel; at
    # strength 1.0 we use every pixel's LSB. We always need exactly len(bits)
    # positions, so we take the first len(bits) pixels.
    new_rows = [list(r) for r in rows]
    idx = 0
    for r in range(len(new_rows)):
        for c in range(len(new_rows[r])):
            if idx >= len(bits):
                break
            bit = bits[idx]
            cur = new_rows[r][c]
            # Set the LSB to the desired bit.
            new_rows[r][c] = (cur & 0xFE) | bit
            idx += 1
        if idx >= len(bits):
            break

    key = json.dumps({"method": "LSB", "length": len(payload), "checksum": checksum,
                      "strength": strength})
    return new_rows, key, None


def _psn_decode(rows, embedding_key, method):
    """Extract secret from ``rows`` using the key.

    Returns (secret, ok, reason).
    """
    if not isinstance(embedding_key, str):
        return "", False, "embedding_key must be a string"
    try:
        key = json.loads(embedding_key)
    except (ValueError, TypeError):
        return "", False, "embedding_key is not valid JSON"
    if not isinstance(key, dict):
        return "", False, "embedding_key must be a JSON object"
    k_method = key.get("method")
    if k_method != "LSB":
        return "", False, "unsupported key method: %r" % (k_method,)
    if method != "LSB":
        return "", False, "method mismatch with key"
    length = key.get("length")
    checksum = key.get("checksum")
    if not isinstance(length, int) or length < 0:
        return "", False, "invalid length in key"
    if not isinstance(checksum, str):
        return "", False, "invalid checksum in key"

    # Need header (4 + 16 bytes) + payload bits.
    total_bytes = 4 + 16 + length
    bits_needed = total_bytes * 8
    total_pixels = sum(len(r) for r in rows)
    if total_pixels < bits_needed:
        return "", False, "image too small for recorded payload"

    bits = []
    idx = 0
    for r in range(len(rows)):
        for c in range(len(rows[r])):
            if idx >= bits_needed:
                break
            bits.append(rows[r][c] & 1)
            idx += 1
        if idx >= bits_needed:
            break

    raw = _psn_bytes_from_bits(bits)
    rec_len = int.from_bytes(raw[0:4], "big")
    rec_sum = raw[4:20].decode("ascii", "replace")
    payload = raw[20:20 + rec_len]

    if rec_len != length:
        return "", False, "length mismatch"
    if _psn_checksum(payload) != rec_sum or rec_sum != checksum:
        return "", False, "checksum mismatch"
    try:
        secret = payload.decode("utf-8")
    except UnicodeDecodeError:
        return "", False, "payload is not valid UTF-8"
    return secret, True, "ok"


class PSN_Steganography_Encoder:
    """Embed invisible metadata/watermark into an image (LSB) and return a key."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("STRING", {"default": "[]", "multiline": True}),
                "secret_data": ("STRING", {"default": "", "multiline": True}),
                "method": (list(_METHODS),),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("watermarked_image", "embedding_key")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, secret_data, method, strength):
        rows, err = _psn_parse_image(image)
        if err:
            return ("", "error: " + err)
        if method not in _SUPPORTED:
            return ("", "error: method %s not supported in pure-logic build" % method)
        new_rows, key, err = _psn_encode(rows, secret_data, strength)
        if err:
            return ("", "error: " + err)
        return (_psn_image_to_json(new_rows), key)


class PSN_Steganography_Decoder:
    """Extract embedded secret from a watermarked image and check integrity."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("STRING", {"default": "[]", "multiline": True}),
                "embedding_key": ("STRING", {"default": "", "multiline": True}),
                "method": (list(_METHODS),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("extracted_data", "integrity_check")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, embedding_key, method):
        rows, err = _psn_parse_image(image)
        if err:
            return ("", False)
        secret, ok, _reason = _psn_decode(rows, embedding_key, method)
        return (secret, ok)


NODE_CLASS_MAPPINGS = {
    "PSN_Steganography_Encoder": PSN_Steganography_Encoder,
    "PSN_Steganography_Decoder": PSN_Steganography_Decoder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Steganography_Encoder": "PSN Steganography Encoder",
    "PSN_Steganography_Decoder": "PSN Steganography Decoder",
}
