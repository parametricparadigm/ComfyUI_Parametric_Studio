import torch
import torch.nn.functional as F
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Simulate two batches of 4 items each (e.g., 4 images and 4 texts)
# In a real CLIP model, these would be high-dimensional embeddings.
# Here we use 3-dimensional vectors for simplicity.

# Image embeddings (batch_size=4, dim=3)
img_embeds = torch.tensor([
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 1.0, 0.0]
], dtype=torch.float32)

# Text embeddings (batch_size=4, dim=3)
# The 'correct' pairs are diagonal: img0-text0, img1-text1, etc.
txt_embeds = torch.tensor([
    [1.0, 0.1, 0.0],
    [0.1, 1.0, 0.0],
    [0.0, 0.1, 1.0],
    [1.0, 0.9, 0.0]
], dtype=torch.float32)

# Normalize embeddings to unit length (standard in CLIP)
img_norm = F.normalize(img_embeds, p=2, dim=1)
txt_norm = F.normalize(txt_embeds, p=2, dim=1)

# Compute similarity matrix (batch_size x batch_size)
# Each element [i, j] is the cosine similarity between image i and text j
sim_matrix = torch.matmul(img_norm, txt_norm.t())

# The diagonal elements should be the highest similarities for correct pairs
# Let's verify this concept holds
diag_sims = torch.diag(sim_matrix)
off_diag_sims = sim_matrix[~torch.eye(4, dtype=torch.bool)]

# Assert that the diagonal similarities are higher than the off-diagonal ones
# This is the core idea of contrastive learning: correct pairs should be more similar
assert torch.all(diag_sims > off_diag_sims.min()), "Diagonal similarities should be higher than minimum off-diagonal"

# Compute the contrastive loss (InfoNCE) for the image-to-text direction
# Temperature scaling (typical in CLIP)
temperature = 0.07
logits = sim_matrix / temperature

# Labels are the diagonal indices: [0, 1, 2, 3]
labels = torch.arange(4)

# Cross-entropy loss for image-to-text
loss_it = F.cross_entropy(logits, labels)

# Cross-entropy loss for text-to-image
loss_ti = F.cross_entropy(logits.t(), labels)

# Total CLIP loss is the average of both directions
clip_loss = (loss_it + loss_ti) / 2

# Print results
print(f"RESULT sim_matrix = {sim_matrix.tolist()}")
print(f"RESULT diag_sims = {diag_sims.tolist()}")
print(f"RESULT loss_it = {loss_it.item()}")
print(f"RESULT loss_ti = {loss_ti.item()}")
print(f"RESULT clip_loss = {clip_loss.item()}")

# Verify that the highest similarity for each image is its correct text pair
for i in range(4):
    max_idx = torch.argmax(sim_matrix[i]).item()
    assert max_idx == i, f"Image {i} should match text {i}, but matched text {max_idx}"

# Verify that the highest similarity for each text is its correct image pair
for j in range(4):
    max_idx = torch.argmax(sim_matrix[:, j]).item()
    assert max_idx == j, f"Text {j} should match image {j}, but matched image {max_idx}"

print("RESULT all_assertions_passed = True")
