"""
Tests for PSN_Artifact_Retriever node.
"""

import pytest
from psn_nodes.gen.psn_artifact_retriever import (
    PSN_Artifact_Retriever,
    _psn_simulate_embedding,
    _psn_cosine_similarity,
    _PSN_ARTIFACT_STORE
)


class TestPSNArtifactRetriever:
    """Test suite for PSN_Artifact_Retriever node."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.node = PSN_Artifact_Retriever()
    
    def test_input_types_structure(self):
        """Test that INPUT_TYPES has correct structure."""
        input_types = PSN_Artifact_Retriever.INPUT_TYPES()
        
        assert "required" in input_types
        assert "query" in input_types["required"]
        assert "collection_name" in input_types["required"]
        assert "top_k" in input_types["required"]
        
        # Check types
        assert input_types["required"]["query"][0] == "STRING"
        assert input_types["required"]["collection_name"][0] == "STRING"
        assert input_types["required"]["top_k"][0] == "INT"
    
    def test_return_types_and_names(self):
        """Test that RETURN_TYPES and RETURN_NAMES are correct."""
        assert PSN_Artifact_Retriever.RETURN_TYPES == ("LIST", "LIST")
        assert PSN_Artifact_Retriever.RETURN_NAMES == ("artifacts", "scores")
        assert PSN_Artifact_Retriever.FUNCTION == "run"
        assert PSN_Artifact_Retriever.CATEGORY == "ParametricStudio/Retrieval"
    
    def test_retrieve_from_default_collection(self):
        """Test retrieving artifacts from default collection."""
        artifacts, scores = self.node.run(
            query="red shape",
            collection_name="default_collection",
            top_k=3
        )
        
        # Should return up to 3 results
        assert len(artifacts) <= 3
        assert len(scores) <= 3
        assert len(artifacts) == len(scores)
        
        # Each artifact should have id and metadata
        for artifact in artifacts:
            assert "id" in artifact
            assert "metadata" in artifact
        
        # Scores should be floats
        for score in scores:
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0
    
    def test_retrieve_from_empty_collection(self):
        """Test retrieving from an empty collection."""
        artifacts, scores = self.node.run(
            query="test",
            collection_name="empty_collection",
            top_k=5
        )
        
        assert artifacts == []
        assert scores == []
    
    def test_retrieve_from_nonexistent_collection(self):
        """Test retrieving from a nonexistent collection."""
        artifacts, scores = self.node.run(
            query="test",
            collection_name="nonexistent_collection",
            top_k=5
        )
        
        assert artifacts == []
        assert scores == []
    
    def test_top_k_limits_results(self):
        """Test that top_k limits the number of results."""
        # Request more results than available
        artifacts, scores = self.node.run(
            query="test",
            collection_name="default_collection",
            top_k=100
        )
        
        # Should return all 5 artifacts in default_collection
        assert len(artifacts) == 5
        assert len(scores) == 5
        
        # Request fewer results
        artifacts, scores = self.node.run(
            query="test",
            collection_name="default_collection",
            top_k=2
        )
        
        assert len(artifacts) == 2
        assert len(scores) == 2
    
    def test_invalid_top_k_value(self):
        """Test that invalid top_k values raise errors."""
        with pytest.raises(ValueError):
            self.node.run(
                query="test",
                collection_name="default_collection",
                top_k=0
            )
        
        with pytest.raises(ValueError):
            self.node.run(
                query="test",
                collection_name="default_collection",
                top_k=-1
            )
    
    def test_invalid_query_type(self):
        """Test that invalid query types raise errors."""
        with pytest.raises(ValueError):
            self.node.run(
                query=123,  # Not a string
                collection_name="default_collection",
                top_k=3
            )
    
    def test_invalid_collection_name_type(self):
        """Test that invalid collection name types raise errors."""
        with pytest.raises(ValueError):
            self.node.run(
                query="test",
                collection_name=123,  # Not a string
                top_k=3
            )
    
    def test_simulate_embedding_deterministic(self):
        """Test that embedding simulation is deterministic."""
        vec1 = _psn_simulate_embedding("test query")
        vec2 = _psn_simulate_embedding("test query")
        
        assert vec1 == vec2
        assert len(vec1) == 3
    
    def test_simulate_embedding_empty_string(self):
        """Test embedding simulation with empty string."""
        vec = _psn_simulate_embedding("")
        
        assert vec == [0.0, 0.0, 0.0]
    
    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity with identical vectors."""
        vec = [1.0, 2.0, 3.0]
        similarity = _psn_cosine_similarity(vec, vec)
        
        assert abs(similarity - 1.0) < 1e-6
    
    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = _psn_cosine_similarity(vec1, vec2)
        
        assert abs(similarity) < 1e-6
    
    def test_cosine_similarity_opposite_vectors(self):
        """Test cosine similarity with opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = _psn_cosine_similarity(vec1, vec2)
        
        assert abs(similarity - (-1.0)) < 1e-6
    
    def test_cosine_similarity_zero_vector(self):
        """Test cosine similarity with zero vector."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = _psn_cosine_similarity(vec1, vec2)
        
        assert similarity == 0.0
    
    def test_cosine_similarity_different_lengths(self):
        """Test cosine similarity with vectors of different lengths."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = _psn_cosine_similarity(vec1, vec2)
        
        assert similarity == 0.0
    
    def test_node_class_mappings(self):
        """Test that NODE_CLASS_MAPPINGS is correctly defined."""
        from psn_nodes.gen.psn_artifact_retriever import NODE_CLASS_MAPPINGS
        
        assert "PSN_Artifact_Retriever" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["PSN_Artifact_Retriever"] == PSN_Artifact_Retriever
    
    def test_node_display_name_mappings(self):
        """Test that NODE_DISPLAY_NAME_MAPPINGS is correctly defined."""
        from psn_nodes.gen.psn_artifact_retriever import NODE_DISPLAY_NAME_MAPPINGS
        
        assert "PSN_Artifact_Retriever" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Artifact_Retriever"] == "PSN Artifact Retriever"
