import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Create a simple 3x3 grayscale image with a vertical edge
# Left column is dark (0), right columns are bright (1)
img = torch.tensor([
    [0.0, 1.0, 1.0],
    [0.0, 1.0, 1.0],
    [0.0, 1.0, 1.0]
], dtype=torch.float32).unsqueeze(0).unsqueeze(0)  # Shape: (1, 1, 3, 3)

# Define Sobel kernels for horizontal (Gx) and vertical (Gy) gradients
# Standard Sobel kernels
kx = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32).view(1, 1, 3, 3)
ky = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32).view(1, 1, 3, 3)

# Apply convolution with padding to maintain size
# F.conv2d expects input (N, C, H, W) and weight (out_channels, in_channels/groups, kH, kW)
# We use padding=1 to keep the output size the same as input (3x3)
gx = torch.nn.functional.conv2d(img, kx, padding=1)
gy = torch.nn.functional.conv2d(img, ky, padding=1)

# Compute magnitude of the gradient
magnitude = torch.sqrt(gx ** 2 + gy ** 2)

# Print results
print(f"RESULT gx_center = {gx[0, 0, 1, 1].item():.6g}")
print(f"RESULT gy_center = {gy[0, 0, 1, 1].item():.6g}")
print(f"RESULT magnitude_center = {magnitude[0, 0, 1, 1].item():.6g}")

# Assert that the horizontal gradient at the center is non-zero (edge detected)
assert gx[0, 0, 1, 1].item() != 0.0, "Horizontal gradient should be non-zero at the edge"

# Assert that the vertical gradient at the center is zero (no vertical edge)
assert gy[0, 0, 1, 1].item() == 0.0, "Vertical gradient should be zero for a vertical edge"
