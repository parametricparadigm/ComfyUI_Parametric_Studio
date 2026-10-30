"""Automated C2PA Provenance Signing (pure-logic, secure-by-design).

This module implements the *pure-logic* part of a C2PA provenance
signing/verification pipeline.  It does NOT touch the network, the file
system, or any GPU/torch/ComfyUI internals, and it does NOT depend on the
``c2pa`` / ``Pillow`` / ``ffmpeg`` libraries.

What it does do, using only the Python standard library:

* Build a deterministic C2PA-style manifest (creation claims, software
  agent info, provenance chain) from plain values.
* Compute a stable, canonical manifest hash (SHA-256 over canonical JSON).
* Produce a *deterministic* signature over the manifest.  The signature is
  a keyed HMAC-SHA256 (a stand-in for a real asymmetric signature) so the
  whole sign -> verify -> tamper-detect flow is fully testable offline.
* Embed the manifest + signature into a media container as a base64
  payload (PNG ``tEXt`` chunk or MP4 ``udta`` atom) *without* altering the
  pixel data.
* Extract and validate that embedded manifest: recompute the hash, check
  the signature, and detect tampering.

The media is represented as a plain dict:
    {"format": "png"|"mp4", "pixels": <opaque>, "metadata": {...}}
``pixels`` is passed through untouched; only ``metadata`` is extended.

Node classes are named ``PSN_`` + CamelCase and expose the standard
ComfyUI-style ``INPUT_TYPES`` / ``RETURN_TYPES`` / ``run`` surface.
"""

import base64
import hashlib
import hmac
import json
import re

CAT = "ParametricStudio/Provenance"

# A deterministic key used for the stand-in signature.  In a real system
# this would be a private key; here it is a fixed, documented constant so
# the pipeline is reproducible and testable without any key material I/O.
_DEFAULT_KEY = b"psn-c2pa-deterministic-signing-key"

# Maximum allowed length for free-text fields (author / tool / override).
_MAX_TEXT_LEN = 4096

# Allowed media container formats.
_ALLOWED_FORMATS = ("png", "mp4")

# C2PA manifest tag used inside the container metadata.
_MANIFEST_TAG = "c2pa_manifest"


def _canonical_json(obj):
    """Return a canonical, deterministic JSON string for *obj*.

    Keys are sorted and separators are fixed so the same logical manifest
    always serialises to the same byte string (and therefore the same hash).
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _b64encode(data):
    """Base64-encode bytes into an ASCII string (no padding surprises)."""
    return base64.b64encode(data).decode("ascii")


def _b64decode(text):
    """Base64-decode an ASCII string back into bytes."""
    return base64.b64decode(text.encode("ascii"))


def _validate_text(value, name):
    """Validate a free-text field: must be a str, non-empty, bounded length."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % name)
    if len(value) == 0:
        raise ValueError("%s must not be empty" % name)
    if len(value) > _MAX_TEXT_LEN:
        raise ValueError("%s exceeds maximum length of %d" % (name, _MAX_TEXT_LEN))
    return value


def _validate_media(media):
    """Validate the media dict shape and return a normalised copy."""
    if not isinstance(media, dict):
        raise ValueError("media must be a dict")
    fmt = media.get("format")
    if fmt not in _ALLOWED_FORMATS:
        raise ValueError("media format must be one of %s" % (_ALLOWED_FORMATS,))
    if "pixels" not in media:
        raise ValueError("media must contain a 'pixels' field")
    metadata = media.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError("media metadata must be a dict")
    return fmt, media["pixels"], metadata


def build_manifest(author, tool, media_format, manifest_override=None):
    """Build a C2PA-style manifest dict from plain values.

    ``manifest_override`` (optional JSON text) is merged *on top of* the
    generated claims so callers can inject extra provenance fields.  The
    override must be valid JSON object text; anything else raises.
    """
    author = _validate_text(author, "author")
    tool = _validate_text(tool, "tool")
    if media_format not in _ALLOWED_FORMATS:
        raise ValueError("media format must be one of %s" % (_ALLOWED_FORMATS,))

    manifest = {
        "c2pa_version": "1.0",
        "claim_generator": "PSN_C2PA_Signer",
        "creation": {
            "author": author,
            "tool": tool,
            "media_format": media_format,
        },
        "software_agent": {
            "name": "ParametricStudio",
            "role": "generator",
        },
        "provenance_chain": [
            {"step": "created", "by": author, "tool": tool},
        ],
    }

    if manifest_override is not None and manifest_override != "":
        if not isinstance(manifest_override, str):
            raise ValueError("manifest override must be a JSON string")
        try:
            override = json.loads(manifest_override)
        except (ValueError, TypeError) as exc:
            raise ValueError("manifest override is not valid JSON: %s" % exc)
        if not isinstance(override, dict):
            raise ValueError("manifest override must be a JSON object")
        # Shallow merge: override wins on conflicting top-level keys.
        manifest.update(override)

    return manifest


def manifest_hash(manifest):
    """Return the SHA-256 hex digest of the canonical manifest JSON."""
    return hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()


