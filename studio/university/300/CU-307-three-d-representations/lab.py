import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# --- Step 1: Define the Sphere SDF ---
# A sphere of radius r centered at the origin has SDF: d(x) = ||x|| - r
# Inside: d < 0, Outside: d > 0, Surface: d = 0
r = 1.0
grid_size = 32
# Grid spans [-1.5, 1.5] to fully contain the sphere (radius 1.0)
# We use linspace to create 32 points in each dimension
coords = torch.linspace(-1.5, 1.5, grid_size)
# Create a 3D grid of coordinates
x, y, z = torch.meshgrid(coords, coords, coords, indexing='ij')
# Stack into a single tensor of shape (32, 32, 32, 3)
grid_points = torch.stack([x, y, z], dim=-1)

# Compute SDF values: distance to origin minus radius
dist_to_origin = torch.norm(grid_points, dim=-1)
sdf_values = dist_to_origin - r

# --- Step 2: Find Voxels Near the Surface ---
# A voxel is "near the surface" if its center is within a small threshold of 0
# We use a threshold slightly larger than the voxel size to capture boundary voxels
# Voxel size: (1.5 - (-1.5)) / (32 - 1) = 3.0 / 31 ≈ 0.0968
voxel_size = 3.0 / (grid_size - 1)
threshold = voxel_size * 0.5  # Half voxel size as a reasonable threshold

# Boolean mask: True where |sdf| < threshold
surface_mask = torch.abs(sdf_values) < threshold

# --- Step 3: Estimate Surface Area from Voxel Faces ---
# For each surface voxel, we check its 6 neighbors.
# If a neighbor is outside the surface (|sdf| >= threshold) or out of bounds,
# we count that face as contributing to the surface area.
# Each face has area = voxel_size^2

surface_area = 0.0
count_faces = 0

# Iterate over all voxels
for i in range(grid_size):
    for j in range(grid_size):
        for k in range(grid_size):
            if not surface_mask[i, j, k]:
                continue
            
            # Check 6 neighbors: +/- x, +/- y, +/- z
            # Neighbor offsets
            neighbors = [
                (i-1, j, k), (i+1, j, k),
                (i, j-1, k), (i, j+1, k),
                (i, j, k-1), (i, j, k+1)
            ]
            
            for (ni, nj, nk) in neighbors:
                # Check if neighbor is out of bounds
                if ni < 0 or ni >= grid_size or nj < 0 or nj >= grid_size or nk < 0 or nk >= grid_size:
                    # Out of bounds: assume outside the surface (contributes to area)
                    surface_area += voxel_size ** 2
                    count_faces += 1
                else:
                    # Check if neighbor is NOT on the surface
                    if not surface_mask[ni, nj, nk]:
                        surface_area += voxel_size ** 2
                        count_faces += 1

# --- Step 4: Compare to Analytical Area ---
analytical_area = 4 * math.pi * r ** 2

# --- Step 5: Show Why Coarse Grid Underestimates Smoothness ---
# A coarse grid approximates the sphere with blocky voxels.
# The estimated area is the sum of flat voxel faces, which overestimates the true curved surface
# in terms of "staircase" effect, but actually for a sphere, the voxel-based area tends to
# overestimate because it counts all exposed faces. However, the question says "underestimates smoothness".
# Let's clarify: The voxel method gives a "staircase" approximation. The area computed is the area of the
# polyhedral surface formed by voxel faces. For a sphere, this polyhedral area is actually LARGER than
# the true sphere area because the staircase surface has more area than the smooth sphere.
# Wait, let's re-read: "show why a coarse grid underestimates smoothness".
# Perhaps it means the grid cannot capture the smooth curvature, leading to a jagged surface.
# The area estimate from voxels is typically an overestimate of the true area for convex shapes like spheres.
# Let's compute the ratio.

ratio = surface_area / analytical_area

# --- Assertions ---
# 1. The surface mask should find some voxels
assert surface_mask.sum() > 0, "No surface voxels found"

# 2. The estimated area should be in a reasonable range (not zero, not absurdly large)
# For a sphere of radius 1, analytical area is ~12.566.
# Voxel area should be somewhat close, typically overestimating for coarse grids.
assert surface_area > 0, "Surface area must be positive"
assert surface_area < 100, "Surface area seems unreasonably large"

# --- Print Results ---
print(f"RESULT grid_size = {grid_size}")
print(f"RESULT voxel_size = {voxel_size:.6g}")
print(f"RESULT surface_voxel_count = {surface_mask.sum().item()}")
print(f"RESULT estimated_surface_area = {surface_area:.6g}")
print(f"RESULT analytical_surface_area = {analytical_area:.6g}")
print(f"RESULT area_ratio = {ratio:.6g}")
print(f"RESULT relative_error = {(surface_area - analytical_area) / analytical_area:.6g}")
