import torch
import math
import random
import json
import itertools
import collections

# Set the random seed for reproducibility
torch.manual_seed(0)

# Step 1: Create a small CPU tensor (float32)
# This simulates a small data payload, like a chunk of image or audio data
tensor = torch.randn(4, 4, dtype=torch.float32)

# Step 2: Compute a simple checksum-like value using the tensor's sum
# In real formats (like PNG or WAV), checksums (e.g., CRC32 or MD5) ensure data integrity
# Here, we use the sum as a lightweight "checksum" for demonstration
checksum_value = tensor.sum().item()

# Step 3: Simulate a header structure similar to file formats
# For example, PNG chunks have a 4-byte length field followed by data
# We'll create a simple "header" with the tensor's size
header = {
    "format": "SIMPLE_TENSOR",
    "shape": list(tensor.shape),
    "dtype": str(tensor.dtype),
    "size_bytes": tensor.numel() * tensor.element_size()
}

# Step 4: Serialize the header to JSON (like metadata in PNG or MP4)
header_json = json.dumps(header, sort_keys=True)

# Step 5: Verify that the JSON serialization is valid and contains expected keys
# This mimics checking metadata integrity in file formats
parsed_header = json.loads(header_json)
assert "shape" in parsed_header and "dtype" in parsed_header, "Header missing required fields"

# Step 6: Verify that the checksum is a finite number (basic sanity check)
# In real formats, you'd verify CRC32 or MD5 matches the stored value
assert math.isfinite(checksum_value), "Checksum is not finite"

# Step 7: Print results in the required format
print(f"RESULT checksum = {checksum_value:.6g}")
print(f"RESULT header_json = {header_json}")
print(f"RESULT size_bytes = {header['size_bytes']}")
