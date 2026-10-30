import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required by the lab rules
torch.manual_seed(0)

# Define small input tensor (batch_size=4, input_dim=8) and weight matrix (input_dim=8, num_experts=4)
x = torch.randn(4, 8)
W = torch.randn(8, 4)

# Compute routing logits: x @ W gives shape (4, 4)
logits = x @ W

# Convert logits to probabilities using softmax over the expert dimension
probs = torch.softmax(logits, dim=-1)

# Select top-2 experts for each sample (Top-2 routing)
topk_vals, topk_idx = torch.topk(probs, k=2, dim=-1)

# Print results in the required format
print(f"RESULT topk_indices = {topk_idx.tolist()}")
print(f"RESULT topk_values = {[f'{v:.6g}' for v in topk_vals.flatten().tolist()]}")

# Assert that the shape of topk values is correct (batch_size, k)
assert topk_vals.shape == (4, 2), "Top-2 values must have shape (4, 2)"

# Assert that all top-2 probabilities are within [0, 1]
assert (topk_vals >= 0).all() and (topk_vals <= 1).all(), "Top-2 probabilities must be in [0, 1]"
