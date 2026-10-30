import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required
torch.manual_seed(0)

# Define the list of (claim, reported_metric, baseline_metric) tuples
# These represent claims from a hypothetical generative AI paper
claims = [
    ("Model A improves accuracy", 0.85, 0.83),
    ("Model B reduces latency", 120.5, 125.0),
    ("Model C increases F1 score", 0.72, 0.715),
    ("Model D boosts throughput", 1000, 990),
    ("Model E enhances diversity", 0.45, 0.44),
]

# Assumed noise level for determining if improvement is within noise
NOISE_THRESHOLD = 0.015  # 1.5%

# Function to compute relative improvement
def compute_relative_improvement(reported, baseline):
    """
    Compute relative improvement as (reported - baseline) / baseline.
    For metrics where lower is better (like latency), we invert the logic.
    Here we assume all metrics are 'higher is better' for simplicity,
    but in practice, you'd need to know the metric direction.
    """
    if baseline == 0:
        return float('inf') if reported > 0 else 0.0
    return (reported - baseline) / baseline

# Process each claim
results = []
for claim, reported, baseline in claims:
    # Convert to float32 CPU tensors as required
    reported_tensor = torch.tensor(reported, dtype=torch.float32)
    baseline_tensor = torch.tensor(baseline, dtype=torch.float32)
    
    # Compute relative improvement
    rel_improvement = compute_relative_improvement(reported_tensor.item(), baseline_tensor.item())
    
    # Check if improvement is within noise (less than 2% improvement)
    # The problem states: flag improvements under 2% as within-noise given assumed noise of 1.5%
    # So if relative improvement < 0.02, it's considered within noise
    is_within_noise = abs(rel_improvement) < 0.02
    
    # A claim "survives" if it's NOT within noise
    survives = not is_within_noise
    
    results.append({
        "claim": claim,
        "relative_improvement": rel_improvement,
        "survives": survives
    })

# Print results in the required format
for result in results:
    name = result["claim"]
    value = result["relative_improvement"]
    # Format floats with f"{x:.6g}" to keep small values' digits
    print(f"RESULT {name} = {value:.6g}")

# Assert statements to check the concept holds
# 1. Check that a claim with >2% improvement survives
assert any(r["survives"] for r in results if r["relative_improvement"] > 0.02), "Claims with >2% improvement should survive"

# 2. Check that a claim with <2% improvement does NOT survive
assert not any(r["survives"] for r in results if abs(r["relative_improvement"]) < 0.02), "Claims with <2% improvement should be flagged as within-noise"
