import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required by the lab rules
torch.manual_seed(0)

# Define small dimensions to ensure CPU-only execution is fast
seq_len = 10
hidden_dim = 4

# Step 1: Simulate a full attention computation over the entire sequence.
# This represents the "naive" way where we recompute attention for all tokens.
# We use random matrices to simulate Key, Value, and Query projections.
Q = torch.randn(seq_len, hidden_dim)
K = torch.randn(seq_len, hidden_dim)
V = torch.randn(seq_len, hidden_dim)

# Compute full attention scores: Q @ K^T / sqrt(d_k)
scale = math.sqrt(hidden_dim)
attn_scores = (Q @ K.T) / scale
attn_weights = torch.softmax(attn_scores, dim=-1)
full_attn_output = attn_weights @ V

# Step 2: Simulate the KV Cache mechanism.
# In autoregressive decoding, we store past K and V to avoid recomputation.
# Let's assume we have already processed 'seq_len' tokens.
cached_K = K.clone()
cached_V = V.clone()

# Step 3: Generate a new token (the next token in the sequence).
new_token_q = torch.randn(1, hidden_dim)
new_token_k = torch.randn(1, hidden_dim)
new_token_v = torch.randn(1, hidden_dim)

# Step 4: Update the KV cache by appending the new token's K and V.
# This is the core operation of KV caching: concatenation along the sequence dimension.
updated_K = torch.cat([cached_K, new_token_k], dim=0)
updated_V = torch.cat([cached_V, new_token_v], dim=0)

# Step 5: Verify cache consistency.
# The first 'seq_len' rows of the updated cache must exactly match the old cache.
assert updated_K.shape == (seq_len + 1, hidden_dim), "Updated K cache shape mismatch"
assert updated_V.shape == (seq_len + 1, hidden_dim), "Updated V cache shape mismatch"
assert torch.allclose(updated_K[:seq_len], cached_K), "K cache consistency failed"
assert torch.allclose(updated_V[:seq_len], cached_V), "V cache consistency failed"

# Step 6: Verify that using the cache produces the same result as full recomputation
# for the new token. We compute attention for the new token using the updated cache.
# Note: In a real transformer, we would also mask future tokens, but here we just
# check that the new token attends to all previous tokens correctly.
new_attn_scores = (new_token_q @ updated_K.T) / scale
new_attn_weights = torch.softmax(new_attn_scores, dim=-1)
new_attn_output = new_attn_weights @ updated_V

# Compare with a "full" recomputation where we include the new token in Q, K, V
full_Q = torch.cat([Q, new_token_q], dim=0)
full_K = torch.cat([K, new_token_k], dim=0)
full_V = torch.cat([V, new_token_v], dim=0)

full_attn_scores_full = (full_Q @ full_K.T) / scale
# Mask the future for the new token (it can only see up to itself)
# For simplicity in this lab, we just check the last row of the full attention output
# matches the cached computation for the new token.
full_attn_weights_full = torch.softmax(full_attn_scores_full, dim=-1)
full_attn_output_full = full_attn_weights_full @ full_V

# The last row of the full attention output should match the new token's output
# from the cached computation.
assert torch.allclose(full_attn_output_full[-1], new_attn_output, atol=1e-5), "Cache-based decoding mismatch"

# Print results in the required format
print(f"RESULT full_attn_shape = {full_attn_output.shape}")
print(f"RESULT updated_K_shape = {updated_K.shape}")
print(f"RESULT updated_V_shape = {updated_V.shape}")
print(f"RESULT new_token_output = {new_attn_output[0, 0]:.6g}")
print(f"RESULT cache_consistency = True")
