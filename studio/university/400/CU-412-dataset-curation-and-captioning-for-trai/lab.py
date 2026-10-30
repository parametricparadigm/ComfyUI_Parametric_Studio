import torch
import math
import random
import json
import itertools
import collections

# Set seeds for reproducibility
torch.manual_seed(0)
random.seed(42)

# Step 1: Define a small dataset of captions
captions = ["a red car", "a blue sky", "a red car", "a green tree", "a red car"]

# Step 2: Count the frequency of each caption
freq = {}
for c in captions:
    freq[c] = freq.get(c, 0) + 1

# Step 3: Find the maximum frequency
max_freq = max(freq.values())

# Step 4: Identify captions with the maximum frequency (most frequent)
balanced = [c for c, f in freq.items() if f == max_freq]

# Step 5: Print original counts and most frequent caption
print(f"Original counts: {freq}")
print(f"Most frequent caption: {balanced[0]} with count {max_freq}")

# Step 6: Assert that the most frequent caption is "a red car"
assert balanced[0] == "a red car", "Most frequent caption should be 'a red car'"

# Step 7: Assert that the maximum frequency is 3
assert max_freq == 3, "Maximum frequency should be 3"

# Step 8: Create a tiny tensor representing caption frequencies
# Convert frequencies to a tensor for demonstration
freq_values = torch.tensor(list(freq.values()), dtype=torch.float32)

# Step 9: Normalize the frequencies to sum to 1 (probability distribution)
total = freq_values.sum()
normalized_freqs = freq_values / total

# Step 10: Print the normalized frequencies as RESULT lines
for caption, norm_freq in zip(freq.keys(), normalized_freqs):
    print(f"RESULT norm_freq_{caption.replace(' ', '_')} = {norm_freq.item():.6g}")

# Step 11: Assert that the normalized frequencies sum to approximately 1
assert abs(normalized_freqs.sum().item() - 1.0) < 1e-6, "Normalized frequencies should sum to 1"

# Step 12: Demonstrate simple balancing by sampling without replacement
# Create a balanced sample where each unique caption appears once
unique_captions = list(freq.keys())
random.shuffle(unique_captions)
balanced_sample = unique_captions[:min(len(unique_captions), 3)]  # Take up to 3 unique captions

# Step 13: Print the balanced sample
print(f"RESULT balanced_sample = {balanced_sample}")

# Step 14: Assert that the balanced sample contains no duplicates
assert len(balanced_sample) == len(set(balanced_sample)), "Balanced sample should have no duplicates"
