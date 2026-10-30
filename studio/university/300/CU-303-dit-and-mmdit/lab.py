import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# 1. Patchify a [1,4,16,16] latent into 2x2 patches
# Input shape: [batch, channels, height, width]
latent = torch.randn(1, 4, 16, 16)

# Patch size is 2x2
patch_h, patch_w = 2, 2

# Calculate number of patches in height and width
num_patches_h = latent.shape[2] // patch_h
num_patches_w = latent.shape[3] // patch_w

# Total number of tokens (patches)
num_tokens = num_patches_h * num_patches_w

# Reshape to extract patches
# Original: [1, 4, 16, 16]
# We want to group into 2x2 spatial blocks
# Reshape to [1, 4, 8, 2, 8, 2] where 8=16/2, 2=patch_size
# Then permute to [1, 8, 8, 4, 2, 2] to group spatial dims together
# Then reshape to [1, 64, 4*2*2] = [1, 64, 16]
x = latent.reshape(1, 4, num_patches_h, patch_h, num_patches_w, patch_w)
x = x.permute(0, 2, 4, 1, 3, 5)  # [1, num_patches_h, num_patches_w, C, ph, pw]
x = x.reshape(1, num_tokens, 4 * patch_h * patch_w)  # [1, num_tokens, 16]

# Count tokens
token_count_16x16 = x.shape[1]

# 2. Implement adaLN-style scale/shift modulation from a timestep vector
# Assume we have a timestep embedding vector of shape [1, D]
# For simplicity, let D = 16 (matching the feature dim of our patches)
timestep_emb = torch.randn(1, 16)

# In adaLN, we typically generate scale and shift from the timestep embedding
# Let's assume a linear layer maps timestep_emb to scale and shift
# For this lab, we'll directly use parts of the embedding as scale and shift
# In a real DiT, this would be: scale, shift = linear(timestep_emb).chunk(2, dim=-1)

# Let's create a simple "modulation" where scale and shift are derived from timestep_emb
# For demonstration, let's say the first 8 dims are for scale, next 8 for shift
# But our feature dim is 16, so let's just use the whole thing for simplicity
# Actually, let's make it more realistic: assume we have a projection that outputs 2*D
# For this tiny example, let's just use the timestep_emb directly as both scale and shift
# to demonstrate the concept

# Let's define a function that applies adaLN modulation
def adaln_modulate(x, scale, shift):
    """
    Apply adaLN modulation: x * (1 + scale) + shift
    x: [B, N, D]
    scale: [B, D] or [B, 1, D]
    shift: [B, D] or [B, 1, D]
    """
    # Expand scale and shift to match x's shape
    scale = scale.unsqueeze(1)  # [B, 1, D]
    shift = shift.unsqueeze(1)  # [B, 1, D]
    return x * (1 + scale) + shift

# For this example, let's create scale and shift from the timestep embedding
# In a real model, these would come from a learned projection
# Let's just use the first half for scale and second half for shift
# But our feature dim is 16, so let's create scale and shift of dim 16
# We'll use random values for demonstration
scale = torch.randn(1, 16)
shift = torch.randn(1, 16)

# Apply modulation
x_modulated = adaln_modulate(x, scale, shift)

# 3. Show identity behaviour when scale=0 and shift=0
scale_zero = torch.zeros(1, 16)
shift_zero = torch.zeros(1, 16)
x_identity = adaln_modulate(x, scale_zero, shift_zero)

# Check that identity holds
assert torch.allclose(x, x_identity), "Identity modulation should return original tensor"

# 4. Compare token counts for 512 vs 1024 px at patch 2 with VAE x8
# VAE downsamples by 8x, so:
# 512 px image -> 512/8 = 64 x 64 latent
# 1024 px image -> 1024/8 = 128 x 128 latent

# For 512 px:
latent_512_h, latent_512_w = 512 // 8, 512 // 8  # 64 x 64
num_tokens_512 = (latent_512_h // patch_h) * (latent_512_w // patch_w)

# For 1024 px:
latent_1024_h, latent_1024_w = 1024 // 8, 1024 // 8  # 128 x 128
num_tokens_1024 = (latent_1024_h // patch_h) * (latent_1024_w // patch_w)

# Verify calculations
assert num_tokens_512 == 32 * 32, "512px should give 32x32=1024 tokens"
assert num_tokens_1024 == 64 * 64, "1024px should give 64x64=4096 tokens"

# Print results
print(f"RESULT token_count_16x16 = {token_count_16x16}")
print(f"RESULT num_tokens_512 = {num_tokens_512}")
print(f"RESULT num_tokens_1024 = {num_tokens_1024}")
print(f"RESULT identity_check = {torch.allclose(x, x_identity)}")
print(f"RESULT modulated_diff = {f'{(x_modulated - x).abs().mean().item():.6g}'}")
