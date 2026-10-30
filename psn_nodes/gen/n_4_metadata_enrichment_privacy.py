"""Metadata Enrichment & Privacy nodes for ParametricStudio.

This module implements the pure-logic, secure-by-design core of the
"Metadata Enrichment & Privacy" feature.  It does NOT touch the GPU,
does NOT import torch/ComfyUI, and does NOT perform any file, network,
or OS I/O.  Instead it operates on plain Python values (dicts, strings,
bytes) so the logic can be unit-tested in isolation.

The two nodes are:

* ``PSN_Metadata_Editor``   -- merges a metadata dict into an image
  payload and encrypts the values of any keys listed in
  ``encrypt_keys`` before embedding.
* ``PSN_Metadata_Decryptor``-- extracts metadata from an image payload
  and decrypts the values of any keys listed in ``decrypt_keys``.

Encryption is real authenticated encryption (Fernet: AES-128-CBC + HMAC-SHA256) with a key derived from a passphrase by scrypt and a fresh random salt per value.
There is NO default key: supply a passphrase, or leave the field empty and set PSN_STUDIO_PASSPHRASE in the environment (a passphrase typed into a node is saved in the
workflow file). Needs the `cryptography` package; without it encryption fails closed instead of falling back to anything weaker.

The "image" is represented as a plain dict with at least a ``"meta"``
key holding the metadata dict, so the nodes can be exercised without
Pillow or any image library.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/Metadata"

# No default key on purpose. The passphrase comes from the node input or, when that is empty, from this environment variable.
PASSPHRASE_ENV = "PSN_STUDIO_PASSPHRASE"
TOKEN_PREFIX = "psn1."


# ---------------------------------------------------------------------------
# Pure-logic helpers
# ---------------------------------------------------------------------------

def _parse_key_list(raw: Any) -> List[str]:
    """Parse a comma-separated string of key names into a clean list.

    Accepts ``None``, an empty string, or a string like
    ``"prompt, negative_prompt"``.  Whitespace around each key is
    stripped and empty entries are dropped.  Non-string inputs are
    treated as empty.
    """
    if raw is None:
        return []
    if not isinstance(raw, str):
        return []
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def _passphrase(key: Any) -> str:
    key = key if isinstance(key, str) and key else os.environ.get(PASSPHRASE_ENV, "")
    if len(key) < 8:
        raise ValueError(f"A passphrase of at least 8 characters is required (node input or the {PASSPHRASE_ENV} environment variable)")
    return key


def _fernet(passphrase: str, salt: bytes):
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # fail closed: never fall back to a weaker scheme
        raise RuntimeError("encryption needs the 'cryptography' package") from exc
    raw = hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)
    return Fernet(base64.urlsafe_b64encode(raw))


def _encrypt_value(value: Any, key: str) -> str:
    """JSON-encode `value`, encrypt it with a key derived from the passphrase (fresh random salt each time) and return 'psn1.<salt>.<fernet token>'."""
    passphrase = _passphrase(key)
    salt = os.urandom(16)
    token = _fernet(passphrase, salt).encrypt(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return TOKEN_PREFIX + base64.urlsafe_b64encode(salt).decode("ascii") + "." + token.decode("ascii")


def _decrypt_value(token: Any, key: str) -> Any:
    """Reverse of :func:`_encrypt_value`. Raises ValueError for a malformed token, a wrong passphrase or a tampered value (the authentication tag fails)."""
    passphrase = _passphrase(key)
    if not isinstance(token, str) or not token.startswith(TOKEN_PREFIX):
        raise ValueError("Not an encrypted token")
    try:
        salt_b64, fernet_token = token[len(TOKEN_PREFIX):].split(".", 1)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        raw = _fernet(passphrase, salt).decrypt(fernet_token.encode("ascii"))
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001 - wrong key, tampering, bad format: one message, no detail leaked
        raise ValueError("Cannot decrypt: wrong passphrase or damaged value") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Decrypted payload is not valid JSON") from exc


def _deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    """Return a new dict that is ``base`` merged with ``extra``.

    Top-level keys from ``extra`` overwrite those in ``base``.  Nested
    dicts are merged recursively; all other types are replaced.
    """
    result: Dict[str, Any] = {}
    for k, v in base.items():
        result[k] = v
    for k, v in extra.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _coerce_image_payload(image: Any) -> Dict[str, Any]:
    """Normalise an "image" input into a dict with a ``"meta"`` dict.

    Accepts either a dict (used as-is, ensuring ``"meta"`` is a dict) or
    ``None`` (returns a fresh empty payload).  Any other type is treated
    as an opaque object stored under ``"data"`` with empty metadata.
    """
    if image is None:
        return {"data": None, "meta": {}}
    if isinstance(image, dict):
        payload = dict(image)
        meta = payload.get("meta")
        if not isinstance(meta, dict):
            payload["meta"] = {}
        return payload
    # Non-dict image: wrap it so metadata can still be attached.
    return {"data": image, "meta": {}}


# ---------------------------------------------------------------------------
# Node 1: PSN_Metadata_Editor
# ---------------------------------------------------------------------------

class PSN_Metadata_Editor:
    """Merge metadata into an image payload, optionally encrypting the
    values of selected keys before embedding.

    Inputs are plain values (dict, string) -- no GPU, no file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "metadata": ("DICT",),
                "encrypt_keys": ("STRING", {"default": "", "multiline": False}),
                "studio_key": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image_with_meta",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, metadata, encrypt_keys, studio_key):
        payload = _coerce_image_payload(image)
        meta = dict(payload.get("meta") or {})

        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a dict")

        merged = _deep_merge(meta, metadata)

        keys_to_encrypt = _parse_key_list(encrypt_keys)
        for k in keys_to_encrypt:
            if k in merged:
                merged[k] = _encrypt_value(merged[k], studio_key)

        payload["meta"] = merged
        return (payload,)


# ---------------------------------------------------------------------------
# Node 2: PSN_Metadata_Decryptor
# ---------------------------------------------------------------------------

class PSN_Metadata_Decryptor:
    """Extract metadata from an image payload and XOR-decrypt the values of
    selected keys.

    Inputs are plain values (dict, string) -- no GPU, no file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "decrypt_keys": ("STRING", {"default": "", "multiline": False}),
                "studio_key": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("metadata",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, decrypt_keys, studio_key):
        payload = _coerce_image_payload(image)
        meta = dict(payload.get("meta") or {})

        keys_to_decrypt = _parse_key_list(decrypt_keys)
        for k in keys_to_decrypt:
            if k in meta:
                meta[k] = _decrypt_value(meta[k], studio_key)

        return (meta,)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Metadata_Editor": PSN_Metadata_Editor,
    "PSN_Metadata_Decryptor": PSN_Metadata_Decryptor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Metadata_Editor": "Metadata Editor (Encrypt)",
    "PSN_Metadata_Decryptor": "Metadata Decryptor",
}
