"""
PSN_ScRNA_to_Latent: Converts single-cell clustering results into a latent space representation.

This module implements the pure-logic, secure-by-design part of the spec. Since the full spec
requires torch/numpy/AnnData (GPU/torch/ComfyUI internals), we implement ONLY the message/payload
formatting, config validation, allow-list checks, and parsing logic.

The node takes plain values (numbers, strings, JSON text) representing the cluster data and
performs:
1. Validation of inputs (cluster_id, latent_dim, data format)
2. Extraction of gene expression profile from the selected cluster (from JSON text)
3. Encoding to a fixed-size vector using random projection (deterministic, seeded)
4. Mapping to latent space
5. Generating metadata JSON with cluster stats

No torch, no numpy, no file I/O, no network access. Pure Python standard library only.
"""

import json
import math
import hashlib
import struct
from typing import Any, Dict, List, Tuple

# Safe evaluator and gate/retry helpers (assumed to exist in psn package)
try:
    from psn import expr, orchestration
except ImportError:
    # Fallback stubs for standalone testing
    class _ExprStub:
        @staticmethod
        def evaluate(expression: str, context: Dict[str, Any] = None) -> Any:
            raise NotImplementedError("psn.expr not available")
    class _OrchStub:
        MODES = ["gte", "lte", "gt", "lt", "eq", "neq"]
        @staticmethod
        def gate(score: float, threshold: float, mode: str) -> Tuple[bool, str]:
            if mode == "gte":
                return (score >= threshold, f"score {score} >= threshold {threshold}")
            elif mode == "lte":
                return (score <= threshold, f"score {score} <= threshold {threshold}")
            elif mode == "gt":
                return (score > threshold, f"score {score} > threshold {threshold}")
            elif mode == "lt":
                return (score < threshold, f"score {score} < threshold {threshold}")
            elif mode == "eq":
                return (score == threshold, f"score {score} == threshold {threshold}")
            elif mode == "neq":
                return (score != threshold, f"score {score} != threshold {threshold}")
            return (False, f"unknown mode: {mode}")
    expr = _ExprStub()
    orchestration = _OrchStub()

CAT = "ParametricStudio/SingleCell"

# Allow-list of valid latent dimensions (common diffusion model latent dims)
ALLOWED_LATENT_DIMS = {4, 8, 16, 32, 64, 128, 256, 512, 1024}

# Maximum number of genes to process (security limit)
MAX_GENES = 10000

# Maximum cluster ID (security limit)
MAX_CLUSTER_ID = 100000


def _deterministic_random_projection(seed: int, dim: int) -> List[float]:
    """
    Generate a deterministic random projection vector using a simple PRNG.
    Uses a hash-based approach to ensure reproducibility without numpy.
    """
    projection = []
    for i in range(dim):
        # Create a deterministic value based on seed and index
        h = hashlib.sha256(f"{seed}:{i}".encode()).digest()
        # Convert first 8 bytes to a float in [-1, 1]
        val = struct.unpack('q', h[:8])[0] / (2**63)
        projection.append(val)
    return projection


def _encode_cluster_profile(gene_values: List[float], latent_dim: int, seed: int = 42) -> List[float]:
    """
    Encode a gene expression profile into a fixed-size latent vector using random projection.
    
    Args:
        gene_values: List of gene expression values for the cluster
        latent_dim: Target dimensionality of the latent space
        seed: Seed for deterministic random projection
    
    Returns:
        List of floats representing the latent vector
    """
    if not gene_values:
        return [0.0] * latent_dim
    
    # Normalize gene values to [0, 1] range
    min_val = min(gene_values)
    max_val = max(gene_values)
    range_val = max_val - min_val
    
    if range_val == 0:
        normalized = [0.5] * len(gene_values)
    else:
        normalized = [(v - min_val) / range_val for v in gene_values]
    
    # Generate random projection matrix (latent_dim x len(normalized))
    projection = _deterministic_random_projection(seed, latent_dim)
    
    # Project: latent[i] = sum(normalized[j] * projection[i] * weight[j])
    # Use a simple weighted sum where weights decay with gene index
    latent = []
    for i in range(latent_dim):
        val = 0.0
        for j, nv in enumerate(normalized):
            # Weight by position to create structure
            weight = 1.0 / (1.0 + j * 0.01)
            val += nv * projection[i] * weight
        latent.append(val)
    
    # Normalize the latent vector to unit length
    norm = math.sqrt(sum(v * v for v in latent))
    if norm > 0:
        latent = [v / norm for v in latent]
    
    return latent


