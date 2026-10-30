import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define constants
GB = 1024 ** 3  # 1 GB in bytes
MB = 1024 ** 2  # 1 MB in bytes

# Define precisions and their bytes per parameter
PRECISIONS = {
    "fp32": 4,
    "bf16": 2,
    "fp8": 1,
    "4bit": 0.5
}

# Define model sizes in billions of parameters
MODELS = {
    "12B": 12e9,
    "4B": 4e9
}

# Define GPU memory configurations
GPUS = {
    "24GB": 24 * GB,
    "96GB": 96 * GB
}

# Reserve memory for safety (4 GB)
RESERVE = 4 * GB

# Safety factor for activations and caches (e.g., 1.2x)
SAFETY_FACTOR = 1.2

# Estimate activation memory as a fraction of weights (simplified model)
# In practice, this depends on batch size, sequence length, etc.
# For this lab, we assume activations are ~10% of weights for a small batch
ACTIVATION_FRACTION = 0.1

# Estimate latent/cache memory as a fraction of weights
# For example, KV cache in transformers can be significant
LATENT_FRACTION = 0.05

def calculate_memory(params, bytes_per_param, activation_fraction=ACTIVATION_FRACTION, latent_fraction=LATENT_FRACTION, safety_factor=SAFETY_FACTOR):
    """
    Calculate total memory required for a model.
    
    Args:
        params: Number of parameters
        bytes_per_param: Bytes per parameter (e.g., 4 for fp32)
        activation_fraction: Fraction of weights for activations
        latent_fraction: Fraction of weights for latent/cache
        safety_factor: Safety multiplier
    
    Returns:
        Total memory in bytes
    """
    # Weights memory
    weights_bytes = params * bytes_per_param
    
    # Activation memory estimate
    activation_bytes = weights_bytes * activation_fraction
    
    # Latent/cache memory estimate
    latent_bytes = weights_bytes * latent_fraction
    
    # Total before safety factor
    total_bytes = weights_bytes + activation_bytes + latent_bytes
    
    # Apply safety factor
    total_bytes *= safety_factor
    
    return total_bytes

# Calculate and print results
results = {}

for model_name, params in MODELS.items():
    for prec_name, bytes_per_param in PRECISIONS.items():
        # Calculate total memory
        total_bytes = calculate_memory(params, bytes_per_param)
        
        # Store result
        key = f"{model_name}_{prec_name}"
        results[key] = total_bytes
        
        # Print result
        print(f"RESULT {key} = {total_bytes:.6g}")

# Check which models fit in which GPUs
print("\n--- Fit Analysis ---")
for gpu_name, gpu_mem in GPUS.items():
    available_mem = gpu_mem - RESERVE
    print(f"\n{gpu_name} GPU (available: {available_mem / GB:.2f} GB after reserve):")
    for model_name, params in MODELS.items():
        for prec_name, bytes_per_param in PRECISIONS.items():
            key = f"{model_name}_{prec_name}"
            total_bytes = results[key]
            fits = total_bytes <= available_mem
            status = "FITS" if fits else "DOES NOT FIT"
            print(f"  {model_name} @ {prec_name}: {total_bytes / GB:.2f} GB -> {status}")

# Assertions to verify concepts
# 1. Higher precision should require more memory
assert results["12B_fp32"] > results["12B_bf16"], "fp32 should require more memory than bf16"
assert results["12B_bf16"] > results["12B_fp8"], "bf16 should require more memory than fp8"
assert results["12B_fp8"] > results["12B_4bit"], "fp8 should require more memory than 4bit"

# 2. Larger model should require more memory at same precision
assert results["12B_fp32"] > results["4B_fp32"], "12B model should require more memory than 4B model"
assert results["12B_bf16"] > results["4B_bf16"], "12B model should require more memory than 4B model at bf16"

# 3. 4-bit should fit in 24GB for 4B model
assert results["4B_4bit"] <= (24 * GB - RESERVE), "4B model at 4-bit should fit in 24GB GPU"

# 4. 12B model at fp32 should NOT fit in 24GB
assert results["12B_fp32"] > (24 * GB - RESERVE), "12B model at fp32 should not fit in 24GB GPU"

print("\nAll assertions passed!")
