"""Tests for PSN Video-in-PNG Steganography (pure-logic, no I/O)."""

import struct

import pytest

from psn_nodes.gen.n_8_video_in_image_steganography_for_deliv import (
    PSN_Video_In_PNG_Decode,
    PSN_Video_In_PNG_Encode,
    decode_video_from_png,
    encode_video_in_png,
    _IEND_CHUNK,
    _PNG_SIGNATURE,
)


def _make_png(payload: bytes = b"fake-image-data") -> bytes:
    """Build a minimal valid-looking PNG byte stream ending with IEND."""
    # Signature + a fake IHDR-like chunk + IEND.
    fake_chunk = struct.pack(">I", len(payload)) + b"IHDR" + payload + struct.pack(">I", 0)
    return _PNG_SIGNATURE + fake_chunk + _IEND_CHUNK


def _make_video(payload: bytes = b"fake-video-bytes") -> bytes:
    """Build a fake video payload (non-empty)."""
    return payload


class TestEncodeDecodeRoundTrip:
    def test_round_trip_basic(self):
        png = _make_png()
        video = _make_video(b"0123456789")
        combined, offset = encode_video_in_png(png, video)
        assert offset == len(png)
        assert combined == png + video
        extracted = decode_video_from_png(combined, offset)
        assert extracted == video

    def test_round_trip_with_string_offset(self):
        png = _make_png()
        video = _make_video(b"abc")
        combined, offset = encode_video_in_png(png, video)
        extracted = decode_video_from_png(combined, str(offset))
        assert extracted == video


class TestEncodeValidation:
    def test_encode_rejects_non_png(self):
        # Create a payload that is long enough to pass the size check
        # but does not start with the PNG signature.
        bad_png = b"X" * (len(_PNG_SIGNATURE) + len(_IEND_CHUNK) + 10)
        with pytest.raises(ValueError, match="PNG signature"):
            encode_video_in_png(bad_png, b"video")

    def test_encode_rejects_png_without_iend(self):
        bad_png = _PNG_SIGNATURE + b"garbage"
        with pytest.raises(ValueError, match="IEND"):
            encode_video_in_png(bad_png, b"video")

    def test_encode_rejects_empty_video(self):
        png = _make_png()
        with pytest.raises(ValueError, match="empty"):
            encode_video_in_png(png, b"")

    def test_encode_rejects_wrong_type(self):
        png = _make_png()
        with pytest.raises(TypeError):
            encode_video_in_png(png, 12345)


class TestDecodeValidation:
    def test_decode_rejects_offset_beyond_length(self):
        png = _make_png()
        video = _make_video(b"xyz")
        combined, offset = encode_video_in_png(png, video)
        # offset + 1 is strictly greater than len(combined)
        with pytest.raises(ValueError, match="exceeds"):
            decode_video_from_png(combined, len(combined) + 1)

    def test_decode_rejects_offset_at_end(self):
        png = _make_png()
        video = _make_video(b"xyz")
        combined, _ = encode_video_in_png(png, video)
        with pytest.raises(ValueError, match="end of payload"):
            decode_video_from_png(combined, len(combined))

    def test_decode_rejects_bad_iend_preceding_offset(self):
        # Craft a combined stream where the bytes before offset are not IEND.
        fake = _PNG_SIGNATURE + b"AAAA" + b"video-data"
        with pytest.raises(ValueError, match="IEND"):
            decode_video_from_png(fake, len(_PNG_SIGNATURE) + 4)

    def test_decode_rejects_negative_offset(self):
        png = _make_png()
        video = _make_video(b"xyz")
        combined, _ = encode_video_in_png(png, video)
        with pytest.raises(ValueError, match="non-negative"):
            decode_video_from_png(combined, -1)

    def test_decode_rejects_bool_offset(self):
        png = _make_png()
        video = _make_video(b"xyz")
        combined, _ = encode_video_in_png(png, video)
        with pytest.raises(TypeError):
            decode_video_from_png(combined, True)


class TestNodeWrappers:
    def test_encode_node_returns_bytes_and_string_offset(self):
        node = PSN_Video_In_PNG_Encode()
        png = _make_png()
        video = _make_video(b"clip")
        combined, offset_str = node.run(png, video)
        assert isinstance(combined, bytes)
        assert isinstance(offset_str, str)
        assert int(offset_str) == len(png)

    def test_decode_node_returns_video_bytes(self):
        encode_node = PSN_Video_In_PNG_Encode()
        decode_node = PSN_Video_In_PNG_Decode()
        png = _make_png()
        video = _make_video(b"clip-data")
        combined, offset_str = encode_node.run(png, video)
        (extracted,) = decode_node.run(combined, int(offset_str))
        assert extracted == video

    def test_node_input_types_are_dict(self):
        assert isinstance(PSN_Video_In_PNG_Encode.INPUT_TYPES(), dict)
        assert isinstance(PSN_Video_In_PNG_Decode.INPUT_TYPES(), dict)
