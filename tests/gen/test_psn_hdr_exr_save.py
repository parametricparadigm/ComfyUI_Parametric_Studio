"""Tests for psn_nodes.gen.psn_hdr_exr_save (pure-logic EXR save planner)."""

import json

from psn_nodes.gen.psn_hdr_exr_save import (
    PSN_HDR_EXR_Save,
    _psn_validate_path,
    _psn_validate_compression,
    _psn_estimate_bytes,
)


def test_psn_validate_path_accepts_safe_relative():
    ok, why = _psn_validate_path("out/exr/frame.exr")
    assert ok is True
    assert why == "ok"


def test_psn_validate_path_rejects_traversal():
    ok, why = _psn_validate_path("../etc/passwd.exr")
    assert ok is False
    assert "traversal" in why


def test_psn_validate_path_rejects_absolute_and_bad_ext():
    ok1, _ = _psn_validate_path("/tmp/x.exr")
    assert ok1 is False
    ok2, why2 = _psn_validate_path("out/image.png")
    assert ok2 is False
    assert "extension" in why2


def test_psn_validate_compression_allowlist():
    assert _psn_validate_compression("Zip")[0] is True
    ok, why = _psn_validate_compression("LZW")
    assert ok is False
    assert "compression" in why


def test_psn_estimate_bytes_math():
    # 2x3x3 channels * 4 bytes = 72
    assert _psn_estimate_bytes(2, 3, 3) == 72


def test_psn_run_success_returns_saved_and_plan():
    node = PSN_HDR_EXR_Save()
    status, plan_json = node.run(
        height=2, width=3, channels=3,
        file_path="out/frame.exr",
        compression="Piz",
        free_space=1000.0,
    )
    assert status == "Saved"
    plan = json.loads(plan_json)
    assert plan["required_bytes"] == 72
    assert plan["fits"] is True
    assert plan["compression"] == "Piz"


def test_psn_run_insufficient_space_reports_error():
    node = PSN_HDR_EXR_Save()
    status, plan_json = node.run(
        height=100, width=100, channels=3,
        file_path="out/frame.exr",
        compression="None",
        free_space=10.0,
    )
    assert status.startswith("Error: insufficient disk space")
    plan = json.loads(plan_json)
    assert plan["fits"] is False
    assert plan["required_bytes"] > plan["free_space_bytes"]


def test_psn_run_bad_path_returns_error():
    node = PSN_HDR_EXR_Save()
    status, plan_json = node.run(
        height=2, width=2, channels=3,
        file_path="../../evil.exr",
        compression="Zip",
        free_space=1e9,
    )
    assert status.startswith("Error:")
    assert "traversal" in status
    assert json.loads(plan_json)["error"] == "path traversal is not allowed"


def test_psn_run_bad_compression_returns_error():
    node = PSN_HDR_EXR_Save()
    status, plan_json = node.run(
        height=2, width=2, channels=3,
        file_path="out/frame.exr",
        compression="Bogus",
        free_space=1e9,
    )
    assert status.startswith("Error:")
    assert "compression" in status


def test_psn_run_null_byte_path_rejected():
    node = PSN_HDR_EXR_Save()
    status, _ = node.run(
        height=2, width=2, channels=3,
        file_path="out/bad\x00name.exr",
        compression="Zip",
        free_space=1e9,
    )
    assert status.startswith("Error:")
    assert "null byte" in status
