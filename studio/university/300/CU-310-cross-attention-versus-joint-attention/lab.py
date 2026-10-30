import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Define small dimensions for a CPU-only demo
batch_size = 1
seq_len_q = 4  # Query sequence length (e.g., image tokens)
seq_len_k = 3  # Key/Value sequence length (e.g., text tokens)
dim = 8

# Generate random inputs
q = torch.randn(batch_size, seq_len_q, dim)
k = torch.randn(batch_size, seq_len_k, dim)
v = torch.randn(batch_size, seq_len_k, dim)

# 1. Cross-Attention: Q from image, K/V from text
# Shape: [B, Lq, Lk]
scores_cross = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(dim)
weights_cross = torch.softmax(scores_cross, dim=-1)
out_cross = torch.matmul(weights_cross, v)

# 2. Joint/Self-Attention: Concatenate Q, K, V into one sequence
# Create joint sequence where image and text tokens attend to each other
# Q_joint = [q, k], K_joint = [q, k], V_joint = [q, k] (using q and k as values for simplicity)
q_joint = torch.cat([q, k], dim=1)  # [B, Lq+Lk, dim]
k_joint = torch.cat([q, k], dim=1)  # [B, Lq+Lk, dim]
v_joint = torch.cat([q, k], dim=1)  # [B, Lq+Lk, dim]

# Compute joint attention scores
scores_joint = torch.matmul(q_joint, k_joint.transpose(-2, -1)) / math.sqrt(dim)
weights_joint = torch.softmax(scores_joint, dim=-1)
out_joint = torch.matmul(weights_joint, v_joint)

# Extract the image part of the joint output (first seq_len_q tokens)
out_joint_image = out_joint[:, :seq_len_q, :]

# Print results
print(f"RESULT cross_attention_output_shape = {out_cross.shape}")
print(f"RESULT joint_attention_output_shape = {out_joint.shape}")
print(f"RESULT cross_attention_first_token = {out_cross[0, 0, 0].item():.6g}")
print(f"RESULT joint_attention_first_token = {out_joint_image[0, 0, 0].item():.6g}")

# Assert that cross-attention output has the correct shape
assert out_cross.shape == (batch_size, seq_len_q, dim), "Cross-attention output shape is incorrect"

# Assert that joint attention output has the correct shape
assert out_joint.shape == (batch_size, seq_len_q + seq_len_k, dim), "Joint attention output shape is incorrect"

# Assert that cross-attention weights sum to 1 over the key dimension
assert torch.allclose(weights_cross.sum(dim=-1), torch.ones(batch_size, seq_len_q)), "Cross-attention weights do not sum to 1"

# Assert that joint attention weights sum to 1 over the key dimension
assert torch.allclose(weights_joint.sum(dim=-1), torch.ones(batch_size, seq_len_q + seq_len_k)), "Joint attention weights do not sum to 1"
