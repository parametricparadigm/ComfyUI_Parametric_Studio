"""Tests for PSN_LatentForensics node."""

import json
import math
import pytest

from psn_nodes.gen.psn_latent_forensics import (
    PSN_LatentForensics,
    _check_shape,
    _check_dtype,
    _scan_values,
    _flatten,
)


def _make_node():
    return PSN_LatentForensics()


def test_valid_latent_passes():
    node = _make_node()
    report, is_valid = node.run(
        run_id="test_ok",
        actual_shape="1,4,64,64",
        expected_shape="1,4,64,64",
        actual_dtype="float16",
        expected_dtype="float16",
        sampled_values="[1.0, 2.0, 3.0, -0.5]",
    )
    assert is_valid is True
    data = json.loads(report)
    assert data["is_valid"] is True
    assert data["shape"]["matches"] is True
    assert data["dtype"]["matches"] is True
    assert data["values"]["has_nan"] is False
    assert data["values"]["has_inf"] is False


def test_nan_injected_invalid():
    node = _make_node()
    # Use a string representation that json.loads can parse as NaN
    # Python's json module accepts NaN, Infinity, -Infinity as literals
    report, is_valid = node.run(
        run_id="test_nan",
        actual_shape="1,4,64,64",
        expected_shape="1,4,64,64",
        actual_dtype="float16",
        expected_dtype="float16",
        sampled_values="[1.0, NaN, 3.0]",
    )
    assert is_valid is False
    data = json.loads(report)
    assert data["values"]["has_nan"] is True
    assert data["values"]["nan_count"] == 1


def test_inf_injected_invalid():
    node = _make_node()
    report, is_valid = node.run(
        run_id="test_inf",
        actual_shape="1,4,64,64",
        expected_shape="1,4,64,64",
        actual_dtype="float32",
        expected_dtype="float32",
        sampled_values="[1.0, Infinity, 3.0]",
    )
    assert is_valid is False
    data = json.loads(report)
    assert data["values"]["has_inf"] is True
    assert data["values"]["inf_count"] == 1


def test_shape_mismatch_invalid():
    node = _make_node()
    report, is_valid = node.run(
        run_id="test_shape",
        actual_shape="1,4,32,32",
        expected_shape="1,4,64,64",
        actual_dtype="float16",
        expected_dtype="float16",
        sampled_values="[1.0, 2.0]",
    )
    assert is_valid is False
    data = json.loads(report)
    assert data["shape"]["matches"] is False
    assert "dim" in data["shape"]["detail"]


def test_dtype_mismatch_invalid():
    node = _make_node()
    report, is_valid = node.run(
        run_id="test_dtype",
        actual_shape="1,4,64,64",
        expected_shape="1,4,64,64",
        actual_dtype="float32",
        expected_dtype="float16",
        sampled_values="[1.0, 2.0]",
    )
    assert is_valid is False
    data = json.loads(report)
    assert data["dtype"]["matches"] is False


def test_bad_shape_string_handled():
    node = _make_node()
    report, is_valid = node.run(
        run_id="test_bad_shape",
        actual_shape="not_a_shape",
        expected_shape="1,4,64,64",
        actual_dtype="float16",
        expected_dtype="float16",
        sampled_values="[1.0]",
    )
    assert is_valid is False
    data = json.loads(report)
    assert data["shape"]["matches"] is False


def test_bad_sampled_values_json_handled():
    node = _make_node()
    report, is_valid = node.run(
        run_id="test_bad_json",
        actual_shape="1,4,64,64",
        expected_shape="1,4,64,64",
        actual_dtype="float16",
        expected_dtype="float16",
        sampled_values="not valid json",
    )
    # No values to scan, shape/dtype ok, so valid
    assert is_valid is True
    data = json.loads(report)
    assert data["values"]["sampled_count"] == 0


def test_nested_sampled_values_flattened():
    node = _make_node()
    report, is_valid = node.run(
        run_id="test_nested",
        actual_shape="1,4,64,64",
        expected_shape="1,4,64,64",
        actual_dtype="float16",
        expected_dtype="float16",
        sampled_values="[[1.0, 2.0], [3.0, NaN]]",
    )
    assert is_valid is False
    data = json.loads(report)
    assert data["values"]["sampled_count"] == 4
    assert data["values"]["nan_count"] == 1


def test_max_sampled_limits_scan():
    node = _make_node()
    # 10 values, but max_sampled=3
    report, is_valid = node.run(
        run_id="test_max",
        actual_shape="1,4,64,64",
        expected_shape="1,4,64,64",
        actual_dtype="float16",
        expected_dtype="float16",
        sampled_values="[1.0, 2.0, 3.0, NaN, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]",
        max_sampled=3,
    )
    # NaN is at index 3, beyond max_sampled=3, so not scanned
    assert is_valid is True
    data = json.loads(report)
    assert data["values"]["sampled_count"] == 3
    assert data["values"]["has_nan"] is False


def test_check_shape_helper():
    assert _check_shape((1, 4, 64, 64), (1, 4, 64, 64))[0] is True
    assert _check_shape((1, 4, 32, 32), (1, 4, 64, 64))[0] is False
    assert _check_shape((1, 4), (1, 4, 64, 64))[0] is False
    assert _check_shape("bad", (1, 4))[0] is False


def test_check_dtype_helper():
    assert _check_dtype("float16", "float16")[0] is True
    assert _check_dtype("float32", "float16")[0] is False
    assert _check_dtype("unknown", "float16")[0] is False


def test_scan_values_helper():
    has_nan, has_inf, nan_c, inf_c = _scan_values([1.0, float("nan"), float("inf"), 2.0])
    assert has_nan is True
    assert has_inf is True
    assert nan_c == 1
    assert inf_c == 1


def test_flatten_helper():
    assert _flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]
    assert _flatten(42) == [42]
    assert _flatten([]) == []
