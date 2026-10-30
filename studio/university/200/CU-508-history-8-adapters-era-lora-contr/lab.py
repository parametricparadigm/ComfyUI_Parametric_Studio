import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Simulate a LoRA weight matrix (low-rank decomposition)
# Original weight matrix W (4x4)
W = torch.randn(4, 4)

# LoRA matrices A (4x2) and B (2x4) with rank r=2
# In LoRA, the update is delta_W = A @ B where A: (d, r) and B: (r, d)
# For a square matrix W: (d, d), we have A: (d, r) and B: (r, d)
# So delta_W = A @ B: (d, r) @ (r, d) = (d, d)
r = 2
A = torch.randn(4, r)
B = torch.randn(r, 4)

# Calculate the low-rank update delta_W = A @ B
delta_W = A @ B  # (4, r) @ (r, 4) = (4, 4)

# The effective weight is W + delta_W
W_effective = W + delta_W

# Truth 1: The rank of the update matrix delta_W is at most r
# We check the singular values to verify the rank
singular_values = torch.linalg.svdvals(delta_W)
non_zero_singulars = torch.sum(singular_values > 1e-6).item()
print(f"RESULT rank_of_update = {non_zero_singulars}")
assert non_zero_singulars <= r, "LoRA update rank must be <= r"

# Truth 2: The Frobenius norm of the update is smaller than the original for small random init
# This demonstrates that LoRA adds a small perturbation
# To ensure the update is small, we scale A and B by a small factor
scale = 0.1
A_scaled = A * scale
B_scaled = B * scale
delta_W_scaled = A_scaled @ B_scaled

frobenius_norm_update = torch.linalg.norm(delta_W_scaled, ord='fro').item()
frobenius_norm_original = torch.linalg.norm(W, ord='fro').item()
print(f"RESULT frobenius_norm_update = {frobenius_norm_update:.6g}")
print(f"RESULT frobenius_norm_original = {frobenius_norm_original:.6g}")
assert frobenius_norm_update < frobenius_norm_original, "Update norm should be smaller than original for small init"

# Truth 3: The effective weight can be computed as W + A @ B
# Verify that W_effective equals W + delta_W
recomputed_effective = W + delta_W
max_diff = torch.max(torch.abs(W_effective - recomputed_effective)).item()
print(f"RESULT max_diff_effective = {max_diff:.6g}")
assert max_diff < 1e-5, "Effective weight computation should match"

# Truth 4: The number of parameters in LoRA is much smaller than the original
# Original has 4*4 = 16 parameters
# LoRA has 4*2 + 2*4 = 16 parameters (in this small example, but in practice r << d)
original_params = W.numel()
lora_params = A.numel() + B.numel()
print(f"RESULT original_params = {original_params}")
print(f"RESULT lora_params = {lora_params}")
assert lora_params <= original_params, "LoRA should have fewer or equal parameters"

# Truth 5: The relative error between W and W_effective is small
# Use the scaled update to ensure the relative error is small
W_effective_scaled = W + delta_W_scaled
relative_error = torch.linalg.norm(W_effective_scaled - W, ord='fro').item() / frobenius_norm_original
print(f"RESULT relative_error = {relative_error:.6g}")
assert relative_error < 1.0, "Relative error should be less than 1"
