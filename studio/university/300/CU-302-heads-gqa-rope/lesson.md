# CU-302 - Multi-head, GQA and RoPE

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back. In CU-301, we looked at the Transformer as a black box that predicts the next token. Today, we open the hood. We are going to dissect the three mechanisms that allow a model to understand *structure*, *efficiency*, and *space*.

Without **Multi-Head Attention (MHA)**, your model is a monolith; it sees the whole sentence but cannot simultaneously track syntax, semantics, and coreference. Without **Grouped-Query Attention (GQA)**, your inference is painfully slow because you are storing redundant memory for every single head. Without **Rotary Position Embedding (RoPE)**, your model is amnesiac regarding order; it treats "cat sat" and "sat cat" as identical sets of tokens.

In ComfyUI, these are not just theoretical concepts. They are the gears turning inside `HunYuanDiT`, `SAM3`, and `TripoSplat`. Whether you are generating a 4K image or tracking an object in video, these mechanisms determine how the model attends to whom.

## The intuition

Imagine a committee deciding on a policy.

**Multi-Head Attention** is like having four different experts in the room. One expert looks only at the grammar, another at the emotional tone, another at the factual accuracy, and the fourth at the logical flow. They all look at the same document (the input sequence), but they extract different features. At the end, they merge their opinions. This is why we split the hidden dimension into heads.

**Grouped-Query Attention (GQA)** is an optimization. In standard MHA, every expert (Query head) has its own dedicated notepad (Key/Value heads). This is expensive. GQA says: "Experts 1 and 2 can share a notepad. Experts 3 and 4 can share another." You reduce the number of notepads (KV heads) while keeping the number of experts (Q heads) the same. The quality remains close to MHA, but the memory footprint drops significantly.

**RoPE** is how the experts know *where* things are. Instead of adding a position vector to the token (which can interfere with the content), RoPE *rotates* the vector itself. Think of it as a compass. If I rotate my compass needle by 10 degrees, I know my position relative to North. If I rotate it by 20 degrees, I know I am further away. The dot product between two rotated vectors depends only on the *difference* in their rotations (the relative distance), not their absolute orientation. This gives the model a built-in sense of relative distance.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us define the variables. Let $x$ be the input tensor of shape $(seq\_len, hidden\_dim)$.

**1. Multi-Head Split**
We split $x$ into $num\_heads$ sub-vectors.
$$x\_heads = x.view(seq\_len, num\_heads, head\_dim).permute(1, 0, 2)$$
Here, $head\_dim = hidden\_dim / num\_heads$. The result is a tensor of shape $(num\_heads, seq\_len, head\_dim)$. Each head computes attention independently.

**2. GQA Parameter Reduction**
In standard MHA, the Key and Value projections are matrices of size $(hidden\_dim, hidden\_dim)$.
In GQA, we introduce a $group\_size$. The number of KV heads is $num\_kv\_heads = num\_heads / group\_size$.
The Key projection matrix becomes $(hidden\_dim, hidden\_dim / group\_size)$.
The parameter count for K and V drops by a factor of $group\_size$.

**3. RoPE (Rotary Position Embedding)**
For a vector $x$ at position $m$, we rotate it using a matrix $R_m$.
The rotation is applied to pairs of dimensions. For a dimension $i$, the angle is:
$$\theta_i = m \cdot 10000^{-2i/d}$$
where $d$ is the head dimension.
The rotation for a pair $(x_{2i}, x_{2i+1})$ is:
$$x'_{2i} = x_{2i} \cos(\theta_i) - x_{2i+1} \sin(\theta_i)$$
$$x'_{2i+1} = x_{2i} \sin(\theta_i) + x_{2i+1} \cos(\theta_i)$$
Crucially, this is a rotation, so it preserves the norm (length) of the vector.

## In ComfyUI

These mechanisms are deeply embedded in ComfyUI's model implementations.

