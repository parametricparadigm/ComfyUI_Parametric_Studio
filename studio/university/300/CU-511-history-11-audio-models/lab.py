import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility as required by the lab rules
torch.manual_seed(0)

# Concept 1: WaveNet/Autoregressive nature relies on sequential dependency.
# Simulate a simple AR(1) process where current sample depends on previous.
# x_t = a * x_{t-1} + b
a = 0.5
b = 0.1
prev_val = 0.0
ar_samples = []

# Generate 10 steps of the autoregressive process
for i in range(10):
    current_val = a * prev_val + b
    ar_samples.append(current_val)
    prev_val = current_val

# Truth 1: In an AR process with positive coefficient < 1, the sequence converges.
# The steady state is b / (1 - a) = 0.1 / 0.5 = 0.2
steady_state = b / (1.0 - a)

# The last value should be closer to the steady state than the first value
first_val = ar_samples[0]
last_val = ar_samples[-1]

# Assert that the sequence is converging towards the steady state
assert abs(last_val - steady_state) < abs(first_val - steady_state), "AR process should converge to steady state"

# Concept 2: Diffusion models operate on noise schedules (sigma).
# Simulate a simple forward diffusion step adding Gaussian noise.
original_signal = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)
noise = torch.randn(3, dtype=torch.float32) * 0.1  # Small noise
sigma = 0.5
noisy_signal = original_signal + sigma * noise

# Truth 2: Adding noise increases the variance of the signal.
# The noisy signal should have a larger deviation from the original than zero.
original_norm = torch.norm(original_signal).item()
noisy_norm = torch.norm(noisy_signal).item()

# Assert that the noisy signal is different from the original (noise was added)
assert noisy_norm != original_norm, "Noisy signal should differ from original"

# Print results in the required format
RESULT_ar_first = f"{first_val:.6g}"
RESULT_ar_last = f"{last_val:.6g}"
RESULT_steady_state = f"{steady_state:.6g}"
RESULT_original_norm = f"{original_norm:.6g}"
RESULT_noisy_norm = f"{noisy_norm:.6g}"

print(f"RESULT ar_first = {RESULT_ar_first}")
print(f"RESULT ar_last = {RESULT_ar_last}")
print(f"RESULT steady_state = {RESULT_steady_state}")
print(f"RESULT original_norm = {RESULT_original_norm}")
print(f"RESULT noisy_norm = {RESULT_noisy_norm}")
