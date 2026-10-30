import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)
random.seed(0)

# Step 1: Build a toy word-level tokenizer
# We define a small vocabulary to keep the example simple and deterministic.
vocab = ["the", "cat", "sat", "on", "mat", "dog", "ran", "in", "park", "sun"]
word_to_idx = {w: i for i, w in enumerate(vocab)}
idx_to_word = {i: w for w, i in word_to_idx.items()}

# Step 2: Create an embedding table using torch.nn.Embedding
# Embedding dimension is 8 for a small, easy-to-inspect space.
embed_dim = 8
embedding = torch.nn.Embedding(len(vocab), embed_dim)
# Initialize with fixed values for determinism (though manual_seed handles this,
# explicit init makes the concept clearer for students).
with torch.no_grad():
    embedding.weight.copy_(torch.randn(len(vocab), embed_dim))

# Step 3: Define two pairs of prompts
# Pair A: Share many words -> should have higher cosine similarity
prompt_a1 = "the cat sat on mat"
prompt_a2 = "the cat sat on mat"  # Identical, so similarity should be 1.0

# Pair B: Share few/no words -> should have lower cosine similarity
prompt_b1 = "the dog ran in park"
prompt_b2 = "the sun sat on mat"  # Shares "the", "sat", "on", "mat" but different context

# Actually, let's make Pair B share fewer words to contrast with Pair A.
# Let's redefine:
# Pair A: "the cat sat on mat" vs "the cat sat on mat" (identical)
# Pair B: "the dog ran in park" vs "the sun sat on mat" (shares "the", "sat", "on", "mat")
# To make the contrast clearer, let's use:
# Prompt 1: "the cat sat on mat"
# Prompt 2: "the cat sat on mat" (identical -> cos sim = 1.0)
# Prompt 3: "the dog ran in park"
# Prompt 4: "the sun sat on mat" (shares "the", "sat", "on", "mat" with Prompt 1)

# Let's use:
# Pair 1 (high similarity): "the cat sat on mat" and "the cat sat on mat"
# Pair 2 (lower similarity): "the dog ran in park" and "the sun sat on mat"

def tokenize(text):
    """Tokenize text into word indices."""
    words = text.split()
    return [word_to_idx[w] for w in words if w in word_to_idx]

def embed_prompt(tokens):
    """Embed a list of token indices into a tensor of shape [num_tokens, embed_dim]."""
    token_tensor = torch.tensor(tokens, dtype=torch.long)
    return embedding(token_tensor)

def pool_embeddings(embeddings):
    """Mean-pool the embeddings to get a single vector for the prompt."""
    return embeddings.mean(dim=0)

def cosine_similarity(v1, v2):
    """Compute cosine similarity between two vectors."""
    return torch.nn.functional.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()

# Step 4: Process the prompts
# Prompt 1 and 2: Identical
tokens_1 = tokenize("the cat sat on mat")
tokens_2 = tokenize("the cat sat on mat")

# Prompt 3 and 4: Different
tokens_3 = tokenize("the dog ran in park")
tokens_4 = tokenize("the sun sat on mat")

# Embed each prompt
emb_1 = embed_prompt(tokens_1)  # Shape: [5, 8]
emb_2 = embed_prompt(tokens_2)  # Shape: [5, 8]
emb_3 = embed_prompt(tokens_3)  # Shape: [5, 8]
emb_4 = embed_prompt(tokens_4)  # Shape: [5, 8]

# Step 5: Pad to equal length and create masks
# All prompts here have 5 tokens, so no padding needed, but we demonstrate the concept.
max_len = max(len(tokens_1), len(tokens_2), len(tokens_3), len(tokens_4))

def pad_and_mask(tokens, max_len):
    """Pad tokens to max_len and create a mask."""
    padded = tokens + [0] * (max_len - len(tokens))  # 0 is padding index
    mask = [1] * len(tokens) + [0] * (max_len - len(tokens))
    return torch.tensor(padded, dtype=torch.long), torch.tensor(mask, dtype=torch.float)

# Pad all prompts
padded_1, mask_1 = pad_and_mask(tokens_1, max_len)
padded_2, mask_2 = pad_and_mask(tokens_2, max_len)
padded_3, mask_3 = pad_and_mask(tokens_3, max_len)
padded_4, mask_4 = pad_and_mask(tokens_4, max_len)

# Embed padded prompts
emb_padded_1 = embedding(padded_1)  # Shape: [max_len, 8]
emb_padded_2 = embedding(padded_2)
emb_padded_3 = embedding(padded_3)
emb_padded_4 = embedding(padded_4)

# Step 6: Masked mean pooling
def masked_mean_pool(embeddings, mask):
    """Mean-pool embeddings, ignoring padded positions."""
    mask_expanded = mask.unsqueeze(1)  # Shape: [max_len, 1]
    masked_embeddings = embeddings * mask_expanded
    sum_embeddings = masked_embeddings.sum(dim=0)
    count = mask.sum()
    return sum_embeddings / count

# Compute pooled vectors
pooled_1 = masked_mean_pool(emb_padded_1, mask_1)
pooled_2 = masked_mean_pool(emb_padded_2, mask_2)
pooled_3 = masked_mean_pool(emb_padded_3, mask_3)
pooled_4 = masked_mean_pool(emb_padded_4, mask_4)

# Step 7: Compute cosine similarities
sim_1_2 = cosine_similarity(pooled_1, pooled_2)  # Should be 1.0 (identical)
sim_3_4 = cosine_similarity(pooled_3, pooled_4)  # Should be lower

# Step 8: Print results
print(f"RESULT shape_emb_1 = {list(emb_1.shape)}")
print(f"RESULT shape_pooled_1 = {list(pooled_1.shape)}")
print(f"RESULT sim_identical = {sim_1_2:.6g}")
print(f"RESULT sim_different = {sim_3_4:.6g}")

# Step 9: Assertions to verify the concept
# Identical prompts should have cosine similarity of 1.0
assert abs(sim_1_2 - 1.0) < 1e-6, "Identical prompts should have cosine similarity 1.0"

# Different prompts should have lower similarity than identical ones
assert sim_3_4 < sim_1_2, "Different prompts should have lower cosine similarity than identical ones"

# Additional check: The similarity for different prompts should be less than 1.0
assert sim_3_4 < 1.0, "Different prompts should not have perfect cosine similarity"
