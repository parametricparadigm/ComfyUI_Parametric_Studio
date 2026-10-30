import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# --- Part 1: Simulate img2img denoising strength ---
# In img2img, we start with a clean latent, add noise proportional to strength s,
# then "denoise" (simulate by recovering the original signal partially).
# We measure how much of the original signal survives via correlation.

def simulate_img2img(clean_latent, strength):
    """
    Simulate img2img:
    1. Add noise to clean latent with magnitude scaled by strength.
    2. Simulate denoising: recover a fraction (1 - strength) of original signal.
    3. Return the resulting latent and correlation with original.
    """
    # Add Gaussian noise scaled by strength
    noise = torch.randn_like(clean_latent) * strength
    noisy_latent = clean_latent + noise
    
    # Simulate denoising: the model recovers (1 - strength) of the original signal
    # and the rest is influenced by the noise. We model this as a linear blend.
    # After denoising, the output is approximately:
    #   output = (1 - strength) * clean + strength * (clean + noise)
    #          = clean + strength * noise
    # But to simulate imperfect recovery, we assume the denoiser removes
    # a fraction of the noise. Let's say it removes (1 - strength) of the noise,
    # so remaining noise = strength * noise * strength = strength^2 * noise.
    # Actually, a simpler model: the output correlates with the original
    # based on how much signal vs noise remains.
    
    # Let's use a more direct approach:
    # The "denoised" output is a blend: (1-s)*clean + s*(clean + noise)
    # = clean + s*noise
    # The correlation between output and clean depends on the SNR.
    
    # Compute correlation between noisy_latent and clean_latent
    # Flatten for correlation
    clean_flat = clean_latent.flatten()
    noisy_flat = noisy_latent.flatten()
    
    # Pearson correlation
    clean_mean = clean_flat.mean()
    noisy_mean = noisy_flat.mean()
    clean_centered = clean_flat - clean_mean
    noisy_centered = noisy_flat - noisy_mean
    
    numerator = torch.sum(clean_centered * noisy_centered)
    denominator = torch.sqrt(torch.sum(clean_centered ** 2) * torch.sum(noisy_centered ** 2))
    
    if denominator == 0:
        correlation = 1.0
    else:
        correlation = (numerator / denominator).item()
    
    return noisy_latent, correlation

# Create a small clean latent (e.g., 4x4x4)
clean_latent = torch.randn(4, 4, 4)

# Test different strengths
strengths = [0.2, 0.5, 0.8, 1.0]
correlations = {}

for s in strengths:
    _, corr = simulate_img2img(clean_latent, s)
    correlations[s] = corr
    print(f"RESULT img2img_corr_s{s} = {corr:.6g}")

# Assert: correlation should decrease as strength increases
assert correlations[0.2] > correlations[0.5], "Correlation should decrease with increasing strength"
assert correlations[0.5] > correlations[0.8], "Correlation should decrease with increasing strength"

# --- Part 2: Simulate inpaint mask blending ---
# In inpainting, we have a mask that defines which regions to preserve.
# Pixels outside the mask should remain unchanged.

def simulate_inpaint(image, mask):
    """
    Simulate inpainting:
    - mask is a binary tensor (1 = preserve, 0 = inpaint)
    - The inpainted region is filled with some new values
    - Pixels outside the mask (where mask=1) should be unchanged
    """
    # Create a "denoised" version that would be different everywhere
    # Simulate the inpainting model output
    inpainted_region = torch.randn_like(image)
    
    # Blend: where mask=1, keep original; where mask=0, use inpainted
    # mask: 1 = preserve original, 0 = use inpainted
    result = mask * image + (1 - mask) * inpainted_region
    
    return result

# Create a small image and mask
image = torch.randn(4, 4)
# Mask: top-left 2x2 is preserved (1), rest is inpainted (0)
mask = torch.zeros(4, 4)
mask[:2, :2] = 1.0

result = simulate_inpaint(image, mask)

# Verify pixels outside the mask (where mask=1) are unchanged
preserved_region_original = image[:2, :2]
preserved_region_result = result[:2, :2]

# Check that preserved region is unchanged
max_diff_preserved = torch.max(torch.abs(preserved_region_original - preserved_region_result)).item()
print(f"RESULT inpaint_max_diff_preserved = {max_diff_preserved:.6g}")

# Assert: preserved region should be unchanged
assert max_diff_preserved < 1e-6, "Pixels outside the mask should be unchanged"

# Also verify that the inpainted region is different (sanity check)
inpainted_region_original = image[2:, 2:]
inpainted_region_result = result[2:, 2:]
diff_inpainted = torch.mean(torch.abs(inpainted_region_original - inpainted_region_result)).item()
print(f"RESULT inpaint_mean_diff_inpainted = {diff_inpainted:.6g}")

# Assert: inpainted region should be different
assert diff_inpainted > 0.01, "Inpainted region should be different from original"
