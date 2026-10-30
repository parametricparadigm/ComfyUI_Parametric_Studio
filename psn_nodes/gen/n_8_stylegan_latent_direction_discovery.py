"""Pure-logic StyleGAN latent direction discovery and application.

This module implements the mathematical core of unsupervised latent direction
discovery (PCA) and direction application for StyleGAN-style latent vectors.
It uses only the Python standard library (math, json, random) and does NOT
import torch, numpy, or any ComfyUI internals. Latent vectors are represented
as plain Python lists of floats.

Nodes:
  - PSN_StyleGAN_Direction_Discover: PCA on a batch of latents to find principal directions.
  - PSN_StyleGAN_Direction_Apply: Project a latent onto a direction vector and scale it.

Data flow: Latent Batch -> PSN_StyleGAN_Direction_Discover -> PSN_StyleGAN_Direction_Apply -> Sampler
"""

import math
import json
import random

CAT = "ParametricStudio/StyleGAN"


def _validate_latent(latent, name="latent"):
    """Validate that a latent is a list of finite numbers."""
    if not isinstance(latent, list):
        raise ValueError(f"{name} must be a list, got {type(latent).__name__}")
    if len(latent) == 0:
        raise ValueError(f"{name} must be non-empty")
    for i, v in enumerate(latent):
        if not isinstance(v, (int, float)):
            raise ValueError(f"{name}[{i}] must be a number, got {type(v).__name__}")
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValueError(f"{name}[{i}] must be finite, got {v}")
    return latent


def _validate_latent_batch(batch, name="latent_batch"):
    """Validate that a latent batch is a list of latents with consistent dimensions."""
    if not isinstance(batch, list):
        raise ValueError(f"{name} must be a list of latents, got {type(batch).__name__}")
    if len(batch) == 0:
        raise ValueError(f"{name} must be non-empty")
    dim = None
    for i, lat in enumerate(batch):
        _validate_latent(lat, f"{name}[{i}]")
        if dim is None:
            dim = len(lat)
        elif len(lat) != dim:
            raise ValueError(f"{name}[{i}] has dimension {len(lat)}, expected {dim}")
    return batch, dim


def _mean_vector(batch):
    """Compute the mean vector of a batch of latents."""
    n = len(batch)
    dim = len(batch[0])
    mean = [0.0] * dim
    for lat in batch:
        for j in range(dim):
            mean[j] += lat[j]
    for j in range(dim):
        mean[j] /= n
    return mean


def _covariance_matrix(batch, mean):
    """Compute the covariance matrix of a batch of latents (centered by mean)."""
    n = len(batch)
    dim = len(batch[0])
    cov = [[0.0] * dim for _ in range(dim)]
    for lat in batch:
        centered = [lat[j] - mean[j] for j in range(dim)]
        for i in range(dim):
            for j in range(dim):
                cov[i][j] += centered[i] * centered[j]
    for i in range(dim):
        for j in range(dim):
            cov[i][j] /= (n - 1) if n > 1 else 1.0
    return cov


def _power_iteration(matrix, dim, num_directions, seed, max_iter=1000, tol=1e-10):
    """
    Find the top `num_directions` eigenvectors of a symmetric matrix using
    power iteration with deflation. Returns (eigenvectors, eigenvalues).
    """
    rng = random.Random(seed)
    eigenvectors = []
    eigenvalues = []
    remaining = [row[:] for row in matrix]

    for _ in range(num_directions):
        # Initialize random vector
        v = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
        norm = math.sqrt(sum(x * x for x in v))
        if norm < 1e-12:
            v = [1.0] + [0.0] * (dim - 1)
        else:
            v = [x / norm for x in v]

        eigenvalue = 0.0
        for _ in range(max_iter):
            # Matrix-vector multiplication
            new_v = [0.0] * dim
            for i in range(dim):
                for j in range(dim):
                    new_v[i] += remaining[i][j] * v[j]

            # Rayleigh quotient for eigenvalue estimate
            eigenvalue = sum(v[i] * new_v[i] for i in range(dim))

            # Normalize
            norm = math.sqrt(sum(x * x for x in new_v))
            if norm < 1e-12:
                break
            new_v = [x / norm for x in new_v]

            # Check convergence
            diff = math.sqrt(sum((new_v[i] - v[i]) ** 2 for i in range(dim)))
            v = new_v
            if diff < tol:
                break

        # Ensure consistent sign (largest absolute component positive)
        max_idx = max(range(dim), key=lambda i: abs(v[i]))
        if v[max_idx] < 0:
            v = [-x for x in v]

        eigenvectors.append(v)
        eigenvalues.append(eigenvalue)

        # Deflate: remove this eigen-direction from the matrix
        for i in range(dim):
            for j in range(dim):
                remaining[i][j] -= eigenvalue * v[i] * v[j]

    return eigenvectors, eigenvalues


def _pca_discover(batch, num_directions, seed):
    """
    Perform PCA on a batch of latents.
    Returns (direction_vectors, eigenvalues) where direction_vectors is a list
    of lists (each inner list is a unit vector) and eigenvalues is a list of floats.
    """
    batch, dim = _validate_latent_batch(batch, "latent_batch")
    if num_directions < 1:
        raise ValueError("num_directions must be >= 1")
    if num_directions > dim:
        num_directions = dim

    mean = _mean_vector(batch)
    cov = _covariance_matrix(batch, mean)
    eigenvectors, eigenvalues = _power_iteration(cov, dim, num_directions, seed)
    return eigenvectors, eigenvalues


def _apply_direction(latent, direction, strength):
    """
    Project the latent onto the direction vector and add the scaled projection.
    modified = latent + strength * (dot(latent, direction) * direction)
    """
    _validate_latent(latent, "latent")
    _validate_latent(direction, "direction_vector")
    if len(latent) != len(direction):
        raise ValueError(f"latent and direction_vector must have the same dimension, got {len(latent)} and {len(direction)}")
    if not isinstance(strength, (int, float)):
        raise ValueError("strength must be a number")
    if isinstance(strength, float) and (math.isnan(strength) or math.isinf(strength)):
        raise ValueError("strength must be finite")

    dot = sum(latent[i] * direction[i] for i in range(len(latent)))
    modified = [latent[i] + strength * dot * direction[i] for i in range(len(latent))]
    return modified


class PSN_StyleGAN_Direction_Discover:
    """Perform PCA on a latent batch to discover principal latent directions."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_batch": ("LATENT", {"default": None}),
                "num_directions": ("INT", {"default": 5, "min": 1, "max": 1024, "step": 1}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LATENT", "FLOAT")
    RETURN_NAMES = ("direction_vectors", "eigenvalues")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent_batch, num_directions, seed):
        directions, eigenvalues = _pca_discover(latent_batch, num_directions, seed)
        return (directions, eigenvalues)


class PSN_StyleGAN_Direction_Apply:
    """Project a latent onto a direction vector and scale it."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT", {"default": None}),
                "direction_vector": ("LATENT", {"default": None}),
                "strength": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("modified_latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, direction_vector, strength):
        modified = _apply_direction(latent, direction_vector, strength)
        return (modified,)


NODE_CLASS_MAPPINGS = {
    "PSN_StyleGAN_Direction_Discover": PSN_StyleGAN_Direction_Discover,
    "PSN_StyleGAN_Direction_Apply": PSN_StyleGAN_Direction_Apply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StyleGAN_Direction_Discover": "StyleGAN Direction Discover",
    "PSN_StyleGAN_Direction_Apply": "StyleGAN Direction Apply",
}
