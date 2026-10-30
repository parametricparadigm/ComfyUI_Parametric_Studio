"""Tests for PSN RGBA support for transparent assets (pure-logic core)."""

import json

import pytest

from psn_nodes.gen.n_3_rgba_support_for_transparent_assets import (
    PSN_Alpha_VAE_Encode,
    PSN_Alpha_VAE_Decode,
    _parse_image,
    _validate_latent,
    _encode_rows,
    _decode_rows,
)


def _make_rgba(h, w, center_transparent=True):
    """Build an RGBA image: opaque edges, transparent center (if requested)."""
    rows = []
    for r in range(h):
        row = []
        for c in range(w):
            is_center = (r == h // 2 and c == w // 2)
            if center_transparent and is_center:
                row.append([255, 0, 0, 0])  # transparent red
            else:
                row.append([0, 255, 0, 255])  # opaque green
        rows.append(row)
    return rows


def _roundtrip(image_rows):
    enc = PSN_Alpha_VAE_Encode()
    dec = PSN_Alpha_VAE_Decode()
    latent_json, _ = enc.run(json.dumps(image_rows), "alpha_vae.safetensors")
    image_json, _ = dec.run(latent_json, "alpha_vae.safetensors")
    return json.loads(image_json)


def test_alpha_preserved_center_transparent():
    """Encode/decode a 3x3 image with a transparent center; alpha must survive."""
    rows = _make_rgba(3, 3, center_transparent=True)
    out = _roundtrip(rows)
    # Center pixel must remain fully transparent (alpha == 0).
    assert out[1][1][3] == 0.0
    # Edge pixel must remain fully opaque (alpha == 255).
    assert out[0][0][3] == 255.0
    # Color channels preserved.
    assert out[1][1][:3] == [255.0, 0.0, 0.0]
    assert out[0][0][:3] == [0.0, 255.0, 0.0]


def test_output_has_four_channels():
    """Every decoded pixel must have exactly 4 channels."""
    rows = _make_rgba(2, 2, center_transparent=False)
    out = _roundtrip(rows)
    for row in out:
        for px in row:
            assert len(px) == 4


def test_lossless_roundtrip_all_opaque():
    """A fully opaque image round-trips exactly (lossless stand-in VAE)."""
    rows = _make_rgba(4, 5, center_transparent=False)
    out = _roundtrip(rows)
    assert out == rows


def test_encode_meta_reports_alpha_preserved():
    """Encode meta must report 4 channels and alpha_preserved True."""
    enc = PSN_Alpha_VAE_Encode()
    rows = _make_rgba(2, 2, center_transparent=True)
    latent_json, meta = enc.run(json.dumps(rows), "alpha_vae.safetensors")
    m = json.loads(meta)
    assert m["channels"] == 4
    assert m["alpha_preserved"] is True
    assert m["height"] == 2
    assert m["width"] == 2
    # Latent itself must be valid 4-channel data.
    h, w, lrows = _validate_latent(latent_json)
    assert h == 2 and w == 2
    for row in lrows:
        for lv in row:
            assert len(lv) == 4


def test_decode_meta_reports_alpha_restored():
    """Decode meta must report alpha_restored True and correct dims."""
    enc = PSN_Alpha_VAE_Encode()
    dec = PSN_Alpha_VAE_Decode()
    rows = _make_rgba(3, 3, center_transparent=True)
    latent_json, _ = enc.run(json.dumps(rows), "alpha_vae.safetensors")
    image_json, meta = dec.run(latent_json, "alpha_vae.safetensors")
    m = json.loads(meta)
    assert m["alpha_restored"] is True
    assert m["channels"] == 4
    assert m["height"] == 3 and m["width"] == 3
    assert json.loads(image_json) == rows


def test_bad_input_wrong_channel_count_raises():
    """A pixel with 3 channels must be rejected."""
    bad = [[[0, 0, 0]]]  # only RGB
    with pytest.raises(ValueError):
        _parse_image(json.dumps(bad))


def test_bad_input_out_of_range_raises():
    """A channel value above 255 must be rejected."""
    bad = [[[0, 0, 0, 300]]]
    with pytest.raises(ValueError):
        _parse_image(json.dumps(bad))


def test_bad_input_invalid_json_raises():
    """Non-JSON text must be rejected."""
    with pytest.raises(ValueError):
        _parse_image("this is not json")


def test_bad_input_ragged_rows_raise():
    """Rows with differing widths must be rejected."""
    bad = [[[0, 0, 0, 255], [0, 0, 0, 255]], [[0, 0, 0, 255]]]
    with pytest.raises(ValueError):
        _parse_image(json.dumps(bad))


def test_bad_input_non_number_channel_raises():
    """A non-numeric channel must be rejected."""
    bad = [[[0, 0, "x", 255]]]
    with pytest.raises(ValueError):
        _parse_image(json.dumps(bad))


def test_encode_rejects_bad_latent_on_decode():
    """Decode must reject a latent that is not 4-channel."""
    dec = PSN_Alpha_VAE_Decode()
    bad_latent = json.dumps([[[0, 0, 0]]])  # 3 channels
    with pytest.raises(ValueError):
        dec.run(bad_latent, "alpha_vae.safetensors")


def test_encode_rejects_empty_image():
    """An empty image (no rows) must be rejected."""
    enc = PSN_Alpha_VAE_Encode()
    with pytest.raises(ValueError):
        enc.run(json.dumps([]), "alpha_vae.safetensors")
