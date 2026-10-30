import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# --- Part 1: Frame counts for durations and fps ---
# Formula: frames = duration_seconds * fps
# Example: 5 seconds at 24 fps
duration_5s = 5
fps_24 = 24
frames_5s_24fps = duration_5s * fps_24
print(f"RESULT frames_5s_24fps = {frames_5s_24fps}")

# Another example: 2 seconds at 30 fps
duration_2s = 2
fps_30 = 30
frames_2s_30fps = duration_2s * fps_30
print(f"RESULT frames_2s_30fps = {frames_2s_30fps}")

# --- Part 2: Temporal VAE with 4x time compression and 8x spatial compression ---
# The "4k+1 frame rule" means that for temporal compression by factor 4,
# the number of input frames must be of the form 4k + 1 to align properly.
# Let's check if 121 frames satisfies this: 121 = 4*30 + 1 -> yes
input_frames = 121
k = (input_frames - 1) // 4
is_4k_plus_1_121 = (4 * k + 1 == input_frames)
print(f"RESULT is_4k_plus_1_121 = {is_4k_plus_1_121}")

# Check another number: 120 frames
input_frames_120 = 120
k_120 = (input_frames_120 - 1) // 4
is_4k_plus_1_120 = (4 * k_120 + 1 == input_frames_120)
print(f"RESULT is_4k_plus_1_120 = {is_4k_plus_1_120}")

# --- Part 3: Latent sizes for 5 s at 24 fps 768x512 ---
# Input: 5s * 24fps = 120 frames, but we need 4k+1, so let's use 121 frames (approx 5.04s)
# Actually, let's stick to the exact 120 frames for calculation, but note that VAEs often pad.
# For this lab, let's assume we use 121 frames to satisfy the 4k+1 rule for a ~5s clip.
# Spatial: 768x512, compressed by 8x -> 768/8 = 96, 512/8 = 64
# Temporal: 121 frames, compressed by 4x -> (121-1)/4 + 1 = 31 latent frames
# Latent shape: (C, T_latent, H_latent, W_latent) where C is latent channels (assume 4 for simplicity)
latent_channels = 4
T_latent = (121 - 1) // 4 + 1
H_latent = 768 // 8
W_latent = 512 // 8
latent_size = latent_channels * T_latent * H_latent * W_latent
print(f"RESULT latent_size_5s_24fps_768x512 = {latent_size}")

# --- Part 4: Attention cost scaling ---
# Full attention cost is O(N^2) where N is the number of tokens.
# If we double the number of frames, N doubles, so cost becomes (2N)^2 = 4N^2.
# Let's demonstrate with a small tensor.
N_original = 10
N_doubled = 2 * N_original
cost_original = N_original ** 2
cost_doubled = N_doubled ** 2
ratio = cost_doubled / cost_original
print(f"RESULT attention_cost_ratio = {ratio}")

# Assertions to check concepts
assert is_4k_plus_1_121 == True, "121 should satisfy 4k+1 rule"
assert ratio == 4.0, "Doubling frames should multiply attention cost by 4"

# Additional check: latent dimensions
assert T_latent == 31, "Temporal latent should be 31 for 121 input frames"
assert H_latent == 96 and W_latent == 64, "Spatial latents should be 96x64"
