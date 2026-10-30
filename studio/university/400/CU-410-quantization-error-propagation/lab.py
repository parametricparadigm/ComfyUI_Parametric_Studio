import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define small tensors for CPU-only computation
# Weight matrix (10x10) and input vector (1x10)
w = torch.randn(10, 10)
x = torch.randn(1, 10)

# Quantize weights to 8-bit integer range [-1, 1]
# Scale by 127, round to nearest integer, then scale back
w_q = torch.round(w * 127.0) / 127.0

# Compute outputs with full precision and quantized weights
out_fp = torch.nn.functional.linear(x, w)
out_q = torch.nn.functional.linear(x, w_q)

# Calculate mean absolute error between full precision and quantized outputs
err = (out_fp - out_q).abs().mean().item()

# Print result in required format
print(f"RESULT mean_abs_error = {err:.6g}")

# Assert that quantization introduces some error
assert err > 0.0, "Quantization should introduce error"

# Assert that error is small for 8-bit quantization
assert err < 0.5, "Error should be small for 8-bit quantization"

# Print a second result: maximum absolute error
max_err = (out_fp - out_q).abs().max().item()
print(f"RESULT max_abs_error = {max_err:.6g}")

# Assert that max error is also bounded
assert max_err < 1.0, "Maximum error should be bounded for 8-bit quantization"
