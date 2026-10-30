"""Verify the integrity of user-uploaded media assets.

Compares a hash of the incoming tensor payload (IMAGE / MASK / LATENT) against
an attested value supplied by the uploader.  This is a pure-torch, CPU-only
implementation: no files are opened, no network is used, and inputs are never
mutated in place.

The hash is a deterministic 64-bit FNV-1a over the flattened float32 bytes of
the tensor, which is stable across runs and platforms for a given tensor.
"""

import hashlib
import torch

CAT = "ParametricStudio/Integrity"


def _fnv1a64(data: bytes) -> str:
    """Return a 16-char hex FNV-1a 64-bit digest of *data*."""
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return format(h, "016x")


def _tensor_bytes(t: torch.Tensor) -> bytes:
    """Flatten *t* to contiguous float32 and return its raw bytes."""
    return t.detach().to(torch.float32).contiguous().numpy().tobytes()


def _extract_tensor(payload):
    """Pull the primary tensor out of a ComfyUI payload.

    Returns (tensor, kind) where kind is one of 'IMAGE', 'MASK', 'LATENT'.
    Raises ValueError for unsupported / malformed payloads.
    """
    if isinstance(payload, dict):
        if "samples" in payload:
            t = payload["samples"]
            if not isinstance(t, torch.Tensor):
                raise ValueError("LATENT 'samples' must be a torch.Tensor")
            return t, "LATENT"
        raise ValueError("Unknown dict payload; expected LATENT with 'samples'")
    if isinstance(payload, torch.Tensor):
        # Heuristic: 4-D [B,H,W,C] -> IMAGE, 3-D [B,H,W] -> MASK
        if payload.dim() == 4:
            return payload, "IMAGE"
        if payload.dim() == 3:
            return payload, "MASK"
        raise ValueError(
            f"Tensor must be 3-D (MASK) or 4-D (IMAGE), got {payload.dim()}-D"
        )
    raise ValueError(f"Unsupported payload type: {type(payload).__name__}")


def compute_hash(payload) -> str:
    """Compute the attestation hash for a ComfyUI media payload."""
    t, _ = _extract_tensor(payload)
    return _fnv1a64(_tensor_bytes(t))


def verify(payload, attested_hash: str) -> bool:
    """Return True if *payload* hashes to *attested_hash* (case-insensitive)."""
    if not isinstance(attested_hash, str) or not attested_hash.strip():
        raise ValueError("attested_hash must be a non-empty string")
    return compute_hash(payload).lower() == attested_hash.strip().lower()


class PSN_VerifyMediaIntegrity:
    """Verify that an uploaded media tensor matches its attested hash."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "payload": ("IMAGE",),
                "attested_hash": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("integrity_ok", "computed_hash")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, payload, attested_hash):
        t, kind = _extract_tensor(payload)
        h = compute_hash(payload)
        ok = verify(payload, attested_hash)
        return (ok, h)


class PSN_ComputeMediaHash:
    """Compute the attestation hash for a media tensor (helper node)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "payload": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("hash",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, payload):
        return (compute_hash(payload),)


NODE_CLASS_MAPPINGS = {
    "PSN_VerifyMediaIntegrity": PSN_VerifyMediaIntegrity,
    "PSN_ComputeMediaHash": PSN_ComputeMediaHash,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VerifyMediaIntegrity": "Verify Media Integrity",
    "PSN_ComputeMediaHash": "Compute Media Hash",
}
