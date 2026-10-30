import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Define parameters for a simple 1D DDPM forward process
# We simulate adding Gaussian noise over T steps to a small data point.
# This demonstrates the core idea: data gradually becomes pure noise.

# Initial data point (x0)
x0 = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)

# Number of diffusion steps
T = 100

# Beta schedule: constant beta for simplicity in this lab
# In real DDPM, beta_t varies, but constant is fine for demonstration
beta = 0.01

# Forward diffusion process: iteratively add noise
# x_t = x_{t-1} + sqrt(beta) * epsilon, where epsilon ~ N(0, I)
x_t = x0.clone()
for t in range(T):
    noise = torch.randn_like(x0)
    x_t = x_t + math.sqrt(beta) * noise

# Check 1: After diffusion, the data should be significantly different from original
# The variance should have increased due to accumulated noise
assert not torch.allclose(x0, x_t), "Forward diffusion should change the data"

# Check 2: The final state should still be finite (no NaNs or infs)
# This ensures numerical stability in the diffusion process
assert torch.all(torch.isfinite(x_t)), "Diffusion steps should produce finite numbers"

# Additional check: The mean of x_t should be close to the mean of x0
# since we're adding zero-mean noise
mean_x0 = x0.mean().item()
mean_xt = x_t.mean().item()
# With only 3 points and 100 steps, the mean might drift, but should be in reasonable range
# We check that it's not wildly off (within 2 standard deviations of expected drift)
# Expected variance after T steps: T * beta = 100 * 0.01 = 1.0
# So std dev of each component is sqrt(1.0) = 1.0
# The mean of 3 components should be within ~2/sqrt(3) ≈ 1.15 of original mean
assert abs(mean_xt - mean_x0) < 2.0, "Mean should not drift too far with zero-mean noise"

# Print results in required format
RESULT_original = [f"{x:.6g}" for x in x0.tolist()]
RESULT_after_diffusion = [f"{x:.6g}" for x in x_t.tolist()]
RESULT_mean_original = f"{mean_x0:.6g}"
RESULT_mean_after = f"{mean_xt:.6g}"

print(f"RESULT original = {RESULT_original}")
print(f"RESULT after_diffusion = {RESULT_after_diffusion}")
print(f"RESULT mean_original = {RESULT_mean_original}")
print(f"RESULT mean_after = {RESULT_mean_after}")
print("Lab complete: Diffusion adds noise deterministically given the seed")
