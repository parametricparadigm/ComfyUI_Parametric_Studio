"""
Tests for PSN_ScRNA_to_Latent node.
"""

import json
import math
import pytest
from psn_nodes.gen.psn_scrna_to_latent import (
    PSN_ScRNA_to_Latent,
    _encode_cluster_profile,
    _compute_cluster_stats,
    _deterministic_random_projection,
    ALLOWED_LATENT_DIMS,
    MAX_GENES,
    MAX_CLUSTER_ID
)


def make_adata_json(clusters: dict) -> str:
    """Helper to create adata JSON string from a clusters dict."""
    return json.dumps({"clusters": clusters})


class TestPSNScRNAtoLatent:
    """Tests for the PSN_ScRNA_to_Latent node."""
    
    def test_basic_run(self):
        """Test basic execution with valid inputs."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, 2.0, 3.0, 4.0, 5.0]},
            "1": {"genes": [0.5, 1.5, 2.5]}
        })
        latent, metadata = node.run(adata, 0, 4)
        
        # Verify latent vector has correct dimension
        assert len(latent) == 4
        # Verify all values are finite
        for v in latent:
            assert math.isfinite(v)
        # Verify metadata is valid JSON
        meta = json.loads(metadata)
        assert meta["cluster_id"] == 0
        assert meta["latent_dim"] == 4
        assert meta["stats"]["num_genes"] == 5
    
    def test_output_shape_matches_latent_dim(self):
        """Verify output shape matches latent_dim for various dimensions."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]}
        })
        
        for dim in [4, 8, 16, 32]:
            latent, _ = node.run(adata, 0, dim)
            assert len(latent) == dim, f"Expected dim {dim}, got {len(latent)}"
    
    def test_no_nans_in_output(self):
        """Verify no NaNs in output for various inputs."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [0.0, 1.0, 2.0, 3.0, 4.0]},
            "1": {"genes": [10.0, 20.0, 30.0]},
            "2": {"genes": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]}
        })
        
        for cluster_id in [0, 1, 2]:
            for dim in [4, 8, 16]:
                latent, _ = node.run(adata, cluster_id, dim)
                for v in latent:
                    assert not math.isnan(v), f"NaN found in latent for cluster {cluster_id}, dim {dim}"
                    assert not math.isinf(v), f"Inf found in latent for cluster {cluster_id}, dim {dim}"
    
    def test_invalid_json_input(self):
        """Test that invalid JSON raises an error."""
        node = PSN_ScRNA_to_Latent()
        with pytest.raises(ValueError, match="Invalid JSON"):
            node.run("not valid json", 0, 4)
    
    def test_missing_cluster(self):
        """Test that missing cluster raises an error."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, 2.0, 3.0]}
        })
        with pytest.raises(ValueError, match="Cluster 5 not found"):
            node.run(adata, 5, 4)
    
    def test_invalid_gene_values(self):
        """Test that non-numeric gene values raise an error."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, "two", 3.0]}
        })
        with pytest.raises(ValueError, match="must be a number"):
            node.run(adata, 0, 4)
    
    def test_nan_gene_values(self):
        """Test that NaN gene values raise an error."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, float('nan'), 3.0]}
        })
        with pytest.raises(ValueError, match="NaN or Inf"):
            node.run(adata, 0, 4)
    
    def test_empty_genes(self):
        """Test that empty gene list produces zero latent vector."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": []}
        })
        latent, metadata = node.run(adata, 0, 4)
        assert len(latent) == 4
        # All values should be 0.0 for empty input
        for v in latent:
            assert v == 0.0
    
    def test_single_gene(self):
        """Test with a single gene value."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [5.0]}
        })
        latent, metadata = node.run(adata, 0, 4)
        assert len(latent) == 4
        for v in latent:
            assert math.isfinite(v)
    
    def test_deterministic_output(self):
        """Test that the same input produces the same output (deterministic)."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, 2.0, 3.0, 4.0]}
        })
        latent1, _ = node.run(adata, 0, 4, seed=42)
        latent2, _ = node.run(adata, 0, 4, seed=42)
        assert latent1 == latent2, "Output should be deterministic with same seed"
        
        # Different seed should produce different output
        latent3, _ = node.run(adata, 0, 4, seed=123)
        assert latent1 != latent3, "Different seeds should produce different outputs"
    
    def test_cluster_stats(self):
        """Test that cluster statistics are computed correctly."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, 2.0, 3.0, 4.0, 5.0]}
        })
        _, metadata = node.run(adata, 0, 4)
        meta = json.loads(metadata)
        stats = meta["stats"]
        assert stats["num_genes"] == 5
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["min"] == pytest.approx(1.0)
        assert stats["max"] == pytest.approx(5.0)
        assert stats["median"] == pytest.approx(3.0)
    
    def test_invalid_latent_dim(self):
        """Test that invalid latent_dim raises an error."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, 2.0, 3.0]}
        })
        with pytest.raises(ValueError, match="latent_dim must be between"):
            node.run(adata, 0, 0)
        with pytest.raises(ValueError, match="latent_dim must be between"):
            node.run(adata, 0, 2048)
    
    def test_invalid_cluster_id(self):
        """Test that invalid cluster_id raises an error."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1.0, 2.0, 3.0]}
        })
        with pytest.raises(ValueError, match="cluster_id must be between"):
            node.run(adata, -1, 4)
        with pytest.raises(ValueError, match="cluster_id must be between"):
            node.run(adata, MAX_CLUSTER_ID + 1, 4)
    
    def test_too_many_genes(self):
        """Test that too many genes raises an error."""
        node = PSN_ScRNA_to_Latent()
        # Create a cluster with more than MAX_GENES genes
        many_genes = [1.0] * (MAX_GENES + 1)
        adata = make_adata_json({
            "0": {"genes": many_genes}
        })
        with pytest.raises(ValueError, match="Too many genes"):
            node.run(adata, 0, 4)
    
    def test_non_dict_clusters(self):
        """Test that non-dict clusters raises an error."""
        node = PSN_ScRNA_to_Latent()
        adata = json.dumps({"clusters": [1, 2, 3]})
        with pytest.raises(ValueError, match="must be a JSON object"):
            node.run(adata, 0, 4)
    
    def test_non_dict_cluster_data(self):
        """Test that non-dict cluster data raises an error."""
        node = PSN_ScRNA_to_Latent()
        adata = json.dumps({"clusters": {"0": [1.0, 2.0, 3.0]}})
        with pytest.raises(ValueError, match="must be a JSON object"):
            node.run(adata, 0, 4)
    
    def test_non_list_genes(self):
        """Test that non-list genes raises an error."""
        node = PSN_ScRNA_to_Latent()
        adata = json.dumps({"clusters": {"0": {"genes": "not a list"}}})
        with pytest.raises(ValueError, match="must be a JSON array"):
            node.run(adata, 0, 4)
    
    def test_all_same_gene_values(self):
        """Test with all gene values being the same."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [5.0, 5.0, 5.0, 5.0]}
        })
        latent, metadata = node.run(adata, 0, 4)
        assert len(latent) == 4
        for v in latent:
            assert math.isfinite(v)
    
    def test_negative_gene_values(self):
        """Test with negative gene values."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [-1.0, -2.0, -3.0, -4.0]}
        })
        latent, metadata = node.run(adata, 0, 4)
        assert len(latent) == 4
        for v in latent:
            assert math.isfinite(v)
    
    def test_large_gene_values(self):
        """Test with very large gene values."""
        node = PSN_ScRNA_to_Latent()
        adata = make_adata_json({
            "0": {"genes": [1e6, 2e6, 3e6, 4e6]}
        })
        latent, metadata = node.run(adata, 0, 4)
        assert len(latent) == 4
        for v in latent:
            assert math.isfinite(v)
    
    def test_input_types_structure(self):
        """Test that INPUT_TYPES has the correct structure."""
        input_types = PSN_ScRNA_to_Latent.INPUT_TYPES()
        assert "required" in input_types
        assert "optional" in input_types
        assert "adata_clustered" in input_types["required"]
        assert "cluster_id" in input_types["required"]
        assert "latent_dim" in input_types["required"]
        assert "seed" in input_types["optional"]
    
    def test_return_types(self):
        """Test that RETURN_TYPES and RETURN_NAMES are correct."""
        assert PSN_ScRNA_to_Latent.RETURN_TYPES == ("FLOAT", "STRING")
        assert PSN_ScRNA_to_Latent.RETURN_NAMES == ("bio_latent", "metadata")
        assert PSN_ScRNA_to_Latent.FUNCTION == "run"
        assert PSN_ScRNA_to_Latent.CATEGORY == "ParametricStudio/SingleCell"
