"""Tests for PSN_FilePathValidator node."""

import pytest
from psn_nodes.gen.psn_filepathvalidator import PSN_FilePathValidator


@pytest.fixture
def node():
    return PSN_FilePathValidator()


def test_valid_simple_relative_path(node):
    valid, err = node.run("assets/video.mp4", 8188)
    assert valid is True
    assert err == ""


def test_valid_absolute_unix_path(node):
    valid, err = node.run("/home/user/projects/output.mp4", 8188)
    assert valid is True
    assert err == ""


def test_valid_windows_path(node):
    valid, err = node.run("C:\\Users\\test\\video.mp4", 8188)
    assert valid is True
    assert err == ""


def test_empty_path_rejected(node):
    valid, err = node.run("", 8188)
    assert valid is False
    assert "empty" in err.lower()


def test_path_with_traversal_rejected(node):
    valid, err = node.run("../../etc/passwd", 8188)
    assert valid is False
    assert "traversal" in err.lower()


def test_path_with_null_byte_rejected(node):
    valid, err = node.run("file\x00name.mp4", 8188)
    assert valid is False
    assert "null" in err.lower()


def test_path_with_control_char_rejected(node):
    valid, err = node.run("file\x01name.mp4", 8188)
    assert valid is False
    assert "control character" in err.lower()


def test_url_path_rejected(node):
    valid, err = node.run("https://example.com/video.mp4", 8188)
    assert valid is False
    assert "URL" in err or "url" in err.lower()


def test_ftp_scheme_rejected(node):
    valid, err = node.run("ftp://server/video.mp4", 8188)
    assert valid is False
    assert "protocol" in err.lower() or "scheme" in err.lower()


def test_port_zero_rejected(node):
    valid, err = node.run("valid/path.mp4", 0)
    assert valid is False
    assert "port" in err.lower()


def test_port_too_large_rejected(node):
    valid, err = node.run("valid/path.mp4", 65536)
    assert valid is False
    assert "port" in err.lower()


def test_port_max_valid(node):
    valid, err = node.run("valid/path.mp4", 65535)
    assert valid is True
    assert err == ""


def test_port_min_valid(node):
    valid, err = node.run("valid/path.mp4", 1)
    assert valid is True
    assert err == ""


def test_excessively_long_path_rejected(node):
    long_path = "a" * 4097
    valid, err = node.run(long_path, 8188)
    assert valid is False
    assert "length" in err.lower()


def test_path_at_max_length_valid(node):
    max_path = "a" * 4096
    valid, err = node.run(max_path, 8188)
    assert valid is True
    assert err == ""


def test_non_string_path_rejected(node):
    valid, err = node.run(12345, 8188)
    assert valid is False
    assert "string" in err.lower()


def test_bool_port_rejected(node):
    valid, err = node.run("valid/path.mp4", True)
    assert valid is False
    assert "integer" in err.lower()


def test_tab_in_path_is_allowed(node):
    valid, err = node.run("file\tname.mp4", 8188)
    assert valid is True
    assert err == ""


def test_file_scheme_allowed(node):
    valid, err = node.run("file:///home/user/video.mp4", 8188)
    assert valid is True
    assert err == ""
