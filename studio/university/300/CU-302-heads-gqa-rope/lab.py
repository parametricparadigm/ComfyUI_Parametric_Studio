import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# --- Part 1: Multi-head Split/Merge ---
# Define dimensions
seq_len = 4
hidden_dim = 8
num_heads = 4
head_dim = hidden_dim // num_heads  # 2

# Create a dummy input tensor
x = torch.randn(seq_len, hidden_dim)

# Split into heads: (seq_len, hidden_dim) -> (seq_len, num_heads, head_dim)
# Reshape to (seq_len, num_heads, head_dim) then permute to (num_heads, seq_len, head_dim)
x_heads = x.view(seq_len, num_heads, head_dim).permute(1, 0, 2)

# Merge back: (num_heads, seq_len, head_dim) -> (seq_len, hidden_dim)
x_merged = x_heads.permute(1, 0, 2).reshape(seq_len, hidden_dim)

# Verify split/merge is identity
assert torch.allclose(x, x_merged), "Multi-head split/merge failed"
print(f"RESULT split_merge_identity = {torch.allclose(x, x_merged)}")

# --- Part 2: GQA Parameter Count Reduction ---
# Standard MHA: Q, K, V each have shape (hidden_dim, hidden_dim)
# GQA: Q has (hidden_dim, hidden_dim), K and V have (hidden_dim, hidden_dim // group_size)
# Let's use group_size = 2 for demonstration
group_size = 2
num_kv_heads = num_heads // group_size  # 2

# Calculate parameter counts for a single layer (ignoring biases for simplicity)
# MHA: Q_proj, K_proj, V_proj each are (hidden_dim, hidden_dim)
mha_params = 3 * (hidden_dim * hidden_dim)

# GQA: Q_proj is (hidden_dim, hidden_dim), K_proj and V_proj are (hidden_dim, hidden_dim // group_size)
gqa_params = (hidden_dim * hidden_dim) + 2 * (hidden_dim * (hidden_dim // group_size))

# The reduction ratio for K/V specifically
# MHA K/V params: 2 * hidden_dim * hidden_dim
# GQA K/V params: 2 * hidden_dim * (hidden_dim // group_size)
kv_reduction_ratio = (2 * hidden_dim * hidden_dim) / (2 * hidden_dim * (hidden_dim // group_size))

print(f"RESULT mha_total_params = {mha_params}")
print(f"RESULT gqa_total_params = {gqa_params}")
print(f"RESULT kv_reduction_ratio = {kv_reduction_ratio:.6g}")

# Assert that GQA reduces parameters
assert gqa_params < mha_params, "GQA should reduce parameter count"
assert kv_reduction_ratio == group_size, "KV reduction ratio should equal group size"

# --- Part 3: RoPE Implementation and Relative Position Verification ---
def apply_rope(x, positions, dim):
    """
    Apply Rotary Position Embedding to input tensor x.
    x: (seq_len, dim)
    positions: (seq_len,)
    dim: dimension of the vector (must be even)
    """
    # Generate frequencies: theta_i = 10000^(-2i/dim)
    # For dim=2, we have one pair: theta_0 = 10000^0 = 1
    # For dim=4, we have two pairs: theta_0 = 1, theta_1 = 10000^(-0.5)
    
    # Create frequency tensor
    # i ranges from 0 to dim/2 - 1
    i = torch.arange(0, dim, 2).float()
    theta = 10000 ** (-i / dim)  # (dim/2,)
    
    # positions: (seq_len,)
    # theta: (dim/2,)
    # We need to compute positions * theta for each pair
    # Expand positions to (seq_len, 1) and theta to (1, dim/2)
    pos_expanded = positions.unsqueeze(1)  # (seq_len, 1)
    theta_expanded = theta.unsqueeze(0)    # (1, dim/2)
    
    # Compute angles: (seq_len, dim/2)
    angles = pos_expanded * theta_expanded
    
    # Compute cos and sin
    cos = torch.cos(angles)  # (seq_len, dim/2)
    sin = torch.sin(angles)  # (seq_len, dim/2)
    
    # Split x into pairs: (seq_len, dim) -> (seq_len, dim/2, 2)
    x_pairs = x.view(x.shape[0], dim // 2, 2)
    x1 = x_pairs[:, :, 0]  # (seq_len, dim/2)
    x2 = x_pairs[:, :, 1]  # (seq_len, dim/2)
    
    # Apply rotation:
    # new_x1 = x1 * cos - x2 * sin
    # new_x2 = x1 * sin + x2 * cos
    new_x1 = x1 * cos - x2 * sin
    new_x2 = x1 * sin + x2 * cos
    
    # Merge back: (seq_len, dim/2, 2)
    new_x_pairs = torch.stack([new_x1, new_x2], dim=-1)
    new_x = new_x_pairs.view(x.shape[0], dim)
    
    return new_x

# Test RoPE with dim=4 (2 pairs)
rope_dim = 4
seq_len_rope = 3
x_rope = torch.randn(seq_len_rope, rope_dim)
positions = torch.tensor([0, 1, 2], dtype=torch.float32)

# Apply RoPE
x_rope_rotated = apply_rope(x_rope, positions, rope_dim)

# Verify that RoPE is a rotation (preserves norm)
norms_before = torch.norm(x_rope, dim=1)
norms_after = torch.norm(x_rope_rotated, dim=1)
assert torch.allclose(norms_before, norms_after, atol=1e-5), "RoPE should preserve vector norms"
print(f"RESULT rope_norm_preserved = {torch.allclose(norms_before, norms_after, atol=1e-5)}")

# Verify relative position property:
# For the SAME query and key vectors, if we rotate them by different absolute positions
# but the same relative offset, the dot product should be the same.

# Let's use the same base vectors for query and key
base_q = torch.randn(1, rope_dim)
base_k = torch.randn(1, rope_dim)

# Case 1: Query at position 0, Key at position 2
q_pos0 = apply_rope(base_q, torch.tensor([0.0]), rope_dim)
k_pos2 = apply_rope(base_k, torch.tensor([2.0]), rope_dim)
score_case1 = torch.sum(q_pos0 * k_pos2, dim=1).item()

# Case 2: Query at position 1, Key at position 3 (same relative offset of -2)
q_pos1 = apply_rope(base_q, torch.tensor([1.0]), rope_dim)
k_pos3 = apply_rope(base_k, torch.tensor([3.0]), rope_dim)
score_case2 = torch.sum(q_pos1 * k_pos3, dim=1).item()

# These should be equal (within floating point tolerance)
assert abs(score_case1 - score_case2) < 1e-5, "RoPE attention score should depend only on relative position"
print(f"RESULT rope_relative_pos_score1 = {score_case1:.6g}")
print(f"RESULT rope_relative_pos_score2 = {score_case2:.6g}")
print(f"RESULT rope_relative_pos_equal = {abs(score_case1 - score_case2) < 1e-5}")
