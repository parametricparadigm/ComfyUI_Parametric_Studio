import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define image dimensions (must be divisible by 8 for VAE downsampling)
H = 64
W = 64
latent_channels = 4
text_channels = 768
text_seq_len = 77
num_steps = 5

# 1. Simulate text embedding shape: [1, 77, 768]
text_emb = torch.randn(1, text_seq_len, text_channels)
print(f"RESULT text_emb_shape = {tuple(text_emb.shape)}")
text_elements = text_emb.numel()
print(f"RESULT text_elements = {text_elements}")

# 2. Simulate empty latent shape: [1, 4, H/8, W/8]
latent_h = H // 8
latent_w = W // 8
latent = torch.randn(1, latent_channels, latent_h, latent_w)
print(f"RESULT latent_shape = {tuple(latent.shape)}")
latent_elements = latent.numel()
print(f"RESULT latent_elements = {latent_elements}")

# Calculate compression factor from original image size to latent size
# Original image would be [1, 3, H, W]
image_elements = 1 * 3 * H * W
compression_factor = image_elements / latent_elements
print(f"RESULT compression_factor = {compression_factor:.6g}")

# 3. Simulate N denoising steps
# Stand-in update rule: shrink the noise (multiply by a decay factor each step)
# In real diffusion, this involves predicting noise and subtracting it
decay_factor = 0.5
current_latent = latent.clone()

for step in range(num_steps):
    # Simulate denoising: reduce the magnitude of the latent (noise)
    current_latent = current_latent * decay_factor
    print(f"RESULT step_{step}_latent_norm = {current_latent.norm().item():.6g}")

# 4. Simulate decoder upsampling x8 to [1, 3, H, W]
# In a real VAE decoder, this is a learned upsampling operation
# Here we just interpolate to show the shape change
decoded = torch.nn.functional.interpolate(
    current_latent, 
    size=(H, W), 
    mode='nearest'
)
# Change channels from 4 to 3 to simulate RGB output
# In reality, the decoder learns this mapping
decoded = decoded[:, :3, :, :]  # Take first 3 channels as stand-in for RGB
print(f"RESULT decoded_shape = {tuple(decoded.shape)}")
decoded_elements = decoded.numel()
print(f"RESULT decoded_elements = {decoded_elements}")

# Assertions to verify the concept holds
# Check that latent is indeed 1/8 the spatial size of the original image
assert latent.shape[2] == H // 8 and latent.shape[3] == W // 8, "Latent spatial dimensions should be H/8 and W/8"

# Check that the decoded image has the original spatial dimensions
assert decoded.shape[2] == H and decoded.shape[3] == W, "Decoded image should have original spatial dimensions"

# Check that compression factor is reasonable (should be > 1)
assert compression_factor > 1, "Compression factor should be greater than 1"

# Check that denoising reduced the norm
assert current_latent.norm().item() < latent.norm().item(), "Denoising should reduce the latent norm"

print("RESULT all_assertions_passed = True")
