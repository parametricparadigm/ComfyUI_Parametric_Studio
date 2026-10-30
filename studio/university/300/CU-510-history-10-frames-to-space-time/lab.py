import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Simulate a simple temporal consistency check
# In early video models, frames were often independent (like images).
# Modern models enforce consistency across time (space-time).

# Create a 'video' of 3 frames, each with 2 pixels
# Frame 0: [1, 2]
# Frame 1: [2, 3] (should be close to Frame 0 if consistent)
# Frame 2: [3, 4] (should be close to Frame 1)

frames = torch.tensor([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]], dtype=torch.float32)

# Calculate temporal difference between consecutive frames
diff_0_1 = torch.abs(frames[1] - frames[0])
diff_1_2 = torch.abs(frames[2] - frames[1])

# In a consistent video, changes should be small and smooth
# Here, the change is exactly 1.0 for each pixel in each step
assert torch.allclose(diff_0_1, torch.tensor([1.0, 1.0])), "Temporal difference 0-1 should be [1.0, 1.0]"
assert torch.allclose(diff_1_2, torch.tensor([1.0, 1.0])), "Temporal difference 1-2 should be [1.0, 1.0]"

# Compute the mean temporal difference across the whole clip
mean_diff = (diff_0_1.mean() + diff_1_2.mean()) / 2.0

# Print results
print(f"RESULT mean_temporal_diff = {mean_diff.item():.6g}")
print(f"RESULT diff_0_1 = {diff_0_1.tolist()}")
print(f"RESULT diff_1_2 = {diff_1_2.tolist()}")
