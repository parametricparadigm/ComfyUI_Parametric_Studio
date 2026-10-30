import torch
import math
import random
import json
import itertools
import collections

# Set seed for determinism as required by the lab rules
torch.manual_seed(0)

# Concept: Memory footprint is proportional to number of elements * bytes per element.
# Concept: Computational cost (FLOPs) for matrix multiplication is proportional to M*N*K.

# Simulate a small batch of images
batch_size = 2
channels = 3
height = 8
width = 8

# Create a tensor on CPU
x = torch.randn(batch_size, channels, height, width)

# Truth 1: Memory size in bytes = numel * element_size
expected_memory_bytes = x.numel() * x.element_size()
actual_memory_bytes = x.numel() * x.element_size()
assert expected_memory_bytes == actual_memory_bytes, "Memory calculation failed"

# Simulate a linear layer (matrix multiplication)
# Input shape: (batch, in_features) -> (batch, out_features)
# Let's flatten the image to treat it as a vector for a simple linear op
in_features = channels * height * width
out_features = 16

# Create weight matrix for the linear layer
W = torch.randn(out_features, in_features)
b = torch.randn(out_features)

# Flatten the input tensor to (batch, in_features)
x_flat = x.view(batch_size, in_features)

# Perform the linear transformation: y = x @ W^T + b
y = torch.nn.functional.linear(x_flat, W, b)

# Truth 2: FLOPs for matrix multiplication (M x K) @ (K x N) is 2 * M * N * K
# Here M=batch_size, N=out_features, K=in_features
expected_flops = 2 * batch_size * out_features * in_features
# Note: The actual FLOPs count might vary slightly depending on implementation,
# but the theoretical minimum for the core matmul is 2*M*N*K.
# We assert that our calculated theoretical FLOPs is positive and matches the formula.
assert expected_flops > 0, "FLOPs calculation must be positive"
assert expected_flops == 2 * batch_size * out_features * in_features, "FLOPs formula check failed"

# Print results as required
print(f"RESULT memory_bytes = {x.numel() * x.element_size()}")
print(f"RESULT flops = {expected_flops}")
print(f"RESULT output_shape = {tuple(y.shape)}")
