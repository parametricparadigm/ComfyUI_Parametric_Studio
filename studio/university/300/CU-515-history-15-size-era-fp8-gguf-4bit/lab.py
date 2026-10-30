import torch
import math
import random
import json
import itertools
import collections

# Set seed for determinism
torch.manual_seed(0)

# Simulate a small tensor of weights
original_weights = torch.randn(10, 10)

# Simulate INT8 quantization (simplified: scale to [-127, 127])
max_val = torch.max(torch.abs(original_weights))
scale = 127.0 / max_val
quantized = torch.round(original_weights * scale).clamp(-127, 127)

# Dequantize back to float
dequantized = quantized / scale

# Calculate error
error = torch.mean(torch.abs(original_weights - dequantized))

# Simulate 4-bit quantization (simplified: scale to [-7, 7])
scale_4bit = 7.0 / max_val
quantized_4bit = torch.round(original_weights * scale_4bit).clamp(-7, 7)
dequantized_4bit = quantized_4bit / scale_4bit
error_4bit = torch.mean(torch.abs(original_weights - dequantized_4bit))

# Print results
print(f"RESULT original_mean = {f'{torch.mean(original_weights):.6g}'}")
print(f"RESULT int8_error = {f'{error:.6g}'}")
print(f"RESULT int4_error = {f'{error_4bit:.6g}'}")

# Assert that INT8 error is smaller than INT4 error (concept check)
assert error < error_4bit, "INT8 quantization should have lower error than INT4"

# Assert that both errors are non-negative
assert error >= 0 and error_4bit >= 0, "Quantization errors must be non-negative"
