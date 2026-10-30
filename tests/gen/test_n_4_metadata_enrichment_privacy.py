"""Tests for psn_nodes.gen.n_4_metadata_enrichment_privacy.

Covers the pure-logic metadata enrichment & privacy nodes: key parsing,
XOR encrypt/decrypt round-trip, editor/decryptor behaviour, and a set of
edge cases and bad-input handling.  No files, no network, no GPU.
"""

import base64
import json

import pytest

from psn_nodes.gen.n_4_metadata_enrichment_privacy import (
    PSN_Metadata_Decryptor,
    PSN_Metadata_Editor,
    _decrypt_value,
    _encrypt_value,
    _parse_key_list,
)


# ---------------------------------------------------------------------------
# Helper-level tests
# ---------------------------------------------------------------------------

def test_parse_key_list_basic():
    assert _parse_key_list("prompt, negative_prompt") == ["prompt", "negative_prompt"]


def test_parse_key_list_strips_and_drops_empty():
    assert _parse_key_list("  a , , b ,,c ") == ["a", "b", "c"]


def test_parse_key_list_bad_inputs():
    assert _parse_key_list(None) == []
    assert _parse_key_list("") == []
    assert _parse_key_list(123) == []
    assert _parse_key_list(["a", "b"]) == []


TEST_KEY = "correct horse battery staple"


def test_no_default_key_and_short_or_missing_passphrase_is_refused(monkeypatch):
    monkeypatch.delenv("PSN_STUDIO_PASSPHRASE", raising=False)
    for bad in ("", None, "short"):
        with pytest.raises(ValueError, match="passphrase"):
            _encrypt_value("x", bad)
    monkeypatch.setenv("PSN_STUDIO_PASSPHRASE", "from the environment 1")
    assert _decrypt_value(_encrypt_value("x", ""), "") == "x"          # empty input falls back to the environment variable


def test_encryption_is_authenticated_salted_and_wrong_key_fails():
    t1, t2 = _encrypt_value("secret prompt", TEST_KEY), _encrypt_value("secret prompt", TEST_KEY)
    assert t1 != t2 and t1.startswith("psn1.")                          # fresh random salt every time
    assert "secret" not in t1
    with pytest.raises(ValueError, match="wrong passphrase or damaged"):
        _decrypt_value(t1, "another passphrase here")
    tampered = t1[:-4] + ("AAAA" if not t1.endswith("AAAA") else "BBBB")
    with pytest.raises(ValueError):
        _decrypt_value(tampered, TEST_KEY)                             # the authentication tag catches edits
    with pytest.raises(ValueError, match="Not an encrypted token"):
        _decrypt_value("plain text", TEST_KEY)

def test_encrypt_decrypt_round_trip_various_types():
    key = TEST_KEY
    for value in ["a prompt", 42, 3.14, True, None, ["a", "b"], {"k": "v"}]:
        token = _encrypt_value(value, key)
        assert isinstance(token, str)
        # Encrypted token must not contain the raw value text. A short value such as 42 can turn up by chance in random ciphertext, so only longer ones can be checked this way.
        raw = json.dumps(value)
        if len(raw) >= 8: assert raw not in token
        assert _decrypt_value(token, key) == value


def test_encrypt_value_rejects_empty_key():
    with pytest.raises(ValueError):
        _encrypt_value("x", "")


def test_decrypt_value_rejects_bad_token():
    with pytest.raises(ValueError):
        _decrypt_value("not-base64!!!", "key")
    with pytest.raises(ValueError):
        _decrypt_value(12345, "key")


def test_decrypt_value_wrong_key_fails():
    token = _encrypt_value("a secret prompt", "key-number-one")
    with pytest.raises(ValueError, match="wrong passphrase"):
        _decrypt_value(token, "key-number-two")


# ---------------------------------------------------------------------------
# Node-level tests
# ---------------------------------------------------------------------------

def test_editor_encrypts_only_listed_keys():
    node = PSN_Metadata_Editor()
    image = {"data": "img", "meta": {"existing": "keep"}}
    metadata = {"prompt": "a cat", "negative_prompt": "blurry", "seed": 7}
    out = node.run(image, metadata, "prompt, negative_prompt", TEST_KEY)
    payload = out[0]
    meta = payload["meta"]

    # Non-encrypted keys pass through unchanged.
    assert meta["seed"] == 7
    assert meta["existing"] == "keep"

    # Encrypted keys are opaque strings, not the raw values.
    assert isinstance(meta["prompt"], str)
    assert meta["prompt"] != "a cat"
    assert meta["negative_prompt"] != "blurry"

    # The encrypted token is a versioned, salted, authenticated token.
    assert meta["prompt"].startswith("psn1.")


def test_editor_and_decryptor_round_trip():
    editor = PSN_Metadata_Editor()
    decryptor = PSN_Metadata_Decryptor()
    key = "round-trip-key"

    image = {"data": "img", "meta": {}}
    metadata = {"prompt": "a dog", "negative_prompt": "ugly", "steps": 20}
    (encrypted_payload,) = editor.run(image, metadata, "prompt, negative_prompt", key)

    (decrypted,) = decryptor.run(encrypted_payload, "prompt, negative_prompt", key)

    assert decrypted["prompt"] == "a dog"
    assert decrypted["negative_prompt"] == "ugly"
    # Non-encrypted key is preserved as-is.
    assert decrypted["steps"] == 20


def test_decryptor_without_keys_returns_raw_meta():
    decryptor = PSN_Metadata_Decryptor()
    image = {"data": "img", "meta": {"prompt": "raw", "seed": 1}}
    (meta,) = decryptor.run(image, "", TEST_KEY)
    assert meta == {"prompt": "raw", "seed": 1}


def test_editor_none_image_and_none_metadata():
    node = PSN_Metadata_Editor()
    (payload,) = node.run(None, {}, "", TEST_KEY)
    assert payload["meta"] == {}
    assert payload["data"] is None


def test_editor_rejects_non_dict_metadata():
    node = PSN_Metadata_Editor()
    with pytest.raises(ValueError):
        node.run({"meta": {}}, "not-a-dict", "", TEST_KEY)


def test_decryptor_rejects_non_string_encrypted_value():
    decryptor = PSN_Metadata_Decryptor()
    # A key listed for decryption but holding a non-string value must fail.
    image = {"data": "img", "meta": {"prompt": 12345}}
    with pytest.raises(ValueError):
        decryptor.run(image, "prompt", TEST_KEY)


def test_editor_empty_encrypt_keys_leaves_values_plain():
    node = PSN_Metadata_Editor()
    image = {"data": "img", "meta": {}}
    (payload,) = node.run(image, {"prompt": "plain"}, "", TEST_KEY)
    assert payload["meta"]["prompt"] == "plain"


def test_registry_mappings_present():
    from psn_nodes.gen import n_4_metadata_enrichment_privacy as mod

    assert "PSN_Metadata_Editor" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_Metadata_Decryptor" in mod.NODE_CLASS_MAPPINGS
    assert mod.NODE_CLASS_MAPPINGS["PSN_Metadata_Editor"] is PSN_Metadata_Editor
    assert mod.NODE_CLASS_MAPPINGS["PSN_Metadata_Decryptor"] is PSN_Metadata_Decryptor
    assert "PSN_Metadata_Editor" in mod.NODE_DISPLAY_NAME_MAPPINGS
