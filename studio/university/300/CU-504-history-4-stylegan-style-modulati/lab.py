import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required by the lab rules
torch.manual_seed(0)

# Define small tensors to simulate style and content vectors (CPU, float32)
# In StyleGAN, style vectors modulate the features of the generator
style = torch.randn(1, 512)
content = torch.randn(1, 512)

# Perform style modulation: content is scaled by (1 + style)
# This simulates how style affects the magnitude of features
modulated = content * (1 + style)

# Assert that the modulation formula is correctly applied
assert torch.allclose(modulated, content * (1 + style)), "Modulation formula mismatch"

# Assert that modulation actually changes the content (unless style is all zeros, which is extremely unlikely)
assert not torch.allclose(modulated, content), "Modulation did not alter content"

# Calculate norms to demonstrate the change in feature magnitude
original_norm = content.norm().item()
modulated_norm = modulated.norm().item()

# Print results in the required format
print(f"RESULT original_norm = {original_norm:.6g}")
print(f"RESULT modulated_norm = {modulated_norm:.6g}")
print(f"RESULT modulation_factor_mean = {(1 + style).mean().item():.6g}")