def sign_manifest(manifest, key=_DEFAULT_KEY):
    """Return a deterministic HMAC-SHA256 signature (hex) over the manifest.

    This is a stand-in for an asymmetric signature: it is keyed, so a
    verifier holding the same key can confirm integrity, and it is
    deterministic so tests are stable.
    """
    if not isinstance(key, (bytes, bytearray)):
        raise ValueError("signing key must be bytes")
    payload = _canonical_json(manifest).encode("utf-8")
    return hmac.new(bytes(key), payload, hashlib.sha256).hexdigest()


def embed_manifest(media, manifest, signature):
    """Embed manifest + signature into the media container metadata.

    The pixel data is returned unchanged.  The manifest and signature are
    stored base64-encoded under the ``c2pa_manifest`` metadata tag, which
    mirrors how a real C2PA payload would ride in a PNG ``tEXt`` chunk or
    an MP4 ``udta`` atom.
    """
    fmt, pixels, metadata = _validate_media(media)
    payload = {
        "manifest": manifest,
        "signature": signature,
        "hash": manifest_hash(manifest),
    }
    encoded = _b64encode(_canonical_json(payload).encode("utf-8"))
    new_metadata = dict(metadata)
    new_metadata[_MANIFEST_TAG] = encoded
    return {"format": fmt, "pixels": pixels, "metadata": new_metadata}


def extract_manifest(media):
    """Extract the embedded manifest payload from media metadata.

    Returns a dict with keys ``manifest``, ``signature``, ``hash``.
    Raises ValueError if no manifest is present or it is malformed.
    """
    _fmt, _pixels, metadata = _validate_media(media)
    encoded = metadata.get(_MANIFEST_TAG)
    if encoded is None:
        raise ValueError("no C2PA manifest embedded in media")
    if not isinstance(encoded, str):
        raise ValueError("C2PA manifest payload is malformed")
    try:
        raw = _b64decode(encoded)
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise ValueError("C2PA manifest payload is not valid: %s" % exc)
    if not isinstance(payload, dict):
        raise ValueError("C2PA manifest payload must be an object")
    for key in ("manifest", "signature", "hash"):
        if key not in payload:
            raise ValueError("C2PA manifest payload missing '%s'" % key)
    return payload


def verify_manifest(media):
    """Verify the embedded manifest: hash integrity + signature validity.

    Returns a tuple ``(valid, details_json, error)`` where:
      * ``valid`` is a bool,
      * ``details_json`` is a JSON string describing the manifest (or "" on
        failure),
      * ``error`` is a human-readable reason (or "" on success).
    """
    try:
        payload = extract_manifest(media)
    except ValueError as exc:
        return (False, "", str(exc))

    manifest = payload["manifest"]
    signature = payload["signature"]
    stored_hash = payload["hash"]

    # 1) Integrity: recompute the manifest hash and compare.
    recomputed_hash = manifest_hash(manifest)
    if recomputed_hash != stored_hash:
        return (False, "", "manifest hash mismatch (content tampered)")

    # 2) Signature: recompute the keyed signature and compare.
    expected_signature = sign_manifest(manifest)
    if not hmac.compare_digest(expected_signature, signature):
        return (False, "", "signature invalid (tampered or wrong key)")

    details = {
        "valid": True,
        "hash": recomputed_hash,
        "author": manifest.get("creation", {}).get("author", ""),
        "tool": manifest.get("creation", {}).get("tool", ""),
        "media_format": manifest.get("creation", {}).get("media_format", ""),
        "claim_generator": manifest.get("claim_generator", ""),
    }
    return (True, _canonical_json(details), "")


# ---------------------------------------------------------------------------
# ComfyUI-style node wrappers
# ---------------------------------------------------------------------------

class PSN_C2PA_Signer:
    """Embed a verifiable C2PA provenance manifest into media.

    Pure-logic: builds the manifest, signs it deterministically, and embeds
    it into the container metadata without touching pixel data.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "media": ("MEDIA",),
                "author": ("STRING", {"default": "Anonymous", "multiline": False}),
                "tool": ("STRING", {"default": "ParametricStudio", "multiline": False}),
                "sign_with_key": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "manifest_override": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("MEDIA", "STRING")
    RETURN_NAMES = ("signed_media", "manifest_hash")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, media, author, tool, sign_with_key, manifest_override=""):
        manifest = build_manifest(author, tool, media.get("format"), manifest_override)
        if sign_with_key:
            signature = sign_manifest(manifest)
        else:
            # Unsigned: store an empty signature; verification will fail the
            # signature check but the hash is still recorded.
            signature = ""
        signed = embed_manifest(media, manifest, signature)
        return (signed, manifest_hash(manifest))


class PSN_C2PA_Verifier:
    """Extract and validate an embedded C2PA manifest.

    Pure-logic: recomputes the manifest hash and the keyed signature and
    reports validity, details, and any error.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "media": ("MEDIA",),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("valid", "details", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, media):
        valid, details, error = verify_manifest(media)
        return (valid, details, error)


NODE_CLASS_MAPPINGS = {
    "PSN_C2PA_Signer": PSN_C2PA_Signer,
    "PSN_C2PA_Verifier": PSN_C2PA_Verifier,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_C2PA_Signer": "C2PA Provenance Signer",
    "PSN_C2PA_Verifier": "C2PA Provenance Verifier",
}
