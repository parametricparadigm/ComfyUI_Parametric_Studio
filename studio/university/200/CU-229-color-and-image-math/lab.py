import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define sRGB to linear conversion
def srgb_to_linear(x):
    """
    Convert sRGB values (0-1) to linear light values.
    sRGB uses a gamma-like curve for perceptual uniformity.
    """
    # Piecewise function: linear for small values, power law for larger
    return torch.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)

# Define linear to sRGB conversion
def linear_to_srgb(x):
    """
    Convert linear light values to sRGB values (0-1).
    This is the inverse of srgb_to_linear.
    """
    # Piecewise function: linear for small values, power law for larger
    return torch.where(x <= 0.0031308, 12.92 * x, 1.055 * (x ** (1 / 2.4)) - 0.055)

# Test 1: Blend black and white 50/50 in sRGB space vs linear space
# Black = 0.0, White = 1.0 in sRGB
black_srgb = torch.tensor([0.0], dtype=torch.float32)
white_srgb = torch.tensor([1.0], dtype=torch.float32)

# Blend in sRGB space: average the sRGB values directly
blend_srgb_space = 0.5 * black_srgb + 0.5 * white_srgb
# Result should be 0.5 in sRGB space

# Blend in linear space: convert to linear, average, convert back
black_linear = srgb_to_linear(black_srgb)
white_linear = srgb_to_linear(white_srgb)
blend_linear_space = 0.5 * black_linear + 0.5 * white_linear
# Convert back to sRGB
blend_linear_to_srgb = linear_to_srgb(blend_linear_space)

# Print results
print(f"RESULT blend_srgb_space = {blend_srgb_space.item():.6g}")
print(f"RESULT blend_linear_to_srgb = {blend_linear_to_srgb.item():.6g}")

# Assert that blending in linear space gives a lighter result than sRGB space
# This is because linear space represents actual light intensity, and the sRGB curve
# compresses highlights, so the linear midpoint appears brighter when converted back
assert blend_linear_to_srgb.item() > blend_srgb_space.item(), "Linear blend should be lighter than sRGB blend"

# Test 2: Show that a gradient averaged both ways differs measurably
# Create a gradient from black to white in sRGB space
num_steps = 10
srgb_gradient = torch.linspace(0.0, 1.0, num_steps, dtype=torch.float32)

# Convert to linear space
linear_gradient = srgb_to_linear(srgb_gradient)

# Average the gradient in sRGB space
avg_srgb = torch.mean(srgb_gradient)

# Average the gradient in linear space, then convert back to sRGB
avg_linear = torch.mean(linear_gradient)
avg_linear_to_srgb = linear_to_srgb(torch.tensor([avg_linear], dtype=torch.float32))

# Print results
print(f"RESULT avg_srgb_gradient = {avg_srgb.item():.6g}")
print(f"RESULT avg_linear_to_srgb = {avg_linear_to_srgb.item():.6g}")

# Assert that the two averages are measurably different
# The difference should be significant enough to detect
diff = abs(avg_srgb.item() - avg_linear_to_srgb.item())
assert diff > 0.01, "The two averaging methods should give measurably different results"

# Additional verification: check that sRGB to linear and back is identity
test_values = torch.tensor([0.0, 0.1, 0.5, 0.9, 1.0], dtype=torch.float32)
roundtrip = linear_to_srgb(srgb_to_linear(test_values))
max_error = torch.max(torch.abs(test_values - roundtrip)).item()
print(f"RESULT roundtrip_max_error = {max_error:.6g}")
assert max_error < 1e-5, "sRGB to linear and back should be approximately identity"
