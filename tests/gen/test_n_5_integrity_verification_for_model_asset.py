"""Tests for psn_nodes.gen.n_5_integrity_verification_for_model_asset."""

import base64
import hashlib

import pytest

from psn_nodes.gen.n_5_integrity_verification_for_model_asset import (
    PSN_File_Hasher,
    PSN_Hash_Verifier,
    _compute_hash,
    _decode_data,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _b64(text):
    """Return the base64 encoding of *text* (a str)."""
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _md5_hex(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# PSN_File_Hasher
# ---------------------------------------------------------------------------

class TestPSNFileHasher:

    def test_sha256_known_value(self):
        """Hash a known string and compare with pre-computed SHA-256."""
        node = PSN_File_Hasher()
        payload = "hello world"
        hex_digest, size = node.run(_b64(payload), "SHA-256")
        assert hex_digest == _sha256_hex(payload)
        assert size == len(payload.encode("utf-8"))

    def test_md5_known_value(self):
        """Hash a known string and compare with pre-computed MD5."""
        node = PSN_File_Hasher()
        payload = "integrity-check"
        hex_digest, size = node.run(_b64(payload), "MD5")
        assert hex_digest == _md5_hex(payload)
        assert size == len(payload.encode("utf-8"))

    def test_literal_string_input(self):
        """A plain (non-base64) string is treated as literal UTF-8 bytes."""
        node = PSN_File_Hasher()
        payload = "plain text, not base64"
        hex_digest, size = node.run(payload, "SHA-256")
        assert hex_digest == _sha256_hex(payload)
        assert size == len(payload.encode("utf-8"))

    def test_empty_data_returns_error(self):
        """Empty input should produce an error string, not a hash."""
        node = PSN_File_Hasher()
        hex_digest, size = node.run("", "SHA-256")
        assert "empty" in hex_digest.lower()
        assert size == 0

    def test_non_string_input_returns_error(self):
        """Passing a non-string (e.g. int) should not crash."""
        node = PSN_File_Hasher()
        hex_digest, size = node.run(12345, "SHA-256")
        assert "must be a string" in hex_digest.lower()
        assert size == 0

    def test_large_payload(self):
        """A larger payload (100 KB) should hash correctly."""
        node = PSN_File_Hasher()
        payload = "A" * 100_000
        hex_digest, size = node.run(_b64(payload), "SHA-256")
        assert hex_digest == _sha256_hex(payload)
        assert size == 100_000


# ---------------------------------------------------------------------------
# PSN_Hash_Verifier
# ---------------------------------------------------------------------------

class TestPSNHashVerifier:

    def test_matching_hash(self):
        """Correct expected hash should yield match=True."""
        node = PSN_Hash_Verifier()
        payload = "model-weights-v1"
        expected = _sha256_hex(payload)
        match, actual = node.run(_b64(payload), expected, "SHA-256")
        assert match is True
        assert actual == expected

    def test_mismatching_hash(self):
        """Wrong expected hash should yield match=False."""
        node = PSN_Hash_Verifier()
        payload = "model-weights-v1"
        wrong = "0" * 64  # valid-length but wrong SHA-256
        match, actual = node.run(_b64(payload), wrong, "SHA-256")
        assert match is False
        assert actual == _sha256_hex(payload)

    def test_case_insensitive_comparison(self):
        """Expected hash in upper-case should still match."""
        node = PSN_Hash_Verifier()
        payload = "case-test"
        expected_upper = _sha256_hex(payload).upper()
        match, _ = node.run(_b64(payload), expected_upper, "SHA-256")
        assert match is True

    def test_whitespace_stripped(self):
        """Surrounding whitespace in expected hash is ignored."""
        node = PSN_Hash_Verifier()
        payload = "ws-test"
        expected = "  " + _sha256_hex(payload) + "  "
        match, _ = node.run(_b64(payload), expected, "SHA-256")
        assert match is True

    def test_md5_verification(self):
        """MD5 algorithm path should work end-to-end."""
        node = PSN_Hash_Verifier()
        payload = "md5-verify"
        expected = _md5_hex(payload)
        match, actual = node.run(_b64(payload), expected, "MD5")
        assert match is True
        assert actual == expected

    def test_empty_data_returns_error(self):
        """Empty data should produce an error string, match=False."""
        node = PSN_Hash_Verifier()
        match, actual = node.run("", "abc123", "SHA-256")
        assert match is False
        assert "empty" in actual.lower()

    def test_non_string_data_returns_error(self):
        """Non-string data should not crash; returns error."""
        node = PSN_Hash_Verifier()
        match, actual = node.run(None, "abc123", "SHA-256")
        assert match is False
        assert "must be a string" in actual.lower()


# ---------------------------------------------------------------------------
# Internal helper edge cases
# ---------------------------------------------------------------------------

class TestInternalHelpers:

    def test_decode_data_valid_base64(self):
        raw, err = _decode_data(_b64("test"))
        assert err == ""
        assert raw == b"test"

    def test_decode_data_literal_fallback(self):
        """A string that is not valid base64 falls back to UTF-8."""
        raw, err = _decode_data("hello world!")
        assert err == ""
        assert raw == b"hello world!"

    def test_decode_data_empty(self):
        raw, err = _decode_data("")
        assert raw == b""
        assert "empty" in err.lower()

    def test_compute_hash_unknown_algorithm(self):
        digest, err = _compute_hash("data", "SHA-1")
        assert digest == ""
        assert "Unknown algorithm" in err

    def test_compute_hash_empty_data(self):
        digest, err = _compute_hash("", "SHA-256")
        assert digest == ""
        assert "empty" in err.lower()
