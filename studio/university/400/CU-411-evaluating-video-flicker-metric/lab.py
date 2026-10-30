import torch
import math
import random
import json
import itertools
import collections

# Set seed for determinism
torch.manual_seed(0)

# Simulate a stable video frame sequence (3 frames, 1 channel, 2x2 pixels)
# Values are constant across time for each pixel position
stable_frames = torch.tensor([
    [[1.0, 2.0], [3.0, 4.0]],
    [[1.0, 2.0], [3.0, 4.0]],
    [[1.0, 2.0], [3.0, 4.0]]
], dtype=torch.float32)

# Simulate a flickering video frame sequence
# Values change randomly across time for each pixel position
flicker_frames = torch.tensor([
    [[1.0, 2.0], [3.0, 4.0]],
    [[5.0, 1.0], [2.0, 6.0]],
    [[3.0, 4.0], [1.0, 2.0]]
], dtype=torch.float32)

# Calculate temporal variance for each pixel position
# Shape: (3, 1, 2, 2) -> variance over dim 0 -> (1, 2, 2)
stable_var = torch.var(stable_frames, dim=0)
flicker_var = torch.var(flicker_frames, dim=0)

# Average variance across all pixels to get a single flicker metric
stable_metric = torch.mean(stable_var).item()
flicker_metric = torch.mean(flicker_var).item()

# Print results
print(f"RESULT stable_metric = {stable_metric:.6g}")
print(f"RESULT flicker_metric = {flicker_metric:.6g}")

# Assert that stable video has zero flicker
assert stable_metric == 0.0, "Stable video should have zero temporal variance"

# Assert that flickering video has positive flicker
assert flicker_metric > 0.0, "Flickering video should have positive temporal variance"
