import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Simulate a simple NeRF-style volume rendering with 3 slices
# Each slice has an opacity (alpha) and color
# We use the front-to-back compositing formula:
# C = sum(alpha_i * T_i * color_i), where T_i = prod(1 - alpha_j for j < i)

# Define 3 slices with fixed opacities and colors
# Slice 0: Red, alpha=0.5
# Slice 1: Green, alpha=0.5
# Slice 2: Blue, alpha=0.5
alphas = torch.tensor([0.5, 0.5, 0.5], dtype=torch.float32)
colors = torch.tensor([[1.0, 0.0, 0.0],
                       [0.0, 1.0, 0.0],
                       [0.0, 0.0, 1.0]], dtype=torch.float32)

# Calculate transmittance T for each slice
# T[0] = 1.0 (no previous slices)
# T[i] = T[i-1] * (1 - alpha[i-1])
T = torch.ones(3, dtype=torch.float32)
for i in range(1, 3):
    T[i] = T[i-1] * (1 - alphas[i-1])

# Calculate the final composited color
# C = sum over i of (alpha_i * T_i * color_i)
# We need to broadcast alpha and T to match colors shape
alpha_expanded = alphas.unsqueeze(1)  # shape (3, 1)
T_expanded = T.unsqueeze(1)           # shape (3, 1)

# Element-wise multiplication and sum over slices
C = torch.sum(alpha_expanded * T_expanded * colors, dim=0)

# Print results in required format
print(f"RESULT final_color = {C[0]:.6g} {C[1]:.6g} {C[2]:.6g}")
print(f"RESULT transmittance = {T[0]:.6g} {T[1]:.6g} {T[2]:.6g}")

# Truth 1: The red component should be 0.5
# First slice: alpha=0.5, T=1.0, color=[1,0,0] -> contribution = 0.5 * 1.0 * 1.0 = 0.5
# Other slices have red=0, so total red = 0.5
assert abs(C[0].item() - 0.5) < 1e-6, "Red component mismatch"

# Truth 2: The green component should be 0.25
# Second slice: alpha=0.5, T=0.5 (since 1-0.5=0.5), color=[0,1,0] -> contribution = 0.5 * 0.5 * 1.0 = 0.25
# Other slices have green=0, so total green = 0.25
assert abs(C[1].item() - 0.25) < 1e-6, "Green component mismatch"

# Truth 3: The blue component should be 0.125
# Third slice: alpha=0.5, T=0.25 (since 0.5*0.5=0.25), color=[0,0,1] -> contribution = 0.5 * 0.25 * 1.0 = 0.125
# Other slices have blue=0, so total blue = 0.125
assert abs(C[2].item() - 0.125) < 1e-6, "Blue component mismatch"
