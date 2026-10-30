"""
Tests for PSN_ScRNA_Cluster node.

Covers:
- Valid input produces correct config and estimated clusters
- Invalid resolution (negative, too large, non-numeric)
- Invalid n_neighbors (zero, negative, non-int)
- Invalid adata JSON (malformed, missing keys, not normalized, disallowed keys)
- Edge cases: zero cells, large resolution
- Status string correctness
"""

import json
import math

import pytest

from psn_nodes.gen.psn_scrna_cluster import (
    PSN_ScRNA_Cluster,
    _validate_resolution,
    _validate_n_neighbors,
    _validate_adata_payload,
    _build_clustering_config,
    _estimate_n_clusters,
)


def _make_adata_json(n_obs=100, n_vars=50, is_normalized=True, **extra):
    payload = {
        "n_obs": n_obs,
        "n_vars": n_vars,
        "is_normalized": is_normalized,
    }
    payload.update(extra)
    return json.dumps(payload)


class TestValidateResolution:
    def test_valid_resolution(self):
        ok, reason = _validate_resolution(1.0)
        assert ok is True
        assert reason == "ok"

    def test_zero_resolution(self):
        ok, reason = _validate_resolution(0.0)
        assert ok is True

    def test_negative_resolution(self):
        ok, reason = _validate_resolution(-0.5)
        assert ok is False
        assert "must be >=" in reason

    def test_too_large_resolution(self):
        ok, reason = _validate_resolution(200.0)
        assert ok is False
        assert "must be <=" in reason

    def test_non_numeric_resolution(self):
        ok, reason = _validate_resolution("high")
        assert ok is False
        assert "must be a number" in reason

    def test_nan_resolution(self):
        ok, reason = _validate_resolution(float("nan"))
        assert ok is False
        assert "finite" in reason

    def test_inf_resolution(self):
        ok, reason = _validate_resolution(float("inf"))
        assert ok is False
        assert "finite" in reason


class TestValidateNNeighbors:
    def test_valid_n_neighbors(self):
        ok, reason = _validate_n_neighbors(15)
        assert ok is True

    def test_zero_n_neighbors(self):
        ok, reason = _validate_n_neighbors(0)
        assert ok is False
        assert "must be >=" in reason

    def test_negative_n_neighbors(self):
        ok, reason = _validate_n_neighbors(-1)
        assert ok is False

    def test_too_large_n_neighbors(self):
        ok, reason = _validate_n_neighbors(20000)
        assert ok is False
        assert "must be <=" in reason

    def test_float_n_neighbors(self):
        ok, reason = _validate_n_neighbors(15.5)
        assert ok is False
        assert "must be an integer" in reason

    def test_bool_n_neighbors(self):
        ok, reason = _validate_n_neighbors(True)
        assert ok is False
        assert "must be an integer" in reason


class TestValidateAdataPayload:
    def test_valid_payload(self):
        ok, reason, data = _validate_adata_payload(_make_adata_json())
        assert ok is True
        assert data["n_obs"] == 100

    def test_malformed_json(self):
        ok, reason, data = _validate_adata_payload("{not valid json")
        assert ok is False
        assert "not valid JSON" in reason

    def test_non_string_input(self):
        ok, reason, data = _validate_adata_payload(12345)
        assert ok is False
        assert "must be a JSON string" in reason

    def test_missing_n_obs(self):
        payload = json.dumps({"n_vars": 50, "is_normalized": True})
        ok, reason, data = _validate_adata_payload(payload)
        assert ok is False
        assert "missing 'n_obs'" in reason

    def test_missing_n_vars(self):
        payload = json.dumps({"n_obs": 100, "is_normalized": True})
        ok, reason, data = _validate_adata_payload(payload)
        assert ok is False
        assert "missing 'n_vars'" in reason

    def test_not_normalized(self):
        ok, reason, data = _validate_adata_payload(_make_adata_json(is_normalized=False))
        assert ok is False
        assert "must be normalized" in reason

    def test_disallowed_keys(self):
        ok, reason, data = _validate_adata_payload(_make_adata_json(secret_key="bad"))
        assert ok is False
        assert "disallowed keys" in reason

    def test_negative_n_obs(self):
        ok, reason, data = _validate_adata_payload(_make_adata_json(n_obs=-5))
        assert ok is False
        assert "non-negative integer" in reason

    def test_json_array_not_object(self):
        ok, reason, data = _validate_adata_payload("[1, 2, 3]")
        assert ok is False
        assert "must be an object" in reason


