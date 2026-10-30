import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# 1. Create a synthetic test image (8x8) with a smooth gradient pattern
# A smooth gradient ensures that a 1-pixel shift preserves most structural information
width, height = 8, 8
x = torch.linspace(0, 1, width)
y = torch.linspace(0, 1, height)
xx, yy = torch.meshgrid(x, y, indexing='ij')
# Create a smooth diagonal gradient pattern
original = (xx + yy) * 255.0
original = original.unsqueeze(0).unsqueeze(0)  # Shape: (1, 1, 8, 8)

# 2. Define PSNR function
def psnr(original, distorted, max_val=255.0):
    """
    Calculate Peak Signal-to-Noise Ratio.
    PSNR = 10 * log10(max_val^2 / MSE)
    """
    mse = torch.mean((original - distorted) ** 2)
    if mse == 0:
        return float('inf')
    return 10 * math.log10(max_val ** 2 / mse)

# 3. Define Structural Correlation (Pearson correlation on flattened images)
def structural_correlation(original, distorted):
    """
    Calculate Pearson correlation coefficient between two images.
    This measures linear relationship, invariant to global shifts/scales.
    """
    orig_flat = original.flatten()
    dist_flat = distorted.flatten()
    
    # Center the data
    orig_mean = torch.mean(orig_flat)
    dist_mean = torch.mean(dist_flat)
    orig_centered = orig_flat - orig_mean
    dist_centered = dist_flat - dist_mean
    
    # Calculate correlation
    numerator = torch.sum(orig_centered * dist_centered)
    denominator = torch.sqrt(torch.sum(orig_centered ** 2) * torch.sum(dist_centered ** 2))
    
    if denominator == 0:
        return 0.0
    return (numerator / denominator).item()

# 4. Generate distorted versions

# a) Blurred image (simple 3x3 box blur)
# Create a 3x3 kernel
kernel = torch.ones((1, 1, 3, 3)) / 9.0
# Pad the image to handle borders
padded = torch.nn.functional.pad(original, (1, 1, 1, 1), mode='replicate')
# Apply convolution (manual implementation for CPU-only simplicity)
blurred = torch.zeros_like(original)
for i in range(height):
    for j in range(width):
        blurred[0, 0, i, j] = torch.sum(padded[0, 0, i:i+3, j:j+3] * kernel[0, 0, :, :])

# b) Brightness shifted image (add 50 to all pixels)
brightness_shifted = original + 50.0

# c) Shifted image (shift by 1 pixel to the right, wrap around)
# For a smooth gradient, this preserves most of the structure
shifted = torch.roll(original, shifts=1, dims=3)

# 5. Calculate metrics for each distortion

# Original vs Original (baseline)
psnr_original = psnr(original, original)
corr_original = structural_correlation(original, original)

# Original vs Blurred
psnr_blur = psnr(original, blurred)
corr_blur = structural_correlation(original, blurred)

# Original vs Brightness Shifted
psnr_brightness = psnr(original, brightness_shifted)
corr_brightness = structural_correlation(original, brightness_shifted)

# Original vs Shifted
psnr_shift = psnr(original, shifted)
corr_shift = structural_correlation(original, shifted)

# 6. Print results
print(f"RESULT psnr_original = {psnr_original:.6g}")
print(f"RESULT corr_original = {corr_original:.6g}")
print(f"RESULT psnr_blur = {psnr_blur:.6g}")
print(f"RESULT corr_blur = {corr_blur:.6g}")
print(f"RESULT psnr_brightness = {psnr_brightness:.6g}")
print(f"RESULT corr_brightness = {corr_brightness:.6g}")
print(f"RESULT psnr_shift = {psnr_shift:.6g}")
print(f"RESULT corr_shift = {corr_shift:.6g}")

# 7. Assertions to verify the concepts

# Assertion 1: Blur should lower both PSNR and correlation compared to original
assert psnr_blur < psnr_original, "Blur should lower PSNR"
assert corr_blur < corr_original, "Blur should lower structural correlation"

# Assertion 2: Brightness shift should hurt PSNR but not correlation (correlation should remain high)
assert psnr_brightness < psnr_original, "Brightness shift should lower PSNR"
assert corr_brightness > 0.99, "Brightness shift should preserve structural correlation (high value)"

# Assertion 3: Shift should have bad PSNR but high correlation (perceptually similar structure)
# For a smooth gradient, a 1-pixel shift preserves most of the linear structure
assert psnr_shift < psnr_original, "Pixel shift should lower PSNR"
assert corr_shift > 0.50, "Pixel shift should preserve structural correlation (moderately high value)"

# Additional check: PSNR for identical images should be very high (infinity or large number)
assert psnr_original > 100, "PSNR for identical images should be very high"

# Check that correlation for identical images is 1.0
assert abs(corr_original - 1.0) < 1e-6, "Correlation for identical images should be 1.0"
