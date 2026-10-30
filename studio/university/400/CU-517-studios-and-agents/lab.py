import torch
import math
import random
import json
import itertools
import collections

# Set seeds for reproducibility
torch.manual_seed(0)
random.seed(42)

# Simulate a simple agent pipeline where nodes pass data
# Node A generates a random seed, Node B doubles it, Node C adds 10
seed_val = random.randint(1, 100)
node_b_output = seed_val * 2
node_c_output = node_b_output + 10

# Convert to PyTorch tensors to simulate model pipeline operations
seed_tensor = torch.tensor([float(seed_val)], dtype=torch.float32)
node_b_tensor = seed_tensor * 2.0
node_c_tensor = node_b_tensor + 10.0

# Extract values for printing
seed_val_t = seed_tensor.item()
node_b_val_t = node_b_tensor.item()
node_c_val_t = node_c_tensor.item()

# Print results in required format
print(f"RESULT seed = {seed_val_t:.6g}")
print(f"RESULT node_b = {node_b_val_t:.6g}")
print(f"RESULT node_c = {node_c_val_t:.6g}")

# Truth 1: The pipeline is deterministic given the seed
assert node_b_val_t == seed_val_t * 2

# Truth 2: The final output is the result of sequential transformation
assert node_c_val_t == (seed_val_t * 2) + 10