class TestBuildClusteringConfig:
    def test_config_structure(self):
        adata_info = {"n_obs": 100, "n_vars": 50}
        config = _build_clustering_config(1.0, 15, adata_info)
        assert config["algorithm"] == "leiden"
        assert config["resolution"] == 1.0
        assert config["n_neighbors"] == 15
        assert config["n_obs"] == 100
        assert config["n_vars"] == 50
        assert config["output_key"] == "leiden"


class TestEstimateNClusters:
    def test_zero_cells(self):
        assert _estimate_n_clusters(1.0, 0) == 0

    def test_small_dataset(self):
        est = _estimate_n_clusters(1.0, 10)
        assert est >= 1
        assert est <= 10

    def test_higher_resolution_more_clusters(self):
        est_low = _estimate_n_clusters(0.5, 1000)
        est_high = _estimate_n_clusters(5.0, 1000)
        assert est_high >= est_low

    def test_large_dataset(self):
        est = _estimate_n_clusters(1.0, 10000)
        assert est >= 1
        assert est <= 10000


class TestPSNScRNA_ClusterNode:
    def setup_method(self):
        self.node = PSN_ScRNA_Cluster()

    def test_valid_input(self):
        adata = _make_adata_json(n_obs=100, n_vars=50)
        config_str, est_clusters, status = self.node.run(adata, 1.0, 15)
        assert status == "ok"
        config = json.loads(config_str)
        assert config["algorithm"] == "leiden"
        assert config["resolution"] == 1.0
        assert config["n_neighbors"] == 15
        assert est_clusters >= 1

    def test_invalid_resolution(self):
        adata = _make_adata_json()
        config_str, est_clusters, status = self.node.run(adata, -1.0, 15)
        assert status.startswith("error:")
        assert est_clusters == 0
        config = json.loads(config_str)
        assert "error" in config

    def test_invalid_n_neighbors(self):
        adata = _make_adata_json()
        config_str, est_clusters, status = self.node.run(adata, 1.0, 0)
        assert status.startswith("error:")
        assert est_clusters == 0

    def test_invalid_adata(self):
        config_str, est_clusters, status = self.node.run("not json", 1.0, 15)
        assert status.startswith("error:")
        assert est_clusters == 0

    def test_zero_cells(self):
        adata = _make_adata_json(n_obs=0, n_vars=50)
        config_str, est_clusters, status = self.node.run(adata, 1.0, 15)
        assert status == "ok"
        assert est_clusters == 0

    def test_large_resolution_edge(self):
        adata = _make_adata_json(n_obs=1000, n_vars=200)
        config_str, est_clusters, status = self.node.run(adata, 100.0, 100)
        assert status == "ok"
        config = json.loads(config_str)
        assert config["resolution"] == 100.0
        assert est_clusters >= 1

    def test_return_types_match(self):
        adata = _make_adata_json()
        result = self.node.run(adata, 1.0, 15)
        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)
        assert isinstance(result[2], str)

    def test_input_types_structure(self):
        it = PSN_ScRNA_Cluster.INPUT_TYPES()
        assert "required" in it
        assert "adata_norm" in it["required"]
        assert "resolution" in it["required"]
        assert "n_neighbors" in it["required"]
        assert it["required"]["resolution"][0] == "FLOAT"
        assert it["required"]["n_neighbors"][0] == "INT"
        assert it["required"]["adata_norm"][0] == "STRING"

    def test_return_names(self):
        assert PSN_ScRNA_Cluster.RETURN_NAMES == ("clustering_config", "estimated_n_clusters", "status")
        assert PSN_ScRNA_Cluster.RETURN_TYPES == ("STRING", "INT", "STRING")
        assert PSN_ScRNA_Cluster.FUNCTION == "run"
        assert PSN_ScRNA_Cluster.CATEGORY == "ParametricStudio/SingleCell"
