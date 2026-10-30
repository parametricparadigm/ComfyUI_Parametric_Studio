import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required
torch.manual_seed(0)

# Simulate two 4-dimensional feature vectors representing image and prompt embeddings
# Vector A: Image features
vec_a = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float32)
# Vector B: Prompt features (perfect match)
vec_b = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float32)
# Vector C: Prompt features (orthogonal/mismatch)
vec_c = torch.tensor([0.0, 1.0, 0.0, 0.0], dtype=torch.float32)

# Function to compute cosine similarity between two vectors
def cosine_similarity(v1, v2):
    # Compute dot product
    dot_product = torch.dot(v1, v2)
    # Compute norms of each vector
    norm_v1 = torch.norm(v1)
    norm_v2 = torch.norm(v2)
    # Return cosine similarity
    return dot_product / (norm_v1 * norm_v2)

# Calculate similarity for matching vectors
sim_match = cosine_similarity(vec_a, vec_b).item()
# Calculate similarity for mismatching (orthogonal) vectors
sim_mismatch = cosine_similarity(vec_a, vec_c).item()

# Print results in the required format
print(f"RESULT sim_match = {sim_match:.6g}")
print(f"RESULT sim_mismatch = {sim_mismatch:.6g}")

# Assert that perfect alignment yields a similarity of 1.0
assert abs(sim_match - 1.0) < 1e-6, "Perfect match should have cosine similarity 1.0"

# Assert that orthogonal vectors yield a similarity of 0.0
assert abs(sim_mismatch - 0.0) < 1e-6, "Orthogonal vectors should have cosine similarity 0.0"
