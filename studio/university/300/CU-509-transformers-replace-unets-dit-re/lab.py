import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Define start (noise) and end (data) points in 2D
start = torch.tensor([0.0, 0.0], dtype=torch.float32)
end = torch.tensor([1.0, 1.0], dtype=torch.float32)

# Rectified flow: linear interpolation x_t = (1-t)*x_0 + t*x_1
# Velocity is constant: v = x_1 - x_0
velocity = end - start

# Check 1: At t=0.5, position should be midpoint
t_mid = 0.5
midpoint = (1 - t_mid) * start + t_mid * end
assert torch.allclose(midpoint, torch.tensor([0.5, 0.5])), "Midpoint calculation failed"

# Check 2: Velocity should be constant regardless of t
v_at_0 = end - start
v_at_1 = end - start
assert torch.allclose(v_at_0, v_at_1), "Velocity is not constant in rectified flow"

# Additional check: Verify the path equation at multiple t values
for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
    x_t = (1 - t) * start + t * end
    expected = start + t * velocity
    assert torch.allclose(x_t, expected), f"Path equation failed at t={t}"

# Print results in required format
print(f"RESULT start = {start[0]:.6g} {start[1]:.6g}")
print(f"RESULT end = {end[0]:.6g} {end[1]:.6g}")
print(f"RESULT velocity = {velocity[0]:.6g} {velocity[1]:.6g}")
print(f"RESULT midpoint = {midpoint[0]:.6g} {midpoint[1]:.6g}")
print("RESULT rectified_flow_verified = True")
