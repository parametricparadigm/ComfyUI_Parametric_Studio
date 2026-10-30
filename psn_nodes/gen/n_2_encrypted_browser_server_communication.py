"""ParametricStudio CryptIO: RSA-OAEP encrypt/decrypt nodes for browser-server communication.

Implements the core of the "Encrypted Browser-Server Communication" idea:
- PSN_CryptIO_Encrypt: RSA-OAEP encrypt a string, output Base64.
- PSN_CryptIO_Decrypt: Base64 decode + RSA-OAEP decrypt a string.

Uses the `cryptography` library (RSA-OAEP with SHA-256). Keys are provided as
PEM strings. For payloads larger than the RSA block size, the data is split
into chunks and each chunk is encrypted separately (concatenated Base64 with
chunk length prefix is NOT used; instead each chunk is Base64-encoded and
joined with a newline, and the decryptor splits on newlines). This keeps the
implementation simple and dependency-light while supporting arbitrary length
strings.
"""

import base64

try: from ._lazy import LazyModule
except ImportError: from _lazy import LazyModule     # imported on its own by the module's plain test

hashes = LazyModule("cryptography.hazmat.primitives.hashes")
serialization = LazyModule("cryptography.hazmat.primitives.serialization")
padding = LazyModule("cryptography.hazmat.primitives.asymmetric.padding")
rsa = LazyModule("cryptography.hazmat.primitives.asymmetric.rsa")

CAT = "ParametricStudio/CryptIO"

# RSA-2048 with OAEP-SHA256: max plaintext per chunk = 256 - 2*32 - 2 = 190 bytes.
_RSA_BITS = 2048
def _oaep_pad():
    return padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )
_CHUNK_SIZE = 190


def _load_public_key(pem: str):
    if not isinstance(pem, str) or not pem.strip():
        raise ValueError("public_key must be a non-empty PEM string")
    return serialization.load_pem_public_key(pem.encode("utf-8"))


def _load_private_key(pem: str):
    if not isinstance(pem, str) or not pem.strip():
        raise ValueError("private_key must be a non-empty PEM string")
    return serialization.load_pem_private_key(pem.encode("utf-8"), password=None)


def _b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64_decode(s: str) -> bytes:
    if not isinstance(s, str) or not s.strip():
        raise ValueError("encrypted_data must be a non-empty Base64 string")
    try:
        return base64.b64decode(s.encode("ascii"), validate=True)
    except Exception as e:
        raise ValueError(f"invalid Base64: {e}")


def _rsa_encrypt_chunks(public_key, plaintext: bytes) -> str:
    """Encrypt plaintext in chunks; return newline-joined Base64 chunks."""
    chunks = []
    for i in range(0, len(plaintext), _CHUNK_SIZE):
        block = plaintext[i : i + _CHUNK_SIZE]
        if not block:
            continue
        ct = public_key.encrypt(block, _oaep_pad())
        chunks.append(_b64_encode(ct))
    if not chunks:
        # Empty input: encrypt a single empty-ish marker? RSA needs >=1 byte.
        # We handle empty string by encrypting a single NUL byte and letting
        # the decryptor strip it. Simpler: raise for empty input.
        raise ValueError("data must be a non-empty string")
    return "\n".join(chunks)


def _rsa_decrypt_chunks(private_key, b64_blob: str) -> bytes:
    """Decrypt newline-joined Base64 chunks; return concatenated plaintext."""
    parts = [p for p in b64_blob.split("\n") if p.strip()]
    if not parts:
        raise ValueError("encrypted_data contains no chunks")
    out = bytearray()
    for p in parts:
        ct = _b64_decode(p)
        pt = private_key.decrypt(ct, _oaep_pad())
        out.extend(pt)
    return bytes(out)


class PSN_CryptIO_Encrypt:
    """Encrypt a string with RSA-OAEP (public key, PEM) and output Base64."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": ("STRING", {"default": "", "multiline": True}),
                "public_key": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("encrypted_data",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, data: str, public_key: str) -> tuple:
        if not isinstance(data, str):
            raise ValueError("data must be a string")
        if data == "":
            raise ValueError("data must be non-empty")
        pub = _load_public_key(public_key)
        blob = _rsa_encrypt_chunks(pub, data.encode("utf-8"))
        return (blob,)


class PSN_CryptIO_Decrypt:
    """Decrypt Base64 RSA-OAEP data with a private key (PEM) back to a string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "encrypted_data": ("STRING", {"default": "", "multiline": True}),
                "private_key": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("data",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, encrypted_data: str, private_key: str) -> tuple:
        if not isinstance(encrypted_data, str):
            raise ValueError("encrypted_data must be a string")
        priv = _load_private_key(private_key)
        pt = _rsa_decrypt_chunks(priv, encrypted_data)
        return (pt.decode("utf-8"),)


NODE_CLASS_MAPPINGS = {
    "PSN_CryptIO_Encrypt": PSN_CryptIO_Encrypt,
    "PSN_CryptIO_Decrypt": PSN_CryptIO_Decrypt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CryptIO_Encrypt": "CryptIO Encrypt (RSA-OAEP)",
    "PSN_CryptIO_Decrypt": "CryptIO Decrypt (RSA-OAEP)",
}