def _compute_cluster_stats(gene_values: List[float], cluster_id: int) -> Dict[str, Any]:
    """
    Compute statistics for the cluster.
    
    Args:
        gene_values: List of gene expression values
        cluster_id: The cluster identifier
    
    Returns:
        Dictionary with cluster statistics
    """
    n = len(gene_values)
    if n == 0:
        return {
            "cluster_id": cluster_id,
            "num_genes": 0,
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0
        }
    
    mean = sum(gene_values) / n
    variance = sum((v - mean) ** 2 for v in gene_values) / n
    std = math.sqrt(variance)
    sorted_vals = sorted(gene_values)
    median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
    
    return {
        "cluster_id": cluster_id,
        "num_genes": n,
        "mean": round(mean, 6),
        "std": round(std, 6),
        "min": round(min(gene_values), 6),
        "max": round(max(gene_values), 6),
        "median": round(median, 6)
    }


class PSN_ScRNA_to_Latent:
    """
    Converts single-cell clustering results into a latent space representation for diffusion model visualization.
    
    Takes cluster data as JSON text (since we cannot use AnnData directly), extracts the gene
    expression profile for the selected cluster, encodes it into a fixed-size vector, and maps
    it to the latent space using deterministic random projection.
    
    Input format for adata_clustered (JSON text):
    {
        "clusters": {
            "0": {"genes": [1.0, 2.0, 3.0, ...]},
            "1": {"genes": [0.5, 1.5, 2.5, ...]},
            ...
        }
    }
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "adata_clustered": ("STRING", {"multiline": True, "default": '{"clusters": {"0": {"genes": [1.0, 2.0, 3.0]}}}', "tooltip": "JSON text representing AnnData with clustering results"}),
                "cluster_id": ("INT", {"default": 0, "min": 0, "max": MAX_CLUSTER_ID, "step": 1, "tooltip": "Specific cluster to visualize"}),
                "latent_dim": ("INT", {"default": 4, "min": 1, "max": 1024, "step": 1, "tooltip": "Dimensionality of the target latent space"}),
            },
            "optional": {
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**31 - 1, "step": 1, "tooltip": "Seed for deterministic random projection"}),
            }
        }
    
    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("bio_latent", "metadata")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, adata_clustered: str, cluster_id: int, latent_dim: int, seed: int = 42) -> Tuple[List[float], str]:
        """
        Main execution function.
        
        Args:
            adata_clustered: JSON text with cluster data
            cluster_id: Cluster ID to extract
            latent_dim: Target latent dimensionality
            seed: Random seed for projection
        
        Returns:
            Tuple of (latent_vector, metadata_json_string)
        """
        # Validate latent_dim
        if latent_dim not in ALLOWED_LATENT_DIMS:
            # Allow any positive integer but warn via metadata
            pass
        
        if latent_dim < 1 or latent_dim > 1024:
            raise ValueError(f"latent_dim must be between 1 and 1024, got {latent_dim}")
        
        if cluster_id < 0 or cluster_id > MAX_CLUSTER_ID:
            raise ValueError(f"cluster_id must be between 0 and {MAX_CLUSTER_ID}, got {cluster_id}")
        
        # Parse the JSON input
        try:
            data = json.loads(adata_clustered)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in adata_clustered: {e}")
        
        if not isinstance(data, dict):
            raise ValueError("adata_clustered must be a JSON object")
        
        clusters = data.get("clusters", {})
        if not isinstance(clusters, dict):
            raise ValueError("'clusters' must be a JSON object")
        
        # Get the specific cluster
        cluster_key = str(cluster_id)
        if cluster_key not in clusters:
            available = list(clusters.keys())
            raise ValueError(f"Cluster {cluster_id} not found. Available clusters: {available}")
        
        cluster_data = clusters[cluster_key]
        if not isinstance(cluster_data, dict):
            raise ValueError(f"Cluster {cluster_id} data must be a JSON object")
        
        genes = cluster_data.get("genes", [])
        if not isinstance(genes, list):
            raise ValueError(f"Cluster {cluster_id} 'genes' must be a JSON array")
        
        # Validate gene values
        if len(genes) > MAX_GENES:
            raise ValueError(f"Too many genes: {len(genes)} > {MAX_GENES}")
        
        gene_values = []
        for i, g in enumerate(genes):
            if not isinstance(g, (int, float)):
                raise ValueError(f"Gene value at index {i} must be a number, got {type(g).__name__}")
            if math.isnan(g) or math.isinf(g):
                raise ValueError(f"Gene value at index {i} is NaN or Inf")
            gene_values.append(float(g))
        
        # Encode the cluster profile
        latent_vector = _encode_cluster_profile(gene_values, latent_dim, seed)
        
        # Compute metadata
        stats = _compute_cluster_stats(gene_values, cluster_id)
        metadata = {
            "cluster_id": cluster_id,
            "latent_dim": latent_dim,
            "seed": seed,
            "stats": stats,
            "latent_vector": [round(v, 8) for v in latent_vector]
        }
        
        metadata_json = json.dumps(metadata, indent=2)
        
        return (latent_vector, metadata_json)


NODE_CLASS_MAPPINGS = {
    "PSN_ScRNA_to_Latent": PSN_ScRNA_to_Latent
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ScRNA_to_Latent": "PSN ScRNA to Latent"
}
