import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define dimensions
D = 64      # Dimension of the weight matrix
R = 4       # Rank of the LoRA update
ALPHA = 8   # Scaling factor alpha

# 1. Initialize the base weight matrix W (64x64)
# This represents the pre-trained model weights
W = torch.randn(D, D, dtype=torch.float32)

# 2. Initialize LoRA matrices A and B
# A is (R x D), B is (D x R)
# Typically A is initialized with Kaiming uniform and B with zeros,
# but for this lab, we initialize both randomly to show the update clearly.
A = torch.randn(R, D, dtype=torch.float32)
B = torch.randn(D, R, dtype=torch.float32)

# 3. Calculate parameter counts
# Full fine-tuning: All D*D parameters are updated
full_params = D * D

# LoRA: Only A and B are updated
lora_params = (R * D) + (D * R)

# Print parameter counts
print(f"RESULT full_params = {full_params}")
print(f"RESULT lora_params = {lora_params}")

# 4. Create a random input vector x (1 x D)
x = torch.randn(1, D, dtype=torch.float32)

# 5. Compute the original output: y_orig = x @ W
y_orig = x @ W

# 6. Compute the LoRA update: delta_y = (alpha/r) * (x @ B) @ A
# The standard LoRA formula is W' = W + (alpha/r) * B @ A
# So the update to the output is x @ ((alpha/r) * B @ A)
# Since matrix multiplication is associative: x @ (B @ A) = (x @ B) @ A
# x is (1, D). B is (D, R). A is (R, D).
# x @ B is (1, R). (x @ B) @ A is (1, D).
scale = ALPHA / R
delta_y = scale * ((x @ B) @ A)

# 7. Compute the unmerged two-path output: y_unmerged = y_orig + delta_y
y_unmerged = y_orig + delta_y

# 8. Compute the merged weight matrix: W' = W + (alpha/r) * B @ A
W_merged = W + scale * (B @ A)

# 9. Compute the merged output: y_merged = x @ W_merged
y_merged = x @ W_merged

# 10. Verify that merged output equals unmerged output
# They should be identical (up to floating point precision)
diff = torch.max(torch.abs(y_merged - y_unmerged)).item()
print(f"RESULT max_diff_merged_unmerged = {diff}")

# Assert that the difference is negligible (use a slightly larger tolerance for float32)
assert diff < 1e-4, "Merged and unmerged outputs should be identical"

# 11. Show that strength scaling is linear in the output delta
# Let's test with a different scale factor, e.g., scale2 = 2 * scale
scale2 = 2 * scale
delta_y2 = scale2 * ((x @ B) @ A)
y_unmerged2 = y_orig + delta_y2

# The delta for scale2 should be exactly 2 times the delta for scale1
delta1 = delta_y
delta2 = delta_y2

# Check linearity: delta2 should be 2 * delta1
linearity_diff = torch.max(torch.abs(delta2 - 2 * delta1)).item()
print(f"RESULT linearity_diff = {linearity_diff}")

# Assert that the scaling is linear
assert linearity_diff < 1e-4, "LoRA scaling should be linear in the output delta"

# 12. Print the actual output values for inspection
print(f"RESULT y_orig[0] = {y_orig[0, 0].item()}")
print(f"RESULT y_unmerged[0] = {y_unmerged[0, 0].item()}")
print(f"RESULT y_merged[0] = {y_merged[0, 0].item()}")
