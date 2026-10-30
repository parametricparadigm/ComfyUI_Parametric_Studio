import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Define a small 2D grid of coordinates
# Shape: (batch_size, height, width, 2) where last dim is (x, y)
batch_size = 1
h, w = 4, 4
coords = torch.zeros(batch_size, h, w, 2)
for i in range(h):
    for j in range(w):
        coords[0, i, j, 0] = j  # x coordinate
        coords[0, i, j, 1] = i  # y coordinate

# Function to compute sinusoidal positional encoding
# Simplified for 2D: encode x and y separately then concatenate
# Formula: [sin(x * f), cos(x * f), sin(y * f), cos(y * f)] for a single frequency f
# In real ComfyUI/SD, multiple frequencies are used, but we use one for clarity.
freq = 1.0

def encode_2d(coords):
    x = coords[..., 0]
    y = coords[..., 1]
    # Compute sin/cos for x and y
    enc_x = torch.stack([torch.sin(x * freq), torch.cos(x * freq)], dim=-1)
    enc_y = torch.stack([torch.sin(y * freq), torch.cos(y * freq)], dim=-1)
    # Concatenate x and y encodings along the last dimension
    return torch.cat([enc_x, enc_y], dim=-1)

# Compute the 2D positional encoding
enc_2d = encode_2d(coords)

# Print the shape of the encoding
print(f"RESULT enc_2d_shape = {enc_2d.shape}")

# Print the first few values of the encoding
print(f"RESULT enc_2d_first = {enc_2d[0, 0, 0].tolist()}")

# Check that the encoding has the correct shape
assert enc_2d.shape == (batch_size, h, w, 4), "Encoding shape should be (batch, h, w, 4)"

# Check that the encoding values are within the range [-1, 1]
assert torch.all(enc_2d >= -1.0) and torch.all(enc_2d <= 1.0), "Encoding values should be in [-1, 1]"

# Define a small 3D grid of coordinates
# Shape: (batch_size, depth, height, width, 3) where last dim is (x, y, z)
d = 2
coords_3d = torch.zeros(batch_size, d, h, w, 3)
for k in range(d):
    for i in range(h):
        for j in range(w):
            coords_3d[0, k, i, j, 0] = j  # x coordinate
            coords_3d[0, k, i, j, 1] = i  # y coordinate
            coords_3d[0, k, i, j, 2] = k  # z coordinate

# Function to compute sinusoidal positional encoding for 3D
# Formula: [sin(x * f), cos(x * f), sin(y * f), cos(y * f), sin(z * f), cos(z * f)]
def encode_3d(coords):
    x = coords[..., 0]
    y = coords[..., 1]
    z = coords[..., 2]
    # Compute sin/cos for x, y, and z
    enc_x = torch.stack([torch.sin(x * freq), torch.cos(x * freq)], dim=-1)
    enc_y = torch.stack([torch.sin(y * freq), torch.cos(y * freq)], dim=-1)
    enc_z = torch.stack([torch.sin(z * freq), torch.cos(z * freq)], dim=-1)
    # Concatenate x, y, and z encodings along the last dimension
    return torch.cat([enc_x, enc_y, enc_z], dim=-1)

# Compute the 3D positional encoding
enc_3d = encode_3d(coords_3d)

# Print the shape of the 3D encoding
print(f"RESULT enc_3d_shape = {enc_3d.shape}")

# Print the first few values of the 3D encoding
print(f"RESULT enc_3d_first = {enc_3d[0, 0, 0, 0].tolist()}")

# Check that the 3D encoding has the correct shape
assert enc_3d.shape == (batch_size, d, h, w, 6), "3D encoding shape should be (batch, d, h, w, 6)"

# Check that the 3D encoding values are within the range [-1, 1]
assert torch.all(enc_3d >= -1.0) and torch.all(enc_3d <= 1.0), "3D encoding values should be in [-1, 1]"
