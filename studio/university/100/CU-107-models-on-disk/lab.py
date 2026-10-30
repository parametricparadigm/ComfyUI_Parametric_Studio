import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Step 1: Create tiny tensors to simulate a model's parameters
# We'll create a few small tensors with different shapes and dtypes
tensor_a = torch.randn(2, 3)  # float32 by default
tensor_b = torch.randn(4)     # float32
tensor_c = torch.randn(1, 1, 5)  # float32

# Step 2: Build a safetensors-like byte string in memory
# Safetensors format: [8-byte header length][JSON header][tensor data]
# The JSON header maps tensor names to metadata: {"dtype": "...", "shape": [...], "data_offsets": [start, end]}

# Helper to get dtype string for torch dtypes
def get_dtype_str(dtype):
    if dtype == torch.float32:
        return "F32"
    elif dtype == torch.float16:
        return "F16"
    elif dtype == torch.int32:
        return "I32"
    elif dtype == torch.int64:
        return "I64"
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")

# Build the header dictionary
header = {}
offset = 0
tensors = {
    "layer1.weight": tensor_a,
    "layer1.bias": tensor_b,
    "layer2.weight": tensor_c
}

for name, tensor in tensors.items():
    # Calculate byte size of this tensor
    byte_size = tensor.numel() * tensor.element_size()
    # Record metadata
    header[name] = {
        "dtype": get_dtype_str(tensor.dtype),
        "shape": list(tensor.shape),
        "data_offsets": [offset, offset + byte_size]
    }
    offset += byte_size

# Convert header to JSON bytes
header_json = json.dumps(header).encode('utf-8')
header_length = len(header_json)

# Build the full byte string: [8-byte little-endian header length][header JSON][tensor data]
# First, pack the header length as 8-byte little-endian unsigned integer
header_len_bytes = header_length.to_bytes(8, byteorder='little')

# Concatenate all tensor data
tensor_data = b''
for name, tensor in tensors.items():
    # Convert tensor to bytes (contiguous float32)
    tensor_data += tensor.numpy().tobytes()

# Full byte string
full_bytes = header_len_bytes + header_json + tensor_data

# Step 3: Parse the byte string to recover tensor info
# Read the first 8 bytes as header length
parsed_header_length = int.from_bytes(full_bytes[0:8], byteorder='little')
assert parsed_header_length == header_length, "Header length mismatch"

# Extract and parse the JSON header
header_bytes = full_bytes[8:8 + parsed_header_length]
parsed_header = json.loads(header_bytes.decode('utf-8'))

# Step 4: Compute total parameter count and byte size
total_params = 0
total_bytes = 0

for name, meta in parsed_header.items():
    shape = meta["shape"]
    # Compute number of elements from shape
    num_elements = 1
    for dim in shape:
        num_elements *= dim
    total_params += num_elements
    # Byte size from data_offsets
    start, end = meta["data_offsets"]
    total_bytes += (end - start)

# Step 5: Verify that the recovered data matches the original tensors
# Extract tensor data from the byte string and compare
for name, meta in parsed_header.items():
    start, end = meta["data_offsets"]
    # Data starts after header_len_bytes (8 bytes) + header_json
    data_start = 8 + parsed_header_length
    tensor_bytes = full_bytes[data_start + start:data_start + end]
    
    # Reconstruct tensor from bytes
    dtype_str = meta["dtype"]
    if dtype_str == "F32":
        dtype = torch.float32
    else:
        raise ValueError(f"Unsupported dtype string: {dtype_str}")
    
    shape = meta["shape"]
    reconstructed = torch.frombuffer(tensor_bytes, dtype=dtype).reshape(shape)
    
    # Compare with original
    original = tensors[name]
    assert torch.allclose(reconstructed, original), f"Tensor mismatch for {name}"

# Step 6: Print results
print(f"RESULT total_params = {total_params}")
print(f"RESULT total_bytes = {total_bytes}")
print(f"RESULT num_tensors = {len(parsed_header)}")

# Additional assertions to check the concept holds
# 1. Total bytes should equal sum of individual tensor byte sizes
expected_total_bytes = sum(t.numel() * t.element_size() for t in tensors.values())
assert total_bytes == expected_total_bytes, "Total byte size mismatch"

# 2. Total params should equal sum of individual tensor element counts
expected_total_params = sum(t.numel() for t in tensors.values())
assert total_params == expected_total_params, "Total parameter count mismatch"
