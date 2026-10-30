import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Define small sequence length and head dimension for CPU-only lab
seq_len = 8
head_dim = 4

# Create random Q, K, V tensors with shape (batch=1, seq_len, head_dim)
q = torch.randn(1, seq_len, head_dim)
k = torch.randn(1, seq_len, head_dim)
v = torch.randn(1, seq_len, head_dim)

# Standard Full Attention: each token attends to all tokens
scores_full = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(head_dim)
weights_full = torch.softmax(scores_full, dim=-1)
out_full = torch.matmul(weights_full, v)

# Windowed Attention with window_size=2: each token attends to itself and previous token
window_size = 2
# Create a boolean mask where mask[i, j] is True if token i can attend to token j
# For sliding window: token i attends to j where j >= i - window_size + 1 and j <= i
mask = torch.zeros(seq_len, seq_len, dtype=torch.bool)
for i in range(seq_len):
    start = max(0, i - window_size + 1)
    mask[i, start:i+1] = True

# Apply mask to scores: set disallowed positions to -inf before softmax
scores_windowed = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(head_dim)
# Expand mask to match batch dimension
mask_expanded = mask.unsqueeze(0)  # (1, seq_len, seq_len)
scores_windowed = scores_windowed.masked_fill(~mask_expanded, float('-inf'))
weights_windowed = torch.softmax(scores_windowed, dim=-1)
out_windowed = torch.matmul(weights_windowed, v)

# Sparse Attention: only attend to even-indexed tokens (sparse pattern)
# Create sparse mask: token i attends to j only if j % 2 == 0
sparse_mask = torch.zeros(seq_len, seq_len, dtype=torch.bool)
for i in range(seq_len):
    for j in range(seq_len):
        if j % 2 == 0:
            sparse_mask[i, j] = True

scores_sparse = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(head_dim)
sparse_mask_expanded = sparse_mask.unsqueeze(0)
scores_sparse = scores_sparse.masked_fill(~sparse_mask_expanded, float('-inf'))
weights_sparse = torch.softmax(scores_sparse, dim=-1)
out_sparse = torch.matmul(weights_sparse, v)

# Verify that windowed attention weights sum to 1 for each token
assert torch.allclose(weights_windowed.sum(dim=-1), torch.ones(1, seq_len), atol=1e-5), "Windowed attention weights should sum to 1"

# Verify that full attention output differs from windowed attention output
assert not torch.allclose(out_full, out_windowed, atol=1e-5), "Full and windowed attention should produce different outputs"

# Print results
print(f"RESULT out_full[0,0,0] = {out_full[0,0,0].item():.6g}")
print(f"RESULT out_windowed[0,0,0] = {out_windowed[0,0,0].item():.6g}")
print(f"RESULT out_sparse[0,0,0] = {out_sparse[0,0,0].item():.6g}")
print(f"RESULT weights_full[0,0,0] = {weights_full[0,0,0].item():.6g}")
print(f"RESULT weights_windowed[0,0,0] = {weights_windowed[0,0,0].item():.6g}")
print(f"RESULT weights_sparse[0,0,0] = {weights_sparse[0,0,0].item():.6g}")