*   **`comfy/ldm/hydit`**: The HunYuanDiT model uses `Attention` and `CrossAttention` modules from `attn_layers.py`. It explicitly uses `apply_rotary_emb` to apply RoPE to query and key tensors. The `posemb_layers.py` file contains `get_2d_rotary_pos_embed`, which generates the 2D rotary embeddings specific to image patches.
*   **`comfy/ldm/sam3`**: The SAM3 tracker uses `apply_rope_memory` to apply 2D axial RoPE to memory attention. This allows the model to track objects across time and space by encoding their relative positions in the memory buffer.
*   **`comfy/ldm/triposplat`**: The TripoSplat model uses `RopeMultiHeadAttention` and `RePo3DRotaryEmbedding`. This is a specialized adaptation of RoPE for 3D point clouds, allowing the model to understand spatial relationships in 3D Gaussian Splatting.

Note: While GQA is a standard architectural choice in many modern LLMs, the specific ComfyUI code evidence provided here highlights the use of standard `MultiHeadAttention` and RoPE implementations. The specific GQA node configurations are not covered in our sources, but the mathematical principles apply to any transformer block where KV heads are grouped.

## Lab

In this lab, we verify three properties:
1.  **Split/Merge Identity**: Splitting a tensor into heads and merging it back should result in the original tensor.
2.  **GQA Efficiency**: We calculate the parameter count for MHA vs. GQA with a group size of 2.
3.  **RoPE Properties**: We verify that RoPE preserves vector norms and that the attention score depends only on relative position.

Here are the results from our lab run:

```text
RESULT split_merge_identity = True
RESULT mha_total_params = 192
RESULT gqa_total_params = 128
RESULT kv_reduction_ratio = 2
RESULT rope_norm_preserved = True
RESULT rope_relative_pos_score1 = -1.38599
RESULT rope_relative_pos_score2 = -1.38599
RESULT rope_relative_pos_equal = True
```

*   `RESULT split_merge_identity = True`: Proves that the reshape and permute operations for multi-head attention are reversible and lossless.
*   `RESULT mha_total_params = 192` and `RESULT gqa_total_params = 128`: Shows that with a group size of 2, GQA reduces the total parameter count for Q, K, V projections from 192 to 128.
*   `RESULT kv_reduction_ratio = 2`: Confirms that the Key/Value parameter reduction is exactly equal to the group size.
*   `RESULT rope_norm_preserved = True`: Proves that RoPE is a pure rotation; it does not change the magnitude of the vector, only its direction.
*   `RESULT rope_relative_pos_score1 = -1.38599` and `RESULT rope_relative_pos_score2 = -1.38599`: These two scores are identical. In Case 1, the query is at position 0 and key at 2 (offset -2). In Case 2, query is at 1 and key at 3 (offset -2). The fact that the scores are equal proves that RoPE encodes *relative* position, not absolute position.

## Common mistakes

1.  **Confusing Absolute and Relative Position**: If you use additive positional embeddings, the model learns absolute positions. If you use RoPE, the model learns relative positions. Do not mix them incorrectly. RoPE is applied to Q and K *before* the dot product.
2.  **Ignoring Head Dimension Parity**: RoPE requires the head dimension to be even because it operates on pairs of dimensions. If your `head_dim` is odd, the rotation logic will break or require padding.
3.  **Assuming GQA is Free**: While GQA reduces memory, it can slightly degrade quality if the group size is too large. The evidence from the GQA paper (arXiv:2305.13245) suggests that uptraining is required to maintain quality close to MHA.

## Go deeper

*   **arXiv:2104.09864**: *RoFormer: Enhanced Transformer with Rotary Position Embedding*. This paper introduces RoPE and proves its ability to incorporate explicit relative position dependency into self-attention.
*   **arXiv:2305.13245**: *GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints*. This paper introduces Grouped-Query Attention and provides a recipe for uptraining existing MHA checkpoints into GQA models using only 5% of the original pre-training compute.

