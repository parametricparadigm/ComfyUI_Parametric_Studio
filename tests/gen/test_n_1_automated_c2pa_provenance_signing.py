"""Tests for the pure-logic C2PA provenance signing/verification nodes."""

import json

import pytest

from psn_nodes.gen.n_1_automated_c2pa_provenance_signing import (
    PSN_C2PA_Signer,
    PSN_C2PA_Verifier,
    build_manifest,
    embed_manifest,
    extract_manifest,
    manifest_hash,
    sign_manifest,
    verify_manifest,
)


def _media(fmt="png", pixels="PIXELDATA", metadata=None):
    return {"format": fmt, "pixels": pixels, "metadata": metadata or {}}


def test_sign_then_verify_roundtrip_is_valid():
    signer = PSN_C2PA_Signer()
    verifier = PSN_C2PA_Verifier()
    media = _media("png", pixels="abc123")
    signed, mhash = signer.run(media, "Alice", "PSN", True)
    # Pixel data must be untouched.
    assert signed["pixels"] == "abc123"
    # Manifest must be embedded.
    assert "c2pa_manifest" in signed["metadata"]
    # Hash is a 64-char hex string.
    assert len(mhash) == 64
    valid, details, error = verifier.run(signed)
    assert valid is True
    assert error == ""
    parsed = json.loads(details)
    assert parsed["author"] == "Alice"
    assert parsed["tool"] == "PSN"
    assert parsed["hash"] == mhash


def test_tampering_pixel_data_does_not_break_manifest_but_hash_still_matches():
    # Tampering the *pixels* does not change the manifest (manifest is
    # metadata-only), so the manifest itself still verifies.  This documents
    # that the pure-logic layer protects the manifest, not the pixels.
    signer = PSN_C2PA_Signer()
    verifier = PSN_C2PA_Verifier()
    signed, _ = signer.run(_media("png", "orig"), "Bob", "T", True)
    tampered = dict(signed)
    tampered["pixels"] = "CHANGED"
    valid, _details, error = verifier.run(tampered)
    # Manifest is intact, so it still verifies.
    assert valid is True
    assert error == ""


def test_tampering_manifest_payload_fails_verification():
    signer = PSN_C2PA_Signer()
    verifier = PSN_C2PA_Verifier()
    signed, _ = signer.run(_media("png", "orig"), "Bob", "T", True)
    # Decode, alter the author, re-encode -> hash + signature now mismatch.
    import base64
    raw = base64.b64decode(signed["metadata"]["c2pa_manifest"])
    payload = json.loads(raw.decode("utf-8"))
    payload["manifest"]["creation"]["author"] = "Mallory"
    signed["metadata"]["c2pa_manifest"] = base64.b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    valid, _details, error = verifier.run(signed)
    assert valid is False
    assert error != ""


def test_unsigned_manifest_fails_signature_check():
    signer = PSN_C2PA_Signer()
    verifier = PSN_C2PA_Verifier()
    signed, _ = signer.run(_media("mp4", "vid"), "Carol", "T", False)
    valid, _details, error = verifier.run(signed)
    assert valid is False
    assert "signature" in error.lower()


def test_manifest_override_merges_and_is_reflected_in_details():
    signer = PSN_C2PA_Signer()
    verifier = PSN_C2PA_Verifier()
    override = json.dumps({"extra_field": "value42"})
    signed, _ = signer.run(_media("png", "x"), "Dave", "T", True, override)
    valid, details, error = verifier.run(signed)
    assert valid is True
    assert error == ""
    # The override is part of the manifest, so its hash differs from a
    # manifest built without it.
    base_manifest = build_manifest("Dave", "T", "png")
    override_manifest = build_manifest("Dave", "T", "png", override)
    assert manifest_hash(base_manifest) != manifest_hash(override_manifest)
    assert override_manifest["extra_field"] == "value42"


def test_invalid_manifest_override_json_raises():
    with pytest.raises(ValueError):
        build_manifest("Eve", "T", "png", "{not valid json")


def test_invalid_media_format_raises():
    with pytest.raises(ValueError):
        build_manifest("Eve", "T", "gif")


def test_empty_author_raises():
    with pytest.raises(ValueError):
        build_manifest("", "T", "png")


def test_non_string_author_raises():
    with pytest.raises(ValueError):
        build_manifest(123, "T", "png")


def test_missing_manifest_in_media_reports_error_not_crash():
    verifier = PSN_C2PA_Verifier()
    valid, details, error = verifier.run(_media("png", "x"))
    assert valid is False
    assert details == ""
    assert "no C2PA manifest" in error


def test_malformed_manifest_payload_reports_error():
    verifier = PSN_C2PA_Verifier()
    media = _media("png", "x", {"c2pa_manifest": "!!!not-base64!!!"})
    valid, details, error = verifier.run(media)
    assert valid is False
    assert details == ""
    assert error != ""


def test_extract_manifest_missing_key_raises():
    import base64
    payload = {"manifest": {}, "signature": "sig"}  # missing 'hash'
    encoded = base64.b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    media = _media("png", "x", {"c2pa_manifest": encoded})
    with pytest.raises(ValueError):
        extract_manifest(media)


def test_sign_manifest_requires_bytes_key():
    with pytest.raises(ValueError):
        sign_manifest({"a": 1}, key="not-bytes")


def test_manifest_hash_is_deterministic_and_order_independent():
    m1 = {"b": 2, "a": 1}
    m2 = {"a": 1, "b": 2}
    assert manifest_hash(m1) == manifest_hash(m2)


def test_node_mappings_are_registered():
    from psn_nodes.gen.n_1_automated_c2pa_provenance_signing import (
        NODE_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS,
    )
    assert "PSN_C2PA_Signer" in NODE_CLASS_MAPPINGS
    assert "PSN_C2PA_Verifier" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_C2PA_Signer"] == "C2PA Provenance Signer"
