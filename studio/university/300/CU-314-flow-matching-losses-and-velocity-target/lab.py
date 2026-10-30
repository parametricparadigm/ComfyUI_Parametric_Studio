import torch
import math
import random
import json
import itertools
import collections

# Set seed for determinism
torch.manual_seed(0)

# Define simple 1D data points and noise points
data = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)
noise = torch.tensor([0.5, -1.0, 0.2], dtype=torch.float32)

# Define a specific timestep t in [0, 1)
t = 0.5

# Compute the interpolated point x_t = (1-t)*data + t*noise
x_t = (1 - t) * data + t * noise

# The velocity target in flow matching is the derivative of the interpolation path
# v_target = noise - data
v_target = noise - data

# A simple model prediction (simulated as a linear combination for demonstration)
# In a real scenario, this would be the output of a neural network
model_pred = 0.8 * v_target + 0.1 * torch.randn_like(v_target)

# Compute the Mean Squared Error loss
loss = torch.mean((model_pred - v_target) ** 2)

# Verify that the velocity target is indeed the difference between noise and data
assert torch.allclose(v_target, noise - data), "Velocity target should be noise - data"

# Verify that the interpolated point lies between data and noise
assert torch.all(x_t >= torch.min(data, noise)) and torch.all(x_t <= torch.max(data, noise)), "Interpolated point should be between data and noise"

# Print results in the required format
print(f"RESULT x_t = {x_t.tolist()}")
print(f"RESULT v_target = {v_target.tolist()}")
print(f"RESULT model_pred = {model_pred.tolist()}")
print(f"RESULT loss = {f'{loss.item():.6g}'}")
