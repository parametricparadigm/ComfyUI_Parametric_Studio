import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Create a random weight matrix with varying row scales to demonstrate per-row advantage
# Row 0 has small values, Row 1 has large values, Row 2 has medium values
W = torch.tensor([
    [0.01, 0.02, 0.015, 0.008, 0.012, 0.009, 0.011, 0.014],
    [5.0, 4.8, 5.2, 4.9, 5.1, 4.7, 5.3, 4.6],
    [1.0, 1.2, 0.9, 1.1, 1.05, 0.95, 1.15, 0.85]
], dtype=torch.float32)

# Create a random input vector for matrix multiplication
x = torch.randn(8, dtype=torch.float32)

# Reference float32 computation
ref_output = W @ x

# Helper function to compute metrics
def compute_metrics(W_orig, W_quant, x):
    """Compute MSE, max error, and output error vs float32"""
    # Weight reconstruction error
    weight_mse = torch.mean((W_orig - W_quant) ** 2).item()
    weight_max_err = torch.max(torch.abs(W_orig - W_quant)).item()
    
    # Output error
    quant_output = W_quant @ x
    output_mse = torch.mean((ref_output - quant_output) ** 2).item()
    output_max_err = torch.max(torch.abs(ref_output - quant_output)).item()
    
    return weight_mse, weight_max_err, output_mse, output_max_err

# Symmetric int8 per-tensor quantization
# Scale = max_abs / 127
max_abs_tensor = torch.max(torch.abs(W)).item()
scale_tensor = max_abs_tensor / 127.0
zero_point_tensor = 0  # Symmetric quantization

# Quantize to int8
W_int8_tensor = torch.round(W / scale_tensor).clamp(-128, 127).to(torch.int8)
# Dequantize back to float32
W_dequant_tensor = W_int8_tensor.to(torch.float32) * scale_tensor

# Compute metrics for per-tensor
wt_mse, wt_max, out_mse, out_max = compute_metrics(W, W_dequant_tensor, x)

# Symmetric int8 per-row quantization
# Each row has its own scale
W_int8_row = torch.zeros_like(W, dtype=torch.int8)
scales_row = torch.zeros(W.shape[0], dtype=torch.float32)

for i in range(W.shape[0]):
    row_max = torch.max(torch.abs(W[i])).item()
    scale_row = row_max / 127.0 if row_max > 0 else 1.0
    scales_row[i] = scale_row
    W_int8_row[i] = torch.round(W[i] / scale_row).clamp(-128, 127).to(torch.int8)

# Dequantize per-row
W_dequant_row = torch.zeros_like(W, dtype=torch.float32)
for i in range(W.shape[0]):
    W_dequant_row[i] = W_int8_row[i].to(torch.float32) * scales_row[i]

# Compute metrics for per-row
wr_mse, wr_max, outr_mse, outr_max = compute_metrics(W, W_dequant_row, x)

# 4-bit quantization with group size 32
# Since our matrix is 3x8, group size 32 means each row is one group (8 elements < 32)
# We'll use symmetric 4-bit: range [-8, 7]
W_int4 = torch.zeros_like(W, dtype=torch.int8)
scales_4bit = torch.zeros(W.shape[0], dtype=torch.float32)

for i in range(W.shape[0]):
    row = W[i]
    row_max = torch.max(torch.abs(row)).item()
    scale_4 = row_max / 7.0 if row_max > 0 else 1.0  # 4-bit symmetric: max positive is 7
    scales_4bit[i] = scale_4
    W_int4[i] = torch.round(row / scale_4).clamp(-8, 7).to(torch.int8)

# Dequantize 4-bit
W_dequant_4bit = torch.zeros_like(W, dtype=torch.float32)
for i in range(W.shape[0]):
    W_dequant_4bit[i] = W_int4[i].to(torch.float32) * scales_4bit[i]

# Compute metrics for 4-bit
w4_mse, w4_max, out4_mse, out4_max = compute_metrics(W, W_dequant_4bit, x)

# Calculate bytes saved
# Original: float32 = 4 bytes per element
num_elements = W.numel()
bytes_float32 = num_elements * 4

# int8: 1 byte per element + 1 float32 scale per tensor (per-tensor) or per row (per-row)
bytes_int8_tensor = num_elements * 1 + 4  # 1 scale for entire tensor
bytes_int8_row = num_elements * 1 + W.shape[0] * 4  # 1 scale per row

# 4-bit: 0.5 bytes per element + 1 float32 scale per group (here per row since group_size=32 > row_len)
bytes_4bit = num_elements * 0.5 + W.shape[0] * 4

# Savings percentages
savings_int8_tensor = (1 - bytes_int8_tensor / bytes_float32) * 100
savings_int8_row = (1 - bytes_int8_row / bytes_float32) * 100
savings_4bit = (1 - bytes_4bit / bytes_float32) * 100

# Print results
print(f"RESULT per_tensor_int8_weight_mse = {wt_mse:.6g}")
print(f"RESULT per_tensor_int8_weight_max_err = {wt_max:.6g}")
print(f"RESULT per_tensor_int8_output_mse = {out_mse:.6g}")
print(f"RESULT per_tensor_int8_output_max_err = {out_max:.6g}")
print(f"RESULT per_tensor_int8_bytes_saved_pct = {savings_int8_tensor:.6g}")

print(f"RESULT per_row_int8_weight_mse = {wr_mse:.6g}")
print(f"RESULT per_row_int8_weight_max_err = {wr_max:.6g}")
print(f"RESULT per_row_int8_output_mse = {outr_mse:.6g}")
print(f"RESULT per_row_int8_output_max_err = {outr_max:.6g}")
print(f"RESULT per_row_int8_bytes_saved_pct = {savings_int8_row:.6g}")

print(f"RESULT int4_group32_weight_mse = {w4_mse:.6g}")
print(f"RESULT int4_group32_weight_max_err = {w4_max:.6g}")
print(f"RESULT int4_group32_output_mse = {out4_mse:.6g}")
print(f"RESULT int4_group32_output_max_err = {out4_max:.6g}")
print(f"RESULT int4_group32_bytes_saved_pct = {savings_4bit:.6g}")

# Assert that per-row beats per-tensor when rows have different scales
# Per-row should have lower MSE than per-tensor
assert wr_mse < wt_mse, "Per-row int8 should have lower weight MSE than per-tensor int8"
assert outr_mse < out_mse, "Per-row int8 should have lower output MSE than per-tensor int8"

# Assert that 4-bit has higher error than int8 (less precision)
assert w4_mse > wr_mse, "4-bit quantization should have higher MSE than int8 per-row"
assert out4_mse > outr_mse, "4-bit quantization should have higher output MSE than int8 per-row"

# Assert bytes saved are reasonable
assert savings_int8_tensor > 70, "int8 should save more than 70% bytes"
assert savings_4bit > 50, "4-bit should save more than 50% bytes"
