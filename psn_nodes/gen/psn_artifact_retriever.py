"""
PSN_Artifact_Retriever: A pure-logic, secure-by-design node for simulating artifact retrieval.

This module implements the core logic for retrieving similar artifacts based on a query.
Since actual vector database operations (ChromaDB, FAISS) and embedding models (sentence-transformers)
require external dependencies and GPU access, this node implements a deterministic, in-memory
simulator using pure Python standard library.

It accepts plain values (strings, numbers, JSON text) and performs:
1. Input validation (collection name, top_k, query).
2. Deterministic "embedding" simulation using a simple hash-based vector.
3. Cosine similarity calculation between query and stored artifacts.
4. Ranking and returning top-k results with scores.

No network, file, or OS access is performed. All data is passed via function arguments.
"""

import json
import math
import hashlib
from typing import Any, List, Dict, Tuple

# Simulated in-memory vector store. In a real scenario, this would be a database.
# For this node, we maintain a static set of test artifacts to ensure deterministic behavior.
# In a real ComfyUI setup, this would likely be a global state or passed via a separate node.
# Here, we use a module-level dictionary to simulate the "database".

_PSN_ARTIFACT_STORE: Dict[str, List[Dict[str, Any]]] = {
    "default_collection": [
        {
            "id": "art_001",
            "metadata": {"title": "Red Square", "tags": ["color", "red", "shape"]},
            "vector": [1.0, 0.0, 0.0]
        },
        {
            "id": "art_002",
            "metadata": {"title": "Blue Circle", "tags": ["color", "blue", "shape"]},
            "vector": [0.0, 1.0, 0.0]
        },
        {
            "id": "art_003",
            "metadata": {"title": "Green Triangle", "tags": ["color", "green", "shape"]},
            "vector": [0.0, 0.0, 1.0]
        },
        {
            "id": "art_004",
            "metadata": {"title": "Red Circle", "tags": ["color", "red", "shape"]},
            "vector": [1.0, 1.0, 0.0]
        },
        {
            "id": "art_005",
            "metadata": {"title": "Blue Square", "tags": ["color", "blue", "shape"]},
            "vector": [1.0, -1.0, 0.0]
        }
    ],
    "empty_collection": []
}


def _psn_simulate_embedding(text: str) -> List[float]:
    """
    Simulates an embedding vector from a text string.
    Uses a deterministic hash to generate a 3-dimensional vector.
    This is a placeholder for actual embedding models.
    """
    if not text:
        return [0.0, 0.0, 0.0]
    
    # Use MD5 hash to generate deterministic pseudo-random values
    hash_obj = hashlib.md5(text.encode('utf-8')).digest()
    
    # Take first 3 bytes and normalize to [-1, 1]
    vec = []
    for i in range(3):
        # Map byte value (0-255) to [-1, 1]
        val = (hash_obj[i] / 255.0) * 2.0 - 1.0
        vec.append(val)
    
    return vec


def _psn_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculates cosine similarity between two vectors.
    Returns 0.0 if either vector is zero.
    """
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


class PSN_Artifact_Retriever:
    """
    Retrieves similar artifacts from a simulated vector database based on a query.
    
    Inputs:
        query (STRING): Text prompt for similarity search.
        collection_name (STRING): Name of the vector collection.
        top_k (INT): Number of results to return.
    
    Outputs:
        artifacts (LIST): List of similar artifacts with metadata.
        scores (LIST): Similarity scores.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "query": ("STRING", {"default": "", "multiline": True}),
                "collection_name": ("STRING", {"default": "default_collection"}),
                "top_k": ("INT", {"default": 3, "min": 1, "max": 100, "step": 1})
            },
            "optional": {}
        }
    
    RETURN_TYPES = ("LIST", "LIST")
    RETURN_NAMES = ("artifacts", "scores")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Retrieval"
    
    def run(self, query: str, collection_name: str, top_k: int) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Retrieves similar artifacts from the simulated vector database.
        
        Args:
            query: Text query for similarity search.
            collection_name: Name of the collection to search.
            top_k: Number of top results to return.
        
        Returns:
            Tuple of (artifacts, scores) where artifacts is a list of dicts
            and scores is a list of floats.
        """
        # Validate inputs
        if not isinstance(query, str):
            raise ValueError("Query must be a string")
        
        if not isinstance(collection_name, str):
            raise ValueError("Collection name must be a string")
        
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("Top_k must be a positive integer")
        
        # Get the collection
        if collection_name not in _PSN_ARTIFACT_STORE:
            return ([], [])
        
        collection = _PSN_ARTIFACT_STORE[collection_name]
        
        if not collection:
            return ([], [])
        
        # Simulate embedding of the query
        query_vector = _psn_simulate_embedding(query)
        
        # Calculate similarity scores for all artifacts
        scored_artifacts = []
        for artifact in collection:
            artifact_vector = artifact.get("vector", [0.0, 0.0, 0.0])
            score = _psn_cosine_similarity(query_vector, artifact_vector)
            scored_artifacts.append((artifact, score))
        
        # Sort by score in descending order
        scored_artifacts.sort(key=lambda x: x[1], reverse=True)
        
        # Get top_k results
        top_results = scored_artifacts[:top_k]
        
        # Separate artifacts and scores
        artifacts = [art for art, _ in top_results]
        scores = [score for _, score in top_results]
        
        return (artifacts, scores)


NODE_CLASS_MAPPINGS = {
    "PSN_Artifact_Retriever": PSN_Artifact_Retriever
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Artifact_Retriever": "PSN Artifact Retriever"
}
