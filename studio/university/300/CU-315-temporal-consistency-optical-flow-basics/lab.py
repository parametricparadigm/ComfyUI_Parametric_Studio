import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Create two tiny 2x2 grayscale images (float32, CPU)
img1 = torch.tensor([[1.0, 2.0], [3.0, 4.0]], dtype=torch.float32)
img2 = torch.tensor([[2.0, 3.0], [4.0, 5.0]], dtype=torch.float32)

# Compute naive "flow" as pixel-wise difference (img2 - img1)
# In this simple case, every pixel shifts by +1, so flow is uniform
flow = img2 - img1

# Assert that the flow is exactly [[1,1],[1,1]]
assert torch.allclose(flow, torch.tensor([[1.0, 1.0], [1.0, 1.0]], dtype=torch.float32)), "Flow should be uniform +1"

# Assert that the mean flow is 1.0
assert flow.mean().item() == 1.0, "Mean flow should be 1.0"

# Compute additional metrics for demonstration
flow_mean = flow.mean().item()
flow_std = flow.std().item()
flow_max = flow.max().item()
flow_min = flow.min().item()

# Print results in required format
print(f"RESULT flow_mean = {flow_mean:.6g}")
print(f"RESULT flow_std = {flow_std:.6g}")
print(f"RESULT flow_max = {flow_max:.6g}")
print(f"RESULT flow_min = {flow_min:.6g}")
print(f"RESULT flow_tensor = {flow.tolist()}")
