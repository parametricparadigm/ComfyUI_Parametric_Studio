"""Tests for PSN_Replay_Verifier."""

import hashlib
import base64
import pytest

from psn_nodes.gen.psn_replay_verifier import (
    PSN_Replay_Verifier,
    _decode_image_data,
    _compute_hash,
)


def _hex(data: bytes) -> str:
    return data.hex()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class TestDecodeImageData:
    def test_hex_valid(self):
        data = b"\x00\x01\x02\xff"
        result, err = _decode_image_data(_hex(data))
        assert err is None
        assert result == data

    def test_base64_valid(self):
        data = b"hello world"
        result, err = _decode_image_data(_b64(data))
        assert err is None
        assert result == data

    def test_empty_string(self):
        result, err = _decode_image_data("")
        assert err is not None
        assert result is None

    def test_non_string_input(self):
        result, err = _decode_image_data(12345)
        assert err is not None
        assert result is None

    def test_invalid_encoding(self):
        result, err = _decode_image_data("!!!not-valid!!!")
        assert err is not None
        assert result is None


class TestComputeHash:
    def test_md5(self):
        data = b"test data"
        expected = hashlib.md5(data).hexdigest()
        assert _compute_hash(data, "md5") == expected

    def test_sha256(self):
        data = b"test data"
        expected = hashlib.sha256(data).hexdigest()
        assert _compute_hash(data, "sha256") == expected

    def test_invalid_algorithm_raises(self):
        with pytest.raises(ValueError):
            _compute_hash(b"data", "crc32")


class TestPSNReplayVerifier:
    def setup_method(self):
        self.node = PSN_Replay_Verifier()

    def test_match_sha256_hex(self):
        data = b"\x01\x02\x03\x04"
        ref = hashlib.sha256(data).hexdigest()
        image_data = _hex(data)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash=ref,
            run_id="test_run",
            algorithm="sha256",
        )
        assert match is True
        assert cur_hash == ref
        assert img == image_data
        assert "Match" in reason

    def test_mismatch_sha256_hex(self):
        data = b"\x01\x02\x03\x04"
        wrong_ref = "0" * 64
        image_data = _hex(data)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash=wrong_ref,
            run_id="test_run",
            algorithm="sha256",
        )
        assert match is False
        assert cur_hash != wrong_ref
        assert "Mismatch" in reason

    def test_match_md5_base64(self):
        data = b"image bytes here"
        ref = hashlib.md5(data).hexdigest()
        image_data = _b64(data)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash=ref,
            run_id="run_42",
            algorithm="md5",
        )
        assert match is True
        assert cur_hash == ref
        assert "run_42" in reason

    def test_case_insensitive_comparison(self):
        data = b"abc"
        ref_upper = hashlib.sha256(data).hexdigest().upper()
        image_data = _hex(data)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash=ref_upper,
            run_id="case_test",
            algorithm="sha256",
        )
        assert match is True

    def test_empty_reference_hash(self):
        data = b"some data"
        image_data = _hex(data)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash="",
            run_id="empty_ref",
            algorithm="sha256",
        )
        assert match is False
        assert "Mismatch" in reason

    def test_invalid_image_data(self):
        img, match, cur_hash, reason = self.node.run(
            image_data="!!!bad!!!",
            reference_hash="abc123",
            run_id="bad_input",
            algorithm="sha256",
        )
        assert match is False
        assert cur_hash == ""
        assert "Decode error" in reason
        assert "bad_input" in reason

    def test_invalid_algorithm(self):
        data = b"data"
        image_data = _hex(data)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash="abc",
            run_id="algo_test",
            algorithm="crc32",
        )
        assert match is False
        assert "Invalid algorithm" in reason

    def test_identical_tensors_produce_same_hash(self):
        """Simulate two identical 'tensors' (byte sequences) and verify hashes match."""
        tensor_bytes = bytes(range(256)) * 4  # 1024 bytes
        hash1 = hashlib.sha256(tensor_bytes).hexdigest()
        hash2 = hashlib.sha256(tensor_bytes).hexdigest()
        assert hash1 == hash2

        image_data = _hex(tensor_bytes)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash=hash1,
            run_id="determinism",
            algorithm="sha256",
        )
        assert match is True
        assert cur_hash == hash1

    def test_different_data_different_hash(self):
        data_a = b"version A"
        data_b = b"version B"
        hash_a = hashlib.sha256(data_a).hexdigest()
        hash_b = hashlib.sha256(data_b).hexdigest()
        assert hash_a != hash_b

        image_data = _hex(data_a)
        img, match, cur_hash, reason = self.node.run(
            image_data=image_data,
            reference_hash=hash_b,
            run_id="diff_test",
            algorithm="sha256",
        )
        assert match is False
        assert cur_hash == hash_a
