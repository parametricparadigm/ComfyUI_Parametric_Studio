import torch
import math
import random
import json
import itertools
import collections

# Set seeds for reproducibility
torch.manual_seed(0)
random.seed(42)

# Simulate a minimal ComfyUI workflow JSON structure
# Each key is a node ID, value contains class_type and inputs
workflow = {
    "3": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 20}},
    "5": {"class_type": "VAEDecode", "inputs": {"samples": [3, 0]}},
    "7": {"class_type": "SaveImage", "inputs": {"images": [5, 0]}}
}

# Truth 1: Every node must have a 'class_type' key to be valid
# This ensures the workflow structure is well-formed
assert all('class_type' in node for node in workflow.values()), "Missing class_type"

# Truth 2: The 'SaveImage' node must reference the 'VAEDecode' node's output
# We extract the reference from the SaveImage node's inputs
save_node = workflow["7"]
ref_node_id, ref_slot = save_node["inputs"]["images"]
# Verify the reference points to node 5 (VAEDecode) at slot 0
assert ref_node_id == 5 and ref_slot == 0, "Incorrect link reference"

# Now let's do a tiny CPU tensor operation to satisfy the PyTorch lab requirement
# Create a small tensor representing "latent" data from KSampler
# Shape: (1, 4, 8, 8) - batch, channels, height, width
latent = torch.randn(1, 4, 8, 8, dtype=torch.float32)

# Simulate VAEDecode: apply a simple linear transformation to "decode" latents
# In real ComfyUI, this would be a neural network, but here we use a simple operation
# We'll compute the mean of the latent tensor as a simple "decoded" value
decoded_value = latent.mean().item()

# Simulate SaveImage: in real life this saves pixels, here we just track the value
# The "image" is represented by the decoded value
image_value = decoded_value

# Print results in the required format
print(f"RESULT node_count = {len(workflow)}")
print(f"RESULT link_target = {ref_node_id}")
print(f"RESULT decoded_value = {decoded_value:.6g}")
print(f"RESULT image_value = {image_value:.6g}")

# Additional assertion: verify the tensor operation produced a finite value
assert math.isfinite(decoded_value), "Decoded value must be finite"

# Verify workflow has exactly 3 nodes as expected
assert len(workflow) == 3, "Expected 3 nodes in workflow"
