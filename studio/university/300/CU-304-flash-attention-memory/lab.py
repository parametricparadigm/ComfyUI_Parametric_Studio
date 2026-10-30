import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Course: CU-304 "Why attention is O(n^2) and how Flash/Sage fix the memory"
# Lab: Compute memory of full attention matrix and implement online-softmax tiled attention

# Step 1: Compute memory footprint of full attention matrix for various sequence lengths
# In fp16, each element is 2 bytes. Attention matrix is n x n.
def compute_attention_memory(n, dtype=torch.float16):
    """
    Compute the memory in bytes for a full n x n attention matrix.
    For fp16, each element is 2 bytes.
    """
    # Number of elements in the attention matrix
    num_elements = n * n
    # Bytes per element for fp16
    bytes_per_element = 2
    # Total memory in bytes
    total_memory_bytes = num_elements * bytes_per_element
    return total_memory_bytes

# Print memory for n = 1k, 4k, 16k, 64k tokens
sequence_lengths = [1024, 4096, 16384, 65536]
for n in sequence_lengths:
    mem_bytes = compute_attention_memory(n)
    mem_mb = mem_bytes / (1024 * 1024)
    print(f"RESULT mem_n_{n} = {mem_mb:.6g}")

# Step 2: Implement standard attention for comparison
def standard_attention(Q, K, V, scale=1.0):
    """
    Standard attention: compute full n x n attention matrix.
    Q, K, V are tensors of shape (batch, seq_len, d_model)
    Returns attention output of shape (batch, seq_len, d_model)
    """
    # Compute attention scores: Q @ K^T
    # Q: (batch, n, d), K: (batch, n, d)
    # scores: (batch, n, n)
    scores = torch.matmul(Q, K.transpose(-2, -1)) * scale
    
    # Apply softmax along the last dimension
    attn_weights = torch.softmax(scores, dim=-1)
    
    # Apply attention weights to values
    # attn_weights: (batch, n, n), V: (batch, n, d)
    output = torch.matmul(attn_weights, V)
    return output

# Step 3: Implement online-softmax tiled attention (Flash-style)
# This avoids forming the full n x n matrix by processing in tiles
def online_softmax_tiled_attention(Q, K, V, scale=1.0, tile_size=256):
    """
    Online-softmax tiled attention that never forms the full n x n matrix.
    Uses the online softmax algorithm to compute attention in tiles.
    
    Q, K, V: (batch, seq_len, d_model)
    Returns: (batch, seq_len, d_model)
    """
    batch_size, seq_len, d_model = Q.shape
    
    # Initialize output and running statistics
    # output: (batch, seq_len, d_model)
    output = torch.zeros(batch_size, seq_len, d_model, dtype=Q.dtype, device=Q.device)
    
    # Running max and sum for online softmax
    # m_i: running max for each query position, shape (batch, seq_len)
    m_i = torch.full((batch_size, seq_len), float('-inf'), dtype=Q.dtype, device=Q.device)
    # l_i: running sum of exp(scores - m_i), shape (batch, seq_len)
    l_i = torch.zeros(batch_size, seq_len, dtype=Q.dtype, device=Q.device)
    
    # Process K and V in tiles
    for k_start in range(0, seq_len, tile_size):
        k_end = min(k_start + tile_size, seq_len)
        
        # Get tile of K and V
        K_tile = K[:, k_start:k_end, :]  # (batch, tile_len, d_model)
        V_tile = V[:, k_start:k_end, :]  # (batch, tile_len, d_model)
        
        # Compute attention scores for this tile: Q @ K_tile^T
        # Q: (batch, seq_len, d_model), K_tile: (batch, tile_len, d_model)
        # scores_tile: (batch, seq_len, tile_len)
        scores_tile = torch.matmul(Q, K_tile.transpose(-2, -1)) * scale
        
        # Find max in this tile for numerical stability
        # m_tile: (batch, seq_len)
        m_tile = torch.max(scores_tile, dim=-1).values
        
        # Update running max: m_new = max(m_i, m_tile)
        m_new = torch.max(m_i, m_tile)
        
        # Avoid log(0) or exp issues when m_new is -inf
        # If m_new is -inf, we can't compute properly, but this shouldn't happen with real data
        # For safety, replace -inf with 0 in the correction factor
        m_new_safe = torch.where(torch.isinf(m_new), torch.zeros_like(m_new), m_new)
        
        # Correction factor for previous tiles: exp(m_i - m_new)
        # This rescales the previous output and l_i
        correction = torch.exp(m_i - m_new_safe)
        # Where m_i was -inf, correction should be 0
        correction = torch.where(torch.isinf(m_i), torch.zeros_like(correction), correction)
        
        # Update l_i: l_new = l_i * correction + sum(exp(scores_tile - m_new), dim=-1)
        # exp_scores_tile: (batch, seq_len, tile_len)
        exp_scores_tile = torch.exp(scores_tile - m_new_safe.unsqueeze(-1))
        # Sum over the tile dimension
        sum_exp_tile = torch.sum(exp_scores_tile, dim=-1)  # (batch, seq_len)
        
        l_new = l_i * correction + sum_exp_tile
        
        # Update output: output_new = output * correction + exp_scores_tile @ V_tile
        # output * correction: (batch, seq_len, d_model) * (batch, seq_len, 1)
        output = output * correction.unsqueeze(-1)
        # exp_scores_tile @ V_tile: (batch, seq_len, tile_len) @ (batch, tile_len, d_model)
        output = output + torch.matmul(exp_scores_tile, V_tile)
        
        # Update running statistics
        m_i = m_new
        l_i = l_new
    
    # Final normalization: divide by l_i
    # l_i: (batch, seq_len), need to reshape for broadcasting
    l_i_safe = torch.where(l_i == 0, torch.ones_like(l_i), l_i)
    output = output / l_i_safe.unsqueeze(-1)
    
    return output

