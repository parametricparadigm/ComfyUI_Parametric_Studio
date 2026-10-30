import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Step 1: Demonstrate precision loss in fp16 accumulation
# fp16 has only 10 mantissa bits, so adding small numbers to large ones can be lost
val_large = torch.tensor(1.0, dtype=torch.float16)
val_small = torch.tensor(0.0001, dtype=torch.float16)

# In fp16, 1.0 + 0.0001 may round back to 1.0 due to limited precision
sum_fp16 = val_large + val_small
print(f"RESULT fp16_sum = {sum_fp16.item():.6g}")

# In fp32, the same addition preserves the small value
val_large_f32 = torch.tensor(1.0, dtype=torch.float32)
val_small_f32 = torch.tensor(0.0001, dtype=torch.float32)
sum_fp32 = val_large_f32 + val_small_f32
print(f"RESULT fp32_sum = {sum_fp32.item():.6g}")

# Assert that fp16 loses precision while fp32 does not
assert sum_fp16.item() == 1.0, "fp16 should lose the small addition"
assert abs(sum_fp32.item() - 1.0001) < 1e-6, "fp32 should preserve the small addition"

# Step 2: Show cumulative error when summing many small values in fp16 vs fp32
# Create a tensor of small positive values
n = 1000
small_values = torch.full((n,), 0.0001, dtype=torch.float32)

# Sum in fp32 (accurate)
sum_fp32_acc = small_values.sum().item()
print(f"RESULT fp32_accumulated = {sum_fp32_acc:.6g}")

# Sum in fp16 (accumulates error)
small_values_fp16 = small_values.to(torch.float16)
sum_fp16_acc = small_values_fp16.sum().item()
print(f"RESULT fp16_accumulated = {sum_fp16_acc:.6g}")

# The fp16 sum should be less accurate
error_fp16 = abs(sum_fp16_acc - n * 0.0001)
error_fp32 = abs(sum_fp32_acc - n * 0.0001)
print(f"RESULT fp16_error = {error_fp16:.6g}")
print(f"RESULT fp32_error = {error_fp32:.6g}")

# Assert that fp16 accumulation has more error than fp32
assert error_fp16 > error_fp32, "fp16 accumulation should have more error than fp32"

# Step 3: Demonstrate gradient accumulation in mixed precision
# Simulate a simple linear layer forward and backward pass
x = torch.randn(4, 8, dtype=torch.float32)
w = torch.randn(8, 4, dtype=torch.float32)

# Forward in fp16
x_fp16 = x.to(torch.float16)
w_fp16 = w.to(torch.float16)
y_fp16 = x_fp16 @ w_fp16

# Backward: compute gradients in fp16, but accumulate in fp32
# Simulate multiple mini-batches
num_batches = 10
grad_acc_fp32 = torch.zeros_like(w, dtype=torch.float32)
grad_acc_fp16 = torch.zeros_like(w, dtype=torch.float16)

for i in range(num_batches):
    # Random input for each batch
    x_batch = torch.randn(4, 8, dtype=torch.float32).to(torch.float16)
    # Create a new weight tensor that requires grad for each batch
    w_batch = w_fp16.clone().requires_grad_(True)
    y_batch = x_batch @ w_batch
    
    # Simple loss: sum of squares
    loss = (y_batch ** 2).sum()
    loss.backward()
    
    # Get gradient of w
    grad_w = w_batch.grad.clone()
    
    # Accumulate in fp32 (correct way)
    grad_acc_fp32 += grad_w.to(torch.float32)
    
    # Accumulate in fp16 (incorrect, shows error)
    grad_acc_fp16 += grad_w

# Compare the accumulated gradients
diff = (grad_acc_fp32 - grad_acc_fp16.to(torch.float32)).abs().max().item()
print(f"RESULT grad_accum_diff = {diff:.6g}")

# Assert that there is a measurable difference between fp16 and fp32 accumulation
assert diff > 0, "There should be a difference between fp16 and fp32 gradient accumulation"
