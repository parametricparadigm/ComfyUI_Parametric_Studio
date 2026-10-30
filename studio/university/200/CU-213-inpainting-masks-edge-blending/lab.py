import torch

# Set seed for reproducibility
torch.manual_seed(0)

# Define a binary mask: 1.0 means "use image A", 0.0 means "use image B"
mask = torch.tensor([0.0, 0.0, 1.0, 1.0], dtype=torch.float32)

# Define two source images (1D tensors for simplicity)
img_a = torch.tensor([10.0, 20.0, 30.0, 40.0], dtype=torch.float32)
img_b = torch.tensor([100.0, 200.0, 300.0, 400.0], dtype=torch.float32)

# Define a feathered (soft) mask with gradual transition
feather = torch.tensor([0.0, 0.5, 0.5, 1.0], dtype=torch.float32)

# Hard blend: abrupt switch based on binary mask
blended = mask * img_a + (1 - mask) * img_b

# Feathered blend: smooth transition using soft alpha values
feathered = feather * img_a + (1 - feather) * img_b

# Print results in required format
print(f"RESULT hard_blend = {blended.tolist()}")
print(f"RESULT feathered_blend = {feathered.tolist()}")

# Assert that at the boundary (index 1), feathered blend gives 50/50 mix
# feather[1] = 0.5, so feathered[1] = 0.5*20 + 0.5*200 = 10 + 100 = 110.0
assert torch.allclose(feathered[1], torch.tensor(110.0)), "Feathered edge should be 50/50 mix at 0.5 alpha"

# Assert hard blend at index 0 uses only img_b (mask=0.0)
# blended[0] = 0.0*10 + 1.0*100 = 100.0
assert torch.allclose(blended[0], torch.tensor(100.0)), "Hard blend with mask=0 should use img_b"