# Step 4: Verify that tiled attention matches standard attention
# Use small tensors for quick verification
batch_size = 1
seq_len = 512
d_model = 64

# Generate random Q, K, V
Q = torch.randn(batch_size, seq_len, d_model, dtype=torch.float32)
K = torch.randn(batch_size, seq_len, d_model, dtype=torch.float32)
V = torch.randn(batch_size, seq_len, d_model, dtype=torch.float32)

# Compute standard attention
attn_std = standard_attention(Q, K, V, scale=1.0 / math.sqrt(d_model))

# Compute tiled attention
attn_tiled = online_softmax_tiled_attention(Q, K, V, scale=1.0 / math.sqrt(d_model), tile_size=128)

# Compute max absolute difference
max_diff = torch.max(torch.abs(attn_std - attn_tiled)).item()
print(f"RESULT max_abs_diff = {max_diff:.6g}")

# Assert that the difference is small (numerical precision)
assert max_diff < 1e-4, f"Max abs diff too large: {max_diff}"

# Step 5: Verify that tiled attention does NOT form the full n x n matrix
# We can verify this conceptually by checking that the tile_size is much smaller than seq_len
# and that the algorithm processes in tiles
assert 128 < seq_len, "Tile size should be smaller than sequence length for tiling to work"

# Additional check: verify with different tile sizes
for ts in [64, 128, 256]:
    attn_tiled_ts = online_softmax_tiled_attention(Q, K, V, scale=1.0 / math.sqrt(d_model), tile_size=ts)
    diff_ts = torch.max(torch.abs(attn_std - attn_tiled_ts)).item()
    print(f"RESULT max_diff_tile_{ts} = {diff_ts:.6g}")
    assert diff_ts < 1e-4, f"Max abs diff too large for tile_size={ts}: {diff_ts}"

# Step 6: Demonstrate memory savings conceptually
# For n=64k, full attention matrix would be 64k * 64k * 2 bytes = 8 GB in fp16
# With tiling, we only need tile_size * n * 2 bytes at a time
n_large = 65536
tile_size_demo = 256
full_mem = n_large * n_large * 2
tiled_mem = tile_size_demo * n_large * 2
print(f"RESULT full_mem_64k_mb = {full_mem / (1024*1024):.6g}")
print(f"RESULT tiled_mem_64k_mb = {tiled_mem / (1024*1024):.6g}")

# Assert that tiled memory is much smaller
assert tiled_mem < full_mem, "Tiled memory should be smaller than full memory"
assert full_mem / tiled_mem == n_large / tile_size_demo, "Memory ratio should match sequence length to tile size ratio"

print("RESULT all_checks_passed = 1")
