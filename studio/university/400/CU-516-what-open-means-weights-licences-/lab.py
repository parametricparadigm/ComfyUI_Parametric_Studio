import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility (as required by the lab rules)
torch.manual_seed(0)
random.seed(0)

# --- Concept: Open vs Closed Ecosystems ---
# In this lab, we simulate the "openness" of a model using simple tensor operations.
# "Open" models have shared weights (high transparency), "Closed" models do not.
# We use a small tensor to represent "weight transparency" scores.

# Step 1: Create a small tensor representing model weight transparency scores.
# Each value is between 0 and 1, simulating how "open" a component is.
# We use float32 on CPU as required.
transparency_scores = torch.tensor([0.8, 0.9, 0.7, 0.95, 0.85], dtype=torch.float32)

# Step 2: Define a threshold for "open" status.
# If the average transparency is above 0.75, we consider the model "open".
threshold = 0.75

# Step 3: Calculate the average transparency score.
avg_transparency = torch.mean(transparency_scores).item()

# Step 4: Determine if the model is "open" based on the threshold.
is_open = avg_transparency > threshold

# Step 5: Simulate a "license compatibility" check using a simple rule.
# Open models (Apache 2.0, MIT) allow redistribution. We simulate this by checking
# if all scores are above a minimum (e.g., 0.5). If any score is too low, it's "closed".
min_score = 0.5
all_components_open = torch.all(transparency_scores >= min_score).item()

# Step 6: Combine both checks to determine final "open ecosystem" status.
# A model is considered part of an "open ecosystem" if it is open AND all components are open.
open_ecosystem = is_open and all_components_open

# Step 7: Calculate a "reproducibility score" using the variance of transparency.
# Lower variance means more consistent openness, which is a hallmark of open standards.
variance = torch.var(transparency_scores).item()
reproducibility_score = 1.0 / (1.0 + variance)  # Higher score = more reproducible

# Step 8: Simulate a "community contribution" metric using a simple sum.
# This represents the number of contributors (simulated as the sum of scores).
community_score = torch.sum(transparency_scores).item()

# --- Assertions to verify the concept holds ---
# Assert 1: The average transparency should be above the threshold for an "open" model.
assert is_open, "Model should be considered open based on average transparency."

# Assert 2: The reproducibility score should be between 0 and 1.
assert 0.0 < reproducibility_score < 1.0, "Reproducibility score must be between 0 and 1."

# --- Print results in the required format ---
print(f"RESULT avg_transparency = {avg_transparency:.6g}")
print(f"RESULT is_open = {is_open}")
print(f"RESULT all_components_open = {all_components_open}")
print(f"RESULT open_ecosystem = {open_ecosystem}")
print(f"RESULT reproducibility_score = {reproducibility_score:.6g}")
print(f"RESULT community_score = {community_score:.6g}")
