import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required
torch.manual_seed(0)

# Define a small latent dimension for CPU-only lab
latent_dim = 4

# Generate a random original "pixel" space tensor
original = torch.randn(latent_dim)

# Simulate compression by scaling down (analogous to VAE encoder)
compressed = original * 0.5

# Simulate reconstruction by scaling back up (analogous to VAE decoder)
reconstructed = compressed * 2.0

# Print results in the required format
print(f"RESULT original = {original.tolist()}")
print(f"RESULT compressed = {compressed.tolist()}")
print(f"RESULT reconstructed = {reconstructed.tolist()}")

# Check that the linear compression is reversible
assert torch.allclose(original, reconstructed, atol=1e-5), "Latent compression should be reversible in this linear model"

# Check that the compressed latent space has lower magnitude than the original
assert compressed.abs().max() < original.abs().max(), "Latent space should generally have lower magnitude than pixel space in this simplified scaling model"
