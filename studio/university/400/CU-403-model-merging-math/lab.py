import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define a small base weight vector
base = torch.randn(10, dtype=torch.float32)

# Create two "fine-tuned" versions by adding small perturbations
t1 = base + 0.1 * torch.randn(10, dtype=torch.float32)
t2 = base + 0.1 * torch.randn(10, dtype=torch.float32)

# Compute linear interpolation (alpha = 0.5)
alpha = 0.5
lin_interp = alpha * t1 + (1 - alpha) * t2

# Compute SLERP (Spherical Linear Interpolation)
# First, normalize the vectors to get directions
t1_norm = t1 / torch.norm(t1)
t2_norm = t2 / torch.norm(t2)

# Compute the angle between the two normalized vectors
cos_theta = torch.dot(t1_norm, t2_norm)
# Clamp to avoid numerical issues
cos_theta = torch.clamp(cos_theta, -1.0, 1.0)
theta = torch.acos(cos_theta)

# SLERP formula: (sin((1-alpha)*theta) * t1_norm + sin(alpha*theta) * t2_norm) / sin(theta)
sin_theta = torch.sin(theta)
slerp = (torch.sin((1 - alpha) * theta) * t1_norm + torch.sin(alpha * theta) * t2_norm) / sin_theta

# Scale SLERP result to match the average norm of t1 and t2 (since SLERP preserves direction but we want comparable magnitude)
# Actually, SLERP preserves the norm of the input vectors if they have the same norm.
# Let's check: if t1 and t2 have different norms, SLERP on normalized vectors gives a unit vector.
# To make it comparable, we can scale it to the geometric mean of the norms, or just report as is.
# For this lab, let's compute SLERP on the original vectors by scaling the unit SLERP result.
# The standard SLERP for vectors of different norms is not straightforward. 
# Let's instead assume t1 and t2 have similar norms, or we normalize them first.
# For clarity, let's compute SLERP on the normalized vectors and then scale to the average norm.
avg_norm = (torch.norm(t1) + torch.norm(t2)) / 2
slerp_scaled = slerp * avg_norm

# Compute task arithmetic: base + a*(t1-base) + b*(t2-base)
a = 0.5
b = 0.5
task_arith = base + a * (t1 - base) + b * (t2 - base)

# Helper function to compute cosine similarity
def cosine_similarity(v1, v2):
    return torch.dot(v1, v2) / (torch.norm(v1) * torch.norm(v2))

# Compute norms
norm_base = torch.norm(base)
norm_t1 = torch.norm(t1)
norm_t2 = torch.norm(t2)
norm_lin = torch.norm(lin_interp)
norm_slerp = torch.norm(slerp_scaled)
norm_task = torch.norm(task_arith)

# Compute cosine similarities to each parent
cos_lin_t1 = cosine_similarity(lin_interp, t1)
cos_lin_t2 = cosine_similarity(lin_interp, t2)
cos_slerp_t1 = cosine_similarity(slerp_scaled, t1)
cos_slerp_t2 = cosine_similarity(slerp_scaled, t2)
cos_task_t1 = cosine_similarity(task_arith, t1)
cos_task_t2 = cosine_similarity(task_arith, t2)

# Print results
print(f"RESULT norm_base = {norm_base.item():.6g}")
print(f"RESULT norm_t1 = {norm_t1.item():.6g}")
print(f"RESULT norm_t2 = {norm_t2.item():.6g}")
print(f"RESULT norm_lin_interp = {norm_lin.item():.6g}")
print(f"RESULT norm_slerp = {norm_slerp.item():.6g}")
print(f"RESULT norm_task_arith = {norm_task.item():.6g}")
print(f"RESULT cos_lin_t1 = {cos_lin_t1.item():.6g}")
print(f"RESULT cos_lin_t2 = {cos_lin_t2.item():.6g}")
print(f"RESULT cos_slerp_t1 = {cos_slerp_t1.item():.6g}")
print(f"RESULT cos_slerp_t2 = {cos_slerp_t2.item():.6g}")
print(f"RESULT cos_task_t1 = {cos_task_t1.item():.6g}")
print(f"RESULT cos_task_t2 = {cos_task_t2.item():.6g}")

# Assert that SLERP preserves norm better than linear interpolation
# Linear interpolation should shrink the norm (unless t1 and t2 are parallel)
assert norm_lin < (norm_t1 + norm_t2) / 2, "Linear interpolation should shrink the norm"

# SLERP should preserve the norm more closely (within a small tolerance)
# Since we scaled SLERP to the average norm, it should be very close
assert abs(norm_slerp - (norm_t1 + norm_t2) / 2) < 1e-5, "SLERP should preserve the norm"

# Assert that cosine similarities are reasonable (between -1 and 1)
assert -1.0 <= cos_lin_t1.item() <= 1.0, "Cosine similarity must be in [-1, 1]"
assert -1.0 <= cos_slerp_t1.item() <= 1.0, "Cosine similarity must be in [-1, 1]"
