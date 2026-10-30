import torch
import math
import random
import json
import itertools
import collections

# Set the global random seed for PyTorch to ensure reproducibility
torch.manual_seed(0)

# Define a simple graph structure representing a node with a seed input
seed = 42
graph = {
    'nodes': [
        {
            'id': 1,
            'type': 'KSampler',
            'inputs': {
                'seed': seed
            }
        }
    ]
}

# Create a canonical JSON string by sorting keys to ensure consistent ordering
canonical_json = json.dumps(graph, sort_keys=True)

# Compute the SHA256 hash of the canonical JSON string
import hashlib
hash_obj = hashlib.sha256(canonical_json.encode('utf-8'))
digest = hash_obj.hexdigest()

# Print the canonical JSON and the resulting hash digest
print(f'Canonical JSON: {canonical_json}')
print(f'SHA256 Digest: {digest}')

# Assert that the hash is deterministic by recomputing it
assert digest == hashlib.sha256(json.dumps(graph, sort_keys=True).encode('utf-8')).hexdigest()

# Assert that the seed is present in the canonical JSON
assert 'seed' in canonical_json and str(seed) in canonical_json

# Create a small tensor to demonstrate CPU-only float32 operations
tensor = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)

# Perform a simple operation on the tensor
result_tensor = tensor * 2.0

# Print the result of the tensor operation
print(f"RESULT tensor_op = {result_tensor[0]:.6g}")

# Ensure the tensor operation is reproducible
assert torch.allclose(result_tensor, torch.tensor([2.0, 4.0, 6.0], dtype=torch.float32))

# Print a final result to confirm the lab completed successfully
print(f"RESULT lab_complete = 1")
