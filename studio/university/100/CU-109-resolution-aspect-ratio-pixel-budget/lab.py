import torch
import math
import random
import json
import itertools
import collections

# Set seeds for determinism
torch.manual_seed(0)
random.seed(42)

# Concept: Pixel Budget and Aspect Ratio
# We define a target pixel budget (e.g., 1 megapixel) and an aspect ratio (16:9).
# Goal: Find integer width and height that fit within the budget while maintaining the ratio as closely as possible.

budget = 1_000_000
aspect_ratio = 16 / 9

# To maintain aspect ratio, height = width / aspect_ratio
# Total pixels = width * height = width * (width / aspect_ratio) = width^2 / aspect_ratio
# So, ideal width = sqrt(budget * aspect_ratio)

calc_width = math.sqrt(budget * aspect_ratio)
calc_height = calc_width / aspect_ratio

# Round to nearest integers
w = round(calc_width)
h = round(calc_height)

# Check 1: The calculated dimensions should be close to the ideal ratio.
ratio_check = w / h
assert abs(ratio_check - aspect_ratio) < 0.01, "Aspect ratio deviation too large"

# Check 2: The total pixel count should be within a reasonable tolerance of the budget.
pixel_count = w * h
assert abs(pixel_count - budget) / budget < 0.01, "Pixel budget deviation too large"

# Use PyTorch tensors to represent the dimensions (tiny tensors, float32 CPU)
w_tensor = torch.tensor([w], dtype=torch.float32)
h_tensor = torch.tensor([h], dtype=torch.float32)

# Compute the actual aspect ratio using torch
actual_ratio = w_tensor / h_tensor
actual_ratio_val = actual_ratio.item()

# Compute the pixel count using torch
pixel_count_tensor = w_tensor * h_tensor
pixel_count_val = pixel_count_tensor.item()

# Print results in the required format
print(f"RESULT width = {w}")
print(f"RESULT height = {h}")
print(f"RESULT aspect_ratio = {actual_ratio_val:.6g}")
print(f"RESULT pixel_count = {pixel_count_val:.6g}")
print(f"RESULT budget = {budget}")
