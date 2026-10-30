"""
PSN_ScRNA_Cluster: Pure-logic validation and configuration for Leiden clustering.

This module implements the secure-by-design, pure-logic portion of a Leiden
clustering node. It does NOT perform actual clustering (which would require
scanpy, leidenalg, and GPU/CPU heavy computation). Instead, it validates
inputs, checks configuration constraints, and prepares the payload that would
be sent to a clustering backend.

Inputs are plain values (numbers, strings, JSON text). No file I/O, no network,
no subprocess, no torch, no ComfyUI internals.
"""

import json
import math
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_RESOLUTION_MIN = 0.0
_VALID_RESOLUTION_MAX = 100.0
_VALID_N_NEIGHBORS_MIN = 1
_VALID_N_NEIGHBORS_MAX = 10000
_VALID_N_NEIGHBORS_DEFAULT = 15

# Allowed keys in the adata_norm JSON payload
_ALLOWED_ADATA_KEYS = frozenset({
    "n_obs", "n_vars", "obs_names", "var_names",
    "X_shape", "dtype", "is_normalized",
})

# Allowed obs columns that may be present
_ALLOWED_OBS_COLUMNS = frozenset({
    "cell_type", "n_counts", "percent_mito", "n_genes",
})


def _validate_resolution(resolution):
    """Validate resolution parameter. Returns (ok, reason)."""
    if not isinstance(resolution, (int, float)):
        return False, "resolution must be a number"
    if isinstance(resolution, float) and (math.isnan(resolution) or math.isinf(resolution)):
        return False, "resolution must be finite"
    if resolution < _VALID_RESOLUTION_MIN:
        return False, f"resolution must be >= {_VALID_RESOLUTION_MIN}"
    if resolution > _VALID_RESOLUTION_MAX:
        return False, f"resolution must be <= {_VALID_RESOLUTION_MAX}"
    return True, "ok"


def _validate_n_neighbors(n_neighbors):
    """Validate n_neighbors parameter. Returns (ok, reason)."""
    if not isinstance(n_neighbors, int) or isinstance(n_neighbors, bool):
        return False, "n_neighbors must be an integer"
    if n_neighbors < _VALID_N_NEIGHBORS_MIN:
        return False, f"n_neighbors must be >= {_VALID_N_NEIGHBORS_MIN}"
    if n_neighbors > _VALID_N_NEIGHBORS_MAX:
        return False, f"n_neighbors must be <= {_VALID_N_NEIGHBORS_MAX}"
    return True, "ok"


def _validate_adata_payload(adata_json):
    """
    Validate the adata_norm JSON payload.
    Returns (ok, reason, parsed_dict).
    """
    if not isinstance(adata_json, str):
        return False, "adata_norm must be a JSON string", None
    try:
        data = json.loads(adata_json)
    except (json.JSONDecodeError, TypeError):
        return False, "adata_norm is not valid JSON", None
    if not isinstance(data, dict):
        return False, "adata_norm JSON must be an object", None

    # Check required fields
    if "n_obs" not in data:
        return False, "adata_norm missing 'n_obs'", None
    if "n_vars" not in data:
        return False, "adata_norm missing 'n_vars'", None

    n_obs = data["n_obs"]
    n_vars = data["n_vars"]
    if not isinstance(n_obs, int) or isinstance(n_obs, bool) or n_obs < 0:
        return False, "n_obs must be a non-negative integer", None
    if not isinstance(n_vars, int) or isinstance(n_vars, bool) or n_vars < 0:
        return False, "n_vars must be a non-negative integer", None

    # Check for disallowed keys
    extra_keys = set(data.keys()) - _ALLOWED_ADATA_KEYS
    if extra_keys:
        return False, f"adata_norm contains disallowed keys: {sorted(extra_keys)}", None

    # Check is_normalized flag
    if "is_normalized" in data and not data["is_normalized"]:
        return False, "adata_norm must be normalized (is_normalized=true)", None

    return True, "ok", data


def _build_clustering_config(resolution, n_neighbors, adata_info):
    """
    Build the clustering configuration payload.
    Returns a dict that would be sent to the backend.
    """
    return {
        "algorithm": "leiden",
        "resolution": float(resolution),
        "n_neighbors": int(n_neighbors),
        "n_obs": adata_info["n_obs"],
        "n_vars": adata_info["n_vars"],
        "output_key": "leiden",
    }


def _estimate_n_clusters(resolution, n_obs):
    """
    Heuristic estimate of expected number of clusters.
    This is a pure-logic approximation for validation/testing purposes.
    """
    if n_obs <= 0:
        return 0
    # Rough heuristic: higher resolution -> more clusters
    base = max(1, int(math.log2(n_obs)))
    estimated = max(1, int(base * (1.0 + resolution * 0.5)))
    return min(estimated, n_obs)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/SingleCell"


class PSN_ScRNA_Cluster:
    """
    Validates and prepares configuration for Leiden clustering on normalized
    single-cell RNA-seq data.

    This node does NOT perform clustering. It validates inputs, checks that
    the AnnData payload is well-formed and normalized, and outputs a
    clustering configuration dict along with an estimated cluster count.

    The actual clustering (sc.pp.neighbors + sc.tl.leiden) must be performed
    by a separate backend that receives the configuration payload.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "adata_norm": ("STRING", {
                    "multiline": True,
                    "default": '{"n_obs": 100, "n_vars": 50, "is_normalized": true}',
                    "tooltip": "JSON string representing the normalized AnnData object. "
                               "Must contain n_obs, n_vars, and is_normalized=true.",
                }),
                "resolution": ("FLOAT", {
                    "default": 1.0,
                    "min": _VALID_RESOLUTION_MIN,
                    "max": _VALID_RESOLUTION_MAX,
                    "step": 0.01,
                    "tooltip": "Clustering resolution. Higher values produce more clusters.",
                }),
                "n_neighbors": ("INT", {
                    "default": _VALID_N_NEIGHBORS_DEFAULT,
                    "min": _VALID_N_NEIGHBORS_MIN,
                    "max": _VALID_N_NEIGHBORS_MAX,
                    "step": 1,
                    "tooltip": "Number of neighbors for graph construction.",
                }),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("clustering_config", "estimated_n_clusters", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, adata_norm, resolution, n_neighbors):
        """
        Validate inputs and produce a clustering configuration payload.

        Returns:
            clustering_config (str): JSON string with the clustering parameters.
            estimated_n_clusters (int): Heuristic estimate of cluster count.
            status (str): "ok" or an error message.
        """
        # Validate resolution
        ok_res, why_res = _validate_resolution(resolution)
        if not ok_res:
            return (json.dumps({"error": why_res}), 0, f"error: {why_res}")

        # Validate n_neighbors
        ok_nn, why_nn = _validate_n_neighbors(n_neighbors)
        if not ok_nn:
            return (json.dumps({"error": why_nn}), 0, f"error: {why_nn}")

        # Validate adata payload
        ok_adata, why_adata, adata_info = _validate_adata_payload(adata_norm)
        if not ok_adata:
            return (json.dumps({"error": why_adata}), 0, f"error: {why_adata}")

        # Build config
        config = _build_clustering_config(resolution, n_neighbors, adata_info)
        config_json = json.dumps(config, sort_keys=True)

        # Estimate clusters
        est = _estimate_n_clusters(resolution, adata_info["n_obs"])

        return (config_json, est, "ok")


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ScRNA_Cluster": PSN_ScRNA_Cluster,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ScRNA_Cluster": "PSN ScRNA Cluster (Leiden Config)",
}
