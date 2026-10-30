import torch
import math
import random
import json
import itertools
import collections

# Set the seed for reproducibility
torch.manual_seed(0)

# --- Part 1: Image Tensor Creation and Permutation ---

# Create a small image tensor with shape [B, H, W, C]
# B=2 (batch size), H=3 (height), W=4 (width), C=3 (channels: RGB)
# Values are random integers between 0 and 255, typical for uint8 images
image_bhwc = torch.randint(0, 256, (2, 3, 4, 3), dtype=torch.uint8)

# Print the shape of the original tensor
print(f"RESULT shape_bhwc = {image_bhwc.shape}")

# Permute the tensor to [B, C, H, W] which is the standard format for PyTorch convolutions
# dims: 0->0 (B), 3->1 (C), 1->2 (H), 2->3 (W)
image_bchw = image_bhwc.permute(0, 3, 1, 2)

# Print the shape after permutation
print(f"RESULT shape_bchw = {image_bchw.shape}")

# Permute back to [B, H, W, C] to verify we can reverse the operation
# dims: 0->0 (B), 2->1 (H), 3->2 (W), 1->3 (C)
image_bhwc_back = image_bchw.permute(0, 2, 3, 1)

# Print the shape after permuting back
print(f"RESULT shape_bhwc_back = {image_bhwc_back.shape}")

# Assert that the tensor values are identical after permuting back and forth
assert torch.equal(image_bhwc, image_bhwc_back), "Permutation back and forth should preserve values"

# --- Part 2: uint8 vs float32 Scaling ---

# Convert the original uint8 tensor to float32
# This keeps the values as 0-255 but in floating point
image_float_0_255 = image_bhwc.float()

# Print the min and max values of the float tensor (should be 0 and 255)
print(f"RESULT float_min_0_255 = {image_float_0_255.min().item():.6g}")
print(f"RESULT float_max_0_255 = {image_float_0_255.max().item():.6g}")

# Scale the float tensor to the range [0, 1] by dividing by 255
image_float_0_1 = image_float_0_255 / 255.0

# Print the min and max values of the scaled tensor (should be 0 and 1)
print(f"RESULT float_min_0_1 = {image_float_0_1.min().item():.6g}")
print(f"RESULT float_max_0_1 = {image_float_0_1.max().item():.6g}")

# --- Part 3: Clamping Out-of-Range Values ---

# Create a small float tensor with values outside the [0, 1] range
# This simulates what might happen after some operations like normalization
out_of_range_tensor = torch.tensor([-0.5, 0.2, 0.8, 1.5, 0.0, 1.0], dtype=torch.float32)

# Print the original out-of-range values
print(f"RESULT out_of_range_original = {out_of_range_tensor.tolist()}")

# Clamp the values to the range [0, 1]
# Values below 0 become 0, values above 1 become 1
clamped_tensor = torch.clamp(out_of_range_tensor, min=0.0, max=1.0)

# Print the clamped values
print(f"RESULT clamped_values = {clamped_tensor.tolist()}")

# Assert that clamping works as expected
# The first value (-0.5) should become 0.0
# The fourth value (1.5) should become 1.0
assert clamped_tensor[0].item() == 0.0, "Negative values should be clamped to 0"
assert clamped_tensor[3].item() == 1.0, "Values above 1 should be clamped to 1"

# Verify that values within range are unchanged using approximate comparison
# to avoid floating-point precision issues
assert math.isclose(clamped_tensor[1].item(), 0.2, rel_tol=1e-5), "Values within range should remain unchanged"
assert math.isclose(clamped_tensor[2].item(), 0.8, rel_tol=1e-5), "Values within range should remain unchanged"

# Print a summary of the concepts covered
print("RESULT concepts_covered = [permutation, scaling, clamping]")
