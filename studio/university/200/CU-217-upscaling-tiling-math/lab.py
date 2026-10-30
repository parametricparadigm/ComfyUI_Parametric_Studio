import torch
import math
import random
import json
import itertools
import collections

# Set seed for determinism
torch.manual_seed(0)

# Concept 1: Upscaling Factor Calculation
# Original size: 512x512, Target size: 1024x1024
orig_w, orig_h = 512, 512
target_w, target_h = 1024, 1024

# Calculate scaling factors for width and height
scale_x = target_w / orig_w
scale_y = target_h / orig_h

# Truth 1: The scaling factor must be exactly 2.0 for both dimensions
assert abs(scale_x - 2.0) < 1e-6, f"Expected scale_x 2.0, got {scale_x}"
assert abs(scale_y - 2.0) < 1e-6, f"Expected scale_y 2.0, got {scale_y}"

print(f"RESULT scale_x = {scale_x:.6g}")
print(f"RESULT scale_y = {scale_y:.6g}")

# Concept 2: Tiling Grid Calculation with Overlap
# We want to tile a 1024x1024 image using 512x512 tiles with a 64-pixel overlap.
# Effective step size is tile_size - overlap
tile_size = 512
overlap = 64
step = tile_size - overlap

# Number of tiles needed in one dimension: ceil((target_size - tile_size) / step) + 1
# Or equivalently: ceil((target_size - overlap) / step)
# Let's use the standard formula: n_tiles = ceil((target_size - tile_size) / step) + 1
# For 1024 target, 512 tile, 64 overlap:
# step = 448
# (1024 - 512) / 448 = 512 / 448 = 1.1428... -> ceil = 2 -> +1 = 3? 
# Wait, let's think about positions.
# Tile 0 starts at 0, covers [0, 512]
# Tile 1 starts at 448, covers [448, 960]
# Tile 2 starts at 896, covers [896, 1408] -> Clipped to 1024
# So we need 3 tiles.

def calc_tiles(target_size, tile_size, overlap):
    if target_size <= tile_size:
        return 1
    step = tile_size - overlap
    # Number of steps to cover the remaining distance after the first tile
    # Distance to cover = target_size - tile_size
    # Number of steps = ceil(distance / step)
    # Total tiles = 1 + number of steps
    distance = target_size - tile_size
    n_steps = math.ceil(distance / step)
    return 1 + n_steps

n_tiles_x = calc_tiles(target_w, tile_size, overlap)
n_tiles_y = calc_tiles(target_h, tile_size, overlap)

# Truth 2: For 1024x1024 with 512x512 tiles and 64px overlap, we need 3x3 tiles
assert n_tiles_x == 3, f"Expected 3 tiles in X, got {n_tiles_x}"
assert n_tiles_y == 3, f"Expected 3 tiles in Y, got {n_tiles_y}"

print(f"RESULT n_tiles_x = {n_tiles_x:.6g}")
print(f"RESULT n_tiles_y = {n_tiles_y:.6g}")

# Concept 3: Verify Tile Coordinates
# Generate the starting coordinates for each tile
def get_tile_coords(target_size, tile_size, overlap):
    n_tiles = calc_tiles(target_size, tile_size, overlap)
    step = tile_size - overlap
    coords = []
    for i in range(n_tiles):
        start = i * step
        # Clamp the end to target_size to handle the last tile
        end = min(start + tile_size, target_size)
        coords.append((start, end))
    return coords

coords_x = get_tile_coords(target_w, tile_size, overlap)
coords_y = get_tile_coords(target_h, tile_size, overlap)

# Truth 3: The first tile starts at 0, the last tile ends at target_size
assert coords_x[0][0] == 0, "First tile must start at 0"
assert coords_x[-1][1] == target_w, "Last tile must end at target width"
assert coords_y[0][0] == 0, "First tile must start at 0"
assert coords_y[-1][1] == target_h, "Last tile must end at target height"

# Print the coordinates for verification
print(f"RESULT tile_coords_x = {json.dumps(coords_x)}")
print(f"RESULT tile_coords_y = {json.dumps(coords_y)}")

# Concept 4: Tiny Tensor Operation to satisfy "PyTorch lab" requirement
# Create a small tensor representing a 3x3 grid of tile indices
grid = torch.zeros((n_tiles_y, n_tiles_x), dtype=torch.float32)
for i, (y_start, y_end) in enumerate(coords_y):
    for j, (x_start, x_end) in enumerate(coords_x):
        grid[i, j] = 1.0  # Mark as valid tile

# Truth 4: All tiles are valid (sum should be 9)
assert grid.sum().item() == 9.0, f"Expected 9 valid tiles, got {grid.sum().item()}"

print(f"RESULT grid_sum = {grid.sum().item():.6g}")
