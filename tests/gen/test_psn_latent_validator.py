"""Tests for PSN_LatentValidator (pure-logic latent metadata validation)."""

import json

import pytest

from psn_nodes.gen.psn_latent_validator import (
    PSN_LatentValidator,
    _parse_latent_meta,
    _validate_latent,
    ALLOWED_DTYPES,
    EXPECTED_DIMS,
)


def _meta(dims, channels=None, dtype=None):
    d = {"dims": dims}
    if channels is not None:
        d["channels"] = channels
    if dtype is not None:
        d["dtype"] = dtype
    return json.dumps(d)


def test_valid_latent_passes():
    node = PSN_LatentValidator()
    out_meta, is_valid, reason = node.run(_meta([1, 4, 64, 64], 4, "float16"))
    assert is_valid is True
    assert reason == "ok"
    parsed = json.loads(out_meta)
    assert parsed["dims"] == [1, 4, 64, 64]
    assert parsed["channels"] == 4
    assert parsed["dtype"] == "float16"


def test_3d_tensor_is_invalid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 4, 64], 4, "float16"))
    assert is_valid is False
    assert "expected 4 dims" in reason


def test_5d_tensor_is_invalid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 4, 64, 64, 2], 4, "float16"))
    assert is_valid is False
    assert "expected 4 dims" in reason


def test_channel_mismatch_is_invalid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 4, 64, 64], 4, "float16"), expected_channels=8)
    assert is_valid is False
    assert "channels mismatch" in reason


def test_channel_match_is_valid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 8, 32, 32], 8, "bfloat16"), expected_channels=8)
    assert is_valid is True
    assert reason == "ok"


def test_disallowed_dtype_is_invalid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 4, 64, 64], 4, "int8"))
    assert is_valid is False
    assert "not in allow-list" in reason


def test_all_allowed_dtypes_pass():
    node = PSN_LatentValidator()
    for dt in ALLOWED_DTYPES:
        _, is_valid, reason = node.run(_meta([1, 4, 64, 64], 4, dt))
        assert is_valid is True, "dtype %s should be allowed" % dt


def test_malformed_json_is_invalid_not_strict():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run("not json at all")
    assert is_valid is False
    assert "parse error" in reason


def test_malformed_json_strict_raises():
    node = PSN_LatentValidator()
    with pytest.raises(ValueError):
        node.run("not json at all", strict=True)


def test_missing_dims_key_raises_parse_error():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(json.dumps({"channels": 4}))
    assert is_valid is False
    assert "parse error" in reason


def test_negative_dim_is_invalid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 4, -64, 64], 4, "float16"))
    assert is_valid is False
    assert "non-negative" in reason


def test_zero_dim_is_invalid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([0, 4, 64, 64], 4, "float16"))
    assert is_valid is False
    assert "must be positive" in reason


def test_expected_channels_set_but_missing_is_invalid():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 4, 64, 64], None, "float16"), expected_channels=4)
    assert is_valid is False
    assert "channels not provided" in reason


def test_expected_channels_minus_one_means_not_provided():
    node = PSN_LatentValidator()
    _, is_valid, reason = node.run(_meta([1, 4, 64, 64], 4, "float16"), expected_channels=-1)
    assert is_valid is True
    assert reason == "ok"


def test_parse_meta_rejects_non_int_dims():
    with pytest.raises(ValueError):
        _parse_latent_meta(json.dumps({"dims": [1, "4", 64, 64]}))


def test_parse_meta_rejects_bool_as_dim():
    with pytest.raises(ValueError):
        _parse_latent_meta(json.dumps({"dims": [True, 4, 64, 64]}))


def test_parse_meta_rejects_negative_channels():
    with pytest.raises(ValueError):
        _parse_latent_meta(json.dumps({"dims": [1, 4, 64, 64], "channels": -1}))


def test_parse_meta_accepts_dict_input():
    meta = _parse_latent_meta({"dims": [1, 4, 64, 64], "channels": 4, "dtype": "float32"})
    assert meta["dims"] == [1, 4, 64, 64]
    assert meta["channels"] == 4
    assert meta["dtype"] == "float32"


def test_validate_latent_helper_direct():
    meta = {"dims": [1, 4, 64, 64], "channels": 4, "dtype": "float16"}
    ok, why = _validate_latent(meta, expected_channels=4)
    assert ok is True
    assert why == "ok"


def test_validate_latent_helper_direct_bad_dims():
    meta = {"dims": [1, 4, 64], "channels": 4, "dtype": "float16"}
    ok, why = _validate_latent(meta)
    assert ok is False
    assert "expected 4 dims" in why


def test_expected_dims_constant_is_four():
    assert EXPECTED_DIMS == 4


def test_node_class_mappings_present():
    from psn_nodes.gen import psn_latent_validator as mod
    assert "PSN_LatentValidator" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_LatentValidator" in mod.NODE_DISPLAY_NAME_MAPPINGS
