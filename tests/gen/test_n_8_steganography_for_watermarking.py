"""Tests for the PSN steganography nodes (pure-logic, no files/network)."""

import json

from psn_nodes.gen.n_8_steganography_for_watermarking import (
    PSN_Steganography_Encoder,
    PSN_Steganography_Decoder,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _make_image(rows):
    return json.dumps(rows)


def _grid(w, h, val=128):
    return [[val] * w for _ in range(h)]


def test_roundtrip_simple_string():
    enc = PSN_Steganography_Encoder()
    dec = PSN_Steganography_Decoder()
    # 16x16 image = 256 pixels = 32 bytes capacity.
    # Header (20 bytes) + "hello world" (11 bytes) = 31 bytes. Fits.
    img = _make_image(_grid(16, 16))
    secret = "hello world"
    wm, key = enc.run(img, secret, "LSB", 1.0)
    assert wm != img
    out, ok = dec.run(wm, key, "LSB")
    assert ok is True
    assert out == secret


def test_roundtrip_json_metadata():
    enc = PSN_Steganography_Encoder()
    dec = PSN_Steganography_Decoder()
    meta = json.dumps({"id": 42, "author": "psn", "tags": ["a", "b"]})
    # 32x32 image = 1024 pixels = 128 bytes capacity.
    # Header (20 bytes) + meta (~40 bytes) = ~60 bytes. Fits.
    img = _make_image(_grid(32, 32))
    wm, key = enc.run(img, meta, "LSB", 1.0)
    out, ok = dec.run(wm, key, "LSB")
    assert ok is True
    assert json.loads(out) == json.loads(meta)


def test_integrity_fails_on_tampered_image():
    enc = PSN_Steganography_Encoder()
    dec = PSN_Steganography_Decoder()
    img = _make_image(_grid(16, 16))
    wm, key = enc.run(img, "secret", "LSB", 1.0)
    rows = json.loads(wm)
    # Flip a bit in the first pixel to corrupt the payload.
    rows[0][0] = rows[0][0] ^ 1
    tampered = _make_image(rows)
    out, ok = dec.run(tampered, key, "LSB")
    assert ok is False


def test_image_too_small_for_payload():
    enc = PSN_Steganography_Encoder()
    # 1x1 image has only 1 pixel = 1 bit, far too small.
    img = _make_image([[128]])
    wm, key = enc.run(img, "this is a long secret that will not fit", "LSB", 1.0)
    assert wm == ""
    assert key.startswith("error:")


def test_bad_image_input():
    enc = PSN_Steganography_Encoder()
    wm, key = enc.run("not json", "x", "LSB", 1.0)
    assert wm == ""
    assert key.startswith("error:")
    # Out-of-range pixel value.
    wm2, key2 = enc.run(json.dumps([[300]]), "x", "LSB", 1.0)
    assert wm2 == ""
    assert key2.startswith("error:")


def test_unsupported_method_rejected():
    enc = PSN_Steganography_Encoder()
    img = _make_image(_grid(16, 16))
    wm, key = enc.run(img, "x", "DCT", 1.0)
    assert wm == ""
    assert "not supported" in key


def test_strength_out_of_range_rejected():
    enc = PSN_Steganography_Encoder()
    img = _make_image(_grid(16, 16))
    wm, key = enc.run(img, "x", "LSB", 1.5)
    assert wm == ""
    assert key.startswith("error:")


def test_method_mismatch_on_decode():
    enc = PSN_Steganography_Encoder()
    dec = PSN_Steganography_Decoder()
    img = _make_image(_grid(16, 16))
    wm, key = enc.run(img, "x", "LSB", 1.0)
    out, ok = dec.run(wm, key, "DCT")
    assert ok is False


def test_node_mappings_present():
    assert "PSN_Steganography_Encoder" in NODE_CLASS_MAPPINGS
    assert "PSN_Steganography_Decoder" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Steganography_Encoder"]
    assert PSN_Steganography_Encoder.FUNCTION == "run"
    assert PSN_Steganography_Encoder.CATEGORY.startswith("ParametricStudio/")
