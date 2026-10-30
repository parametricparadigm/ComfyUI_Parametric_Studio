"""Integrity verification for model assets.

This module provides pure-logic hashing and verification helpers for model
files (e.g. .safetensors, .ckpt, .pt) and LoRA weights.

Because the sandbox forbids any file or OS access, the nodes do NOT open
files themselves. Instead they operate on a caller-supplied ``data`` string
that represents the raw bytes of the asset (e.g. base64-encoded content, or
a literal byte-string). The caller is responsible for reading the file and
passing its content in.

The module exposes:
  * ``PSN_File_Hasher``   -- compute an MD5 or SHA-256 hex digest of the
                             supplied data, and report its byte length.
  * ``PSN_Hash_Verifier`` -- compare a supplied hash against the computed
                             digest and report match / mismatch.

Both nodes return an error string in the hash output when the input is
invalid, so downstream nodes can branch on it without crashing.
"""

import base64
import binascii
import hashlib

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALGORITHMS = ("MD5", "SHA-256")
_CAT = "ParametricStudio/Integrity"

# Map friendly algorithm names to hashlib factory functions.
_ALGO_MAP = {
    "MD5": hashlib.md5,
    "SHA-256": hashlib.sha256,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _decode_data(data):
    """Decode the *data* string into raw bytes.

    Accepts either:
      * a plain ASCII/UTF-8 string (treated as literal bytes), or
      * a base64-encoded string (detected by trying to decode).

    Returns a tuple ``(bytes, error_string)``.  On success *error_string*
    is ``""``; on failure the bytes are ``b""`` and *error_string* describes
    the problem.
    """
    if not isinstance(data, str):
        return b"", "Input 'data' must be a string (base64 or literal bytes)."
    if data == "":
        return b"", "Input 'data' is empty; nothing to hash."

    # Try base64 first (common for binary assets passed as text).
    try:
        raw = base64.b64decode(data, validate=True)
        return raw, ""
    except (binascii.Error, ValueError):
        pass

    # Fall back to treating the string as literal UTF-8 bytes.
    try:
        raw = data.encode("utf-8")
        return raw, ""
    except UnicodeEncodeError as exc:
        return b"", "Could not decode 'data' as base64 or UTF-8: %s" % exc


def _compute_hash(data, algorithm):
    """Compute the hex digest of *data* using *algorithm*.

    Returns a tuple ``(hex_digest, error_string)``.
    """
    if algorithm not in _ALGO_MAP:
        return "", "Unknown algorithm '%s'. Choose from %s." % (
            algorithm, ", ".join(_ALGORITHMS))

    raw, err = _decode_data(data)
    if err:
        return "", err

    hasher = _ALGO_MAP[algorithm]()
    hasher.update(raw)
    return hasher.hexdigest(), ""


# ---------------------------------------------------------------------------
# Node: PSN_File_Hasher
# ---------------------------------------------------------------------------

class PSN_File_Hasher:
    """Compute an MD5 or SHA-256 hash of model-asset data.

    Inputs
    ------
    data : STRING
        The raw content of the file, either as a base64-encoded string or
        as a literal UTF-8 string.  (In a full ComfyUI deployment a
        companion loader node would read the file and pass its bytes here.)
    algorithm : COMBO
        ``"MD5"`` or ``"SHA-256"``.

    Outputs
    -------
    hash_hex : STRING
        Lower-case hex digest, or an error message if the input was invalid.
    file_size : INT
        Number of bytes in the decoded data (0 on error).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": ("STRING", {"default": "", "multiline": True}),
                "algorithm": (list(_ALGORITHMS),),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("hash_hex", "file_size")
    FUNCTION = "run"
    CATEGORY = _CAT

    def run(self, data, algorithm):
        hex_digest, err = _compute_hash(data, algorithm)
        if err:
            return (err, 0)
        raw, _ = _decode_data(data)
        return (hex_digest, len(raw))


# ---------------------------------------------------------------------------
# Node: PSN_Hash_Verifier
# ---------------------------------------------------------------------------

class PSN_Hash_Verifier:
    """Verify that model-asset data matches an expected hash.

    Inputs
    ------
    data : STRING
        The raw content of the file (base64 or literal UTF-8), same
        convention as :class:`PSN_File_Hasher`.
    expected_hash : STRING
        The hex digest the data is expected to produce.  Case-insensitive;
        surrounding whitespace is stripped.
    algorithm : COMBO
        ``"MD5"`` or ``"SHA-256"``.

    Outputs
    -------
    match : BOOLEAN
        ``True`` when the computed digest equals *expected_hash*.
    actual_hash : STRING
        The computed hex digest, or an error message on bad input.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": ("STRING", {"default": "", "multiline": True}),
                "expected_hash": ("STRING", {"default": ""}),
                "algorithm": (list(_ALGORITHMS),),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("match", "actual_hash")
    FUNCTION = "run"
    CATEGORY = _CAT

    def run(self, data, expected_hash, algorithm):
        hex_digest, err = _compute_hash(data, algorithm)
        if err:
            return (False, err)

        expected = expected_hash.strip().lower()
        actual = hex_digest.lower()
        return (actual == expected, hex_digest)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_File_Hasher": PSN_File_Hasher,
    "PSN_Hash_Verifier": PSN_Hash_Verifier,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_File_Hasher": "PSN File Hasher",
    "PSN_Hash_Verifier": "PSN Hash Verifier",
}
