import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define a small sequence length and embedding dimension
seq_len = 5
dim = 8

# Create a random input sequence of tokens (just random vectors for demonstration)
# In a real model, these would be token embeddings
x = torch.randn(seq_len, dim, dtype=torch.float32)

# --- Part 1: Bidirectional Mask (Encoder-only style) ---
# In an encoder (like BERT), every token can attend to every other token.
# The mask is all ones (or True) for all positions.
# We represent the attention mask as a boolean tensor where True means "allowed to attend".
bidir_mask = torch.ones(seq_len, seq_len, dtype=torch.bool)

# --- Part 2: Causal Mask (Decoder-only style) ---
# In a decoder (like GPT), each token can only attend to previous tokens and itself.
# This is a lower-triangular matrix of True values.
causal_mask = torch.tril(torch.ones(seq_len, seq_len, dtype=torch.bool))

# Helper function to compute simple self-attention with a given mask
# This is a simplified version: Q, K, V are all the same input x for demonstration
def simple_attention(x, mask):
    # For simplicity, let Q = K = V = x
    # Attention scores: Q @ K^T / sqrt(d)
    scores = torch.matmul(x, x.T) / math.sqrt(dim)
    
    # Apply mask: set disallowed positions to -inf so they get 0 weight after softmax
    # We use a large negative number instead of -inf for numerical stability in this toy example
    scores = scores.masked_fill(~mask, -1e9)
    
    # Softmax over the last dimension (keys)
    attn_weights = torch.softmax(scores, dim=-1)
    
    # Weighted sum of values
    output = torch.matmul(attn_weights, x)
    return output, attn_weights

# Compute attention outputs for both masks
bidir_out, bidir_weights = simple_attention(x, bidir_mask)
causal_out, causal_weights = simple_attention(x, causal_mask)

# --- Analysis: Which positions can each token see? ---
# For bidirectional: each token sees all tokens
# For causal: token i sees tokens 0..i

# Check bidirectional: each row should have all True
bidir_visible_counts = bidir_mask.sum(dim=1)
# Check causal: token i should see i+1 tokens
causal_visible_counts = causal_mask.sum(dim=1)

# --- Key Concept: Final-token pooling in causal model ---
# In a causal model, the last token's representation aggregates information from all previous tokens.
# In contrast, the first token in a causal model only sees itself.

# Let's verify this by checking the attention weights:
# For the last token (index seq_len-1) in causal mask, it should attend to all previous tokens
last_token_causal_weights = causal_weights[-1, :]  # Attention weights of last token over all keys

# For the first token (index 0) in causal mask, it should only attend to itself
first_token_causal_weights = causal_weights[0, :]  # Attention weights of first token over all keys

# In a causal mask, the first token can only attend to position 0
# So first_token_causal_weights should be [1, 0, 0, 0, 0] (approximately)
# The last token can attend to all positions, so its weights should be non-zero for all positions

# Let's compute the sum of attention weights for the first token over non-self positions
first_token_non_self_sum = first_token_causal_weights[1:].sum().item()

# And for the last token, check that it attends to earlier tokens
last_token_earlier_sum = last_token_causal_weights[:-1].sum().item()

# --- Assertions to verify the concepts ---
# 1. In causal attention, the first token should only attend to itself
#    So the sum of attention weights for positions 1..end should be ~0
assert abs(first_token_non_self_sum) < 1e-5, "First token in causal model should only attend to itself"

# 2. In causal attention, the last token should attend to earlier tokens
#    So the sum of attention weights for positions 0..end-1 should be > 0
assert last_token_earlier_sum > 0.0, "Last token in causal model should attend to earlier tokens"

# 3. Bidirectional mask should allow all tokens to see all tokens
assert (bidir_visible_counts == seq_len).all(), "Bidirectional mask should allow all tokens to see all tokens"

# 4. Causal mask: token i should see exactly i+1 tokens
expected_causal_counts = torch.arange(1, seq_len + 1)
assert torch.equal(causal_visible_counts, expected_causal_counts), "Causal mask should have token i seeing i+1 tokens"

# --- Print results ---
# Format: RESULT <name> = <value>
# Use f"{x:.6g}" for floats

# Print the visible counts for each token in bidirectional mask
for i in range(seq_len):
    print(f"RESULT bidir_visible_count_token_{i} = {bidir_visible_counts[i].item()}")

# Print the visible counts for each token in causal mask
for i in range(seq_len):
    print(f"RESULT causal_visible_count_token_{i} = {causal_visible_counts[i].item()}")

# Print the first token's attention weights in causal model
for j in range(seq_len):
    print(f"RESULT causal_first_token_attn_to_{j} = {first_token_causal_weights[j].item():.6g}")

# Print the last token's attention weights in causal model
for j in range(seq_len):
    print(f"RESULT causal_last_token_attn_to_{j} = {last_token_causal_weights[j].item():.6g}")

# Print the sum of non-self attention for first token (should be ~0)
print(f"RESULT causal_first_token_non_self_sum = {first_token_non_self_sum:.6g}")

# Print the sum of earlier-token attention for last token (should be > 0)
print(f"RESULT causal_last_token_earlier_sum = {last_token_earlier_sum:.6g}")

# Print a sample of the bidirectional attention weights for the first token
for j in range(seq_len):
    print(f"RESULT bidir_first_token_attn_to_{j} = {bidir_weights[0, j].item():.6g}")

# Print a sample of the bidirectional attention weights for the last token
for j in range(seq_len):
    print(f"RESULT bidir_last_token_attn_to_{j} = {bidir_weights[-1, j].item():.6g}")
