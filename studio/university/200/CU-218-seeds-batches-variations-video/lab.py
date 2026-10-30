import torch
import math
import random
import json
import itertools
import collections

# Set the seed to ensure reproducibility of the random number generation
torch.manual_seed(0)

# Define the batch size and the shape of the latent tensor
batch_size = 4
latent_shape = (batch_size, 16, 8, 8)

# Generate a batch of random noise using the standard normal distribution
noise = torch.randn(latent_shape)

# Extract the first and second frames from the first sample in the batch
first_frame = noise[0, :, 0, :]
second_frame = noise[0, :, 1, :]

# Assert that the first frame is identical to itself (sanity check)
assert torch.allclose(first_frame, first_frame), "Frame 0 must be identical to itself"

# Assert that consecutive frames in a random batch are different
assert not torch.allclose(first_frame, second_frame), "Consecutive frames in a random batch should differ"

# Calculate the mean of the first and second frames
first_frame_mean = first_frame.mean().item()
second_frame_mean = second_frame.mean().item()

# Print the results in the required format
print(f"RESULT batch_size = {batch_size}")
print(f"RESULT first_frame_mean = {first_frame_mean:.6g}")
print(f"RESULT second_frame_mean = {second_frame_mean:.6g}")
