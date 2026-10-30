import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required
torch.manual_seed(0)

# Define hyperparameters for a simple convolutional layer
kernel_size = 3
stride = 2
dilation = 1

# Calculate the receptive field of a single layer
# Formula: (kernel_size - 1) * dilation + 1
receptive_field = (kernel_size - 1) * dilation + 1
print(f"RESULT single_layer_rf = {receptive_field}")

# Assert that the base receptive field calculation is correct
assert receptive_field == 3, "Base receptive field calculation failed"

# Calculate cumulative receptive field after 2 layers
# The receptive field grows as we stack layers
# For layer i (0-indexed), the contribution is (kernel_size - 1) * dilation * (stride ** i)
# However, the standard formula for cumulative RF with stride is:
# RF_total = 1 + sum_{i=0}^{L-1} (kernel_size - 1) * dilation * (stride ** i)
# But the prompt's example uses (2 ** i) which implies stride=2 in the growth factor
# Let's follow the prompt's logic: total_rf = 1 + sum((k-1)*d*(2**i) for i in range(2))
total_rf = 1
for i in range(2):
    total_rf = total_rf + (kernel_size - 1) * dilation * (2 ** i)

print(f"RESULT total_rf_2_layers = {total_rf}")

# Assert that the cumulative receptive field calculation is correct
assert total_rf == 7, "Cumulative receptive field calculation failed"

# Demonstrate with a tiny tensor to show how spatial dimensions change
# Input: 1 batch, 1 channel, 7x7 spatial
x = torch.randn(1, 1, 7, 7, dtype=torch.float32)

# Create a simple conv layer (CPU only, float32)
conv = torch.nn.Conv2d(1, 1, kernel_size=3, stride=stride, padding=0, dilation=dilation)

# Forward pass
y = conv(x)

# Calculate expected output spatial size
# Formula: floor((H + 2*padding - dilation*(kernel_size-1) - 1) / stride) + 1
H_in = 7
H_out = math.floor((H_in + 2*0 - dilation*(kernel_size-1) - 1) / stride) + 1

print(f"RESULT input_spatial = {H_in}")
print(f"RESULT output_spatial = {H_out}")

# Assert that the output spatial dimension matches our calculation
assert y.shape[2] == H_out, "Output spatial dimension calculation failed"

# Verify that the receptive field concept holds:
# With RF=7 after 2 layers, a center pixel in the final output
# should depend on 7 pixels in the original input
# We can verify this by checking that changing pixels outside the RF
# doesn't affect the center output pixel

# Create a second input that differs only outside the receptive field
x2 = x.clone()
# The center of the 7x7 input is at (3,3)
# After 2 conv layers with stride 2, the center of output is at (1,1)
# The receptive field of 7 means it covers input pixels from (3-3) to (3+3) = 0 to 6
# So actually the entire 7x7 input is within the RF for the center pixel
# Let's use a larger input to make this clearer

x_large = torch.randn(1, 1, 11, 11, dtype=torch.float32)
x_large2 = x_large.clone()

# Modify a pixel far outside the receptive field of the center
# Center of 11x11 is (5,5)
# RF=7 means it covers (5-3) to (5+3) = 2 to 8
# So pixel (0,0) is outside the RF
x_large2[0, 0, 0, 0] += 100.0

y_large = conv(conv(x_large))
y_large2 = conv(conv(x_large2))

# The center pixel of the output should be the same
center_idx = (0, 0, 1, 1)  # batch, channel, h, w for 3x3 output from 11x11 input
center_val1 = y_large[center_idx].item()
center_val2 = y_large2[center_idx].item()

print(f"RESULT center_pixel_1 = {center_val1:.6g}")
print(f"RESULT center_pixel_2 = {center_val2:.6g}")

# Assert that the center pixel is unchanged (within floating point tolerance)
assert abs(center_val1 - center_val2) < 1e-5, "Receptive field isolation failed"
