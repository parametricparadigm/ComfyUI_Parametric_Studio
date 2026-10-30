"""Tests for PSN_Seed_Auditor node."""

import json
import hashlib

from psn_nodes.gen.psn_seed_auditor import PSN_Seed_Auditor


def test_seed_auditor_basic_run():
    """Basic run with no expected_seed: should return seed, audit JSON, and hash."""
    node = PSN_Seed_Auditor()
    seed, audit_result, digest = node.run(seed=12345, run_id="run_001", model_name="sd_xl_base")
    assert seed == 12345
    assert isinstance(audit_result, str)
    assert isinstance(digest, str)
    # Verify hash is correct SHA256 of "12345:sd_xl_base"
    expected_hash = hashlib.sha256("12345:sd_xl_base".encode("utf-8")).hexdigest()
    assert digest == expected_hash
    # Verify audit JSON structure
    audit = json.loads(audit_result)
    assert audit["seed"] == 12345
    assert audit["run_id"] == "run_001"
    assert audit["model_name"] == "sd_xl_base"
    assert audit["hash"] == expected_hash
    assert audit["expected_seed"] is None
    assert audit["match"] is None
    assert audit["status"] == "NO_EXPECTED"


def test_seed_auditor_match_pass():
    """When expected_seed matches seed, status should be PASS."""
    node = PSN_Seed_Auditor()
    seed, audit_result, digest = node.run(
        seed=99999, run_id="run_002", model_name="sdxl", expected_seed=99999
    )
    assert seed == 99999
    audit = json.loads(audit_result)
    assert audit["expected_seed"] == 99999
    assert audit["match"] is True
    assert audit["status"] == "PASS"


def test_seed_auditor_mismatch_fail():
    """When expected_seed does not match seed, status should be FAIL."""
    node = PSN_Seed_Auditor()
    seed, audit_result, digest = node.run(
        seed=11111, run_id="run_003", model_name="sdxl", expected_seed=22222
    )
    assert seed == 11111
    audit = json.loads(audit_result)
    assert audit["expected_seed"] == 22222
    assert audit["match"] is False
    assert audit["status"] == "FAIL"


def test_seed_auditor_zero_seed():
    """Edge case: seed = 0 should work correctly."""
    node = PSN_Seed_Auditor()
    seed, audit_result, digest = node.run(seed=0, run_id="run_000", model_name="model_a")
    assert seed == 0
    expected_hash = hashlib.sha256("0:model_a".encode("utf-8")).hexdigest()
    assert digest == expected_hash
    audit = json.loads(audit_result)
    assert audit["seed"] == 0


def test_seed_auditor_max_seed():
    """Edge case: maximum 32-bit seed value."""
    max_seed = 2**32 - 1
    node = PSN_Seed_Auditor()
    seed, audit_result, digest = node.run(
        seed=max_seed, run_id="run_max", model_name="big_model"
    )
    assert seed == max_seed
    expected_hash = hashlib.sha256(f"{max_seed}:big_model".encode("utf-8")).hexdigest()
    assert digest == expected_hash


def test_seed_auditor_different_models_different_hashes():
    """Same seed but different model names should produce different hashes."""
    node = PSN_Seed_Auditor()
    _, _, hash_a = node.run(seed=42, run_id="r1", model_name="model_a")
    _, _, hash_b = node.run(seed=42, run_id="r1", model_name="model_b")
    assert hash_a != hash_b


def test_seed_auditor_same_seed_same_model_same_hash():
    """Same seed and model name should always produce the same hash (deterministic)."""
    node = PSN_Seed_Auditor()
    _, _, hash1 = node.run(seed=777, run_id="r1", model_name="stable")
    _, _, hash2 = node.run(seed=777, run_id="r2", model_name="stable")
    assert hash1 == hash2


def test_seed_auditor_expected_seed_zero():
    """Edge case: expected_seed = 0 should be treated as provided (not None)."""
    node = PSN_Seed_Auditor()
    seed, audit_result, _ = node.run(
        seed=0, run_id="run_zero", model_name="m", expected_seed=0
    )
    audit = json.loads(audit_result)
    assert audit["expected_seed"] == 0
    assert audit["match"] is True
    assert audit["status"] == "PASS"


def test_seed_auditor_bad_input_negative_seed():
    """Negative seed should still be handled (hash computed, no crash)."""
    node = PSN_Seed_Auditor()
    seed, audit_result, digest = node.run(seed=-1, run_id="neg", model_name="m")
    assert seed == -1
    expected_hash = hashlib.sha256("-1:m".encode("utf-8")).hexdigest()
    assert digest == expected_hash
    audit = json.loads(audit_result)
    assert audit["seed"] == -1


def test_seed_auditor_empty_model_name():
    """Edge case: empty model_name string should still produce a valid hash."""
    node = PSN_Seed_Auditor()
    seed, audit_result, digest = node.run(seed=5, run_id="r", model_name="")
    assert seed == 5
    expected_hash = hashlib.sha256("5:".encode("utf-8")).hexdigest()
    assert digest == expected_hash
    audit = json.loads(audit_result)
    assert audit["model_name"] == ""
