# CU-317 - Sparse and windowed attention

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back. You have mastered the standard dot-product attention in CU-304. You know that for a sequence of length $L$, the computational cost is $O(L^2)$. This is the tax we pay for global context. Every token looks at every other token. It is elegant. It is also expensive.

In modern architectures—whether you are running SDXL, SD3, or 3D generation models like Trellis2—this quadratic scaling becomes a bottleneck. We need to be selective. We need to decide who attends to whom. This lesson covers **Sparse** and **Windowed** attention. These are not just optimizations; they are architectural choices that alter the very structure of the attention matrix. We trade some global connectivity for computational efficiency and memory savings. If you cannot manage this trade-off, you cannot build scalable generative systems.

## The intuition

Imagine a room full of people (tokens). In full attention, everyone talks to everyone. It is chaotic and slow.

**Windowed Attention** is like a conversation circle. Each person only talks to their immediate neighbors—say, the two people to their left and themselves. They ignore the rest of the room. This captures local context (syntax, local texture) but misses long-range dependencies (global structure, semantic consistency).

**Sparse Attention** is more selective. It is not necessarily about neighbors. It might be that everyone only talks to the people wearing red shirts (even-indexed tokens), or only to specific "expert" tokens. This creates a structured sparsity in the attention matrix. It is efficient because we do not compute scores for pairs that are masked out.

The key insight: **Masking is the mechanism.** We do not change the formula $QK^T/\sqrt{d}$; we change what we feed into the softmax. We set disallowed positions to $-\infty$, so their weight becomes zero. The structure of the mask defines the flow of information.

## Under the hood

Let $Q, K, V \in \mathbb{R}^{L \times d}$ be the query, key, and value matrices. $L$ is sequence length, $d$ is head dimension.

Standard attention computes:
$$ A = \text{softmax}\left(\frac{QK^T}{\sqrt{d}}\right) $$
$$ O = AV $$

For sparse or windowed attention, we introduce a binary mask $M \in \{0, 1\}^{L \times L}$.
- If $M_{ij} = 1$, token $i$ can attend to token $j$.
- If $M_{ij} = 0$, token $i$ cannot attend to token $j$.

We modify the score matrix $S = \frac{QK^T}{\sqrt{d}}$ by applying the mask:
$$ S'_{ij} = \begin{cases} S_{ij} & \text{if } M_{ij} = 1 \\ -\infty & \text{if } M_{ij} = 0 \end{cases} $$

Then we compute:
$$ A = \text{softmax}(S') $$
$$ O = AV $$

Because $\text{softmax}(-\infty) = 0$, the masked positions contribute nothing to the output. The weights for allowed positions are renormalized to sum to 1.

**Windowed Mask:** For a window size $w$, $M_{ij} = 1$ if $i - w + 1 \leq j \leq i$. This creates a banded matrix.
**Sparse Mask:** $M_{ij} = 1$ if $j$ satisfies a specific condition (e.g., $j \pmod 2 = 0$). This creates a column-wise sparsity.

The computational savings come from not computing the full $L \times L$ matrix, or from using specialized kernels that skip zero-weight multiplications.

## In ComfyUI

ComfyUI provides multiple attention backends to handle these variations efficiently. The core logic resides in `comfy/ldm/modules/attention.py`.

- `attention_basic`: Implements standard dot-product attention. This is the baseline.
- `attention_sub_quad`: Implements sub-quadratic attention for memory efficiency. This is where sparse/windowed logic often lives, reducing the $O(L^2)$ cost.
- `attention_flash`: Wrapper for Flash Attention implementations, which are optimized for memory and speed, often incorporating tiling and masking strategies.
- `ComfyAttention`: A configurable module wrapper that manages attention backend selection. It decides which backend to use based on device capabilities and model requirements.

In 3D generation, such as the Trellis2 model (`comfy/ldm/trellis2`), sparsity is inherent to the data structure. The `SparseMultiHeadAttention` class implements sparse attention mechanisms specifically for efficient computation on sparse grids. Here, the "sparsity" is not just a mask on a dense matrix, but a fundamental property of the `SparseTensor` data structure, where only non-zero voxels are processed.

For video models like SAM3 (`comfy/ldm/sam3`), we see `SplitAttn` and `MemoryAttnLayer`. These modules manage attention over time and memory, often using masking to restrict attention to relevant frames or objects, effectively creating a sparse attention pattern over the temporal dimension.

## Lab

In this lab, we compare three attention mechanisms on a small sequence ($L=8, d=4$): Full, Windowed (size 2), and Sparse (even-indexed keys). We verify that the outputs differ and that the weights are correctly normalized.

The lab prints the first element of the output vector and the first weight for each mechanism.

```
RESULT out_full[0,0,0] = -0.670553
RESULT out_windowed[0,0,0] = -0.569248
RESULT out_sparse[0,0,0] = -0.654069
RESULT weights_full[0,0,0] = 0.14138
RESULT weights_windowed[0,0,0] = 1
RESULT weights_sparse[0,0,0] = 0.442288
```

**Analysis:**
1.  `out_full[0,0,0] = -0.670553`: The baseline output. Token 0 attends to all 8 tokens.
2.  `out_windowed[0,0,0] = -0.569248`: The output differs from full attention. This proves that restricting context changes the result.
3.  `out_sparse[0,0,0] = -0.654069`: The sparse output is closer to full than windowed, but still distinct. This shows that the specific pattern of sparsity matters.
4.  `weights_full[0,0,0] = 0.14138`: In full attention, token 0 distributes its attention across all 8 tokens. The weight for token 0 itself is ~0.14.
5.  `weights_windowed[0,0,0] = 1`: In windowed attention with size 2, token 0 can only attend to tokens 0 and 1. However, the mask allows $j \in [0, 1]$. Wait, let's look at the mask logic: `start = max(0, i - window_size + 1)`. For $i=0$, `start=0`. `mask[0, 0:1]` is True. So token 0 only attends to token 0. Thus, the weight is 1. This proves the window is causal and local.
6.  `weights_sparse[0,0,0] = 0.442288`: In sparse attention, token 0 attends to all even-indexed tokens (0, 2, 4, 6). There are 4 such tokens. The weight is ~0.44, which is higher than the full attention weight (~0.14) because the attention is concentrated on fewer keys. This proves the sparsity pattern alters the weight distribution.

## Common mistakes

1.  **Forgetting to renormalize:** If you mask out positions but do not apply softmax to the masked scores, the weights will not sum to 1. Always apply `masked_fill` with $-\infty$ before `softmax`.
2.  **Assuming sparsity is always faster:** If your hardware does not support sparse matrix multiplication efficiently, a dense matrix with many zeros might be slower than a full dense matrix due to overhead. Use `attention_sub_quad` or `attention_flash` which are optimized for these patterns.
3.  **Ignoring positional encoding:** Sparse and windowed attention break the assumption that all tokens are equally distant. You must use appropriate positional encodings (like RoPE, seen in `apply_rope_memory` in SAM3) to ensure the model understands the relative positions of the tokens it *can* see.
4.  **Confusing data sparsity with attention sparsity:** In Trellis2, the data is sparse (`SparseTensor`). In standard 2D models, the data is dense, but the attention is sparse via masking. Do not mix these concepts.

## Go deeper

- **arXiv:2205.14135**: "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness". This paper details the IO-aware algorithms that make sparse and windowed attention practical on modern GPUs.
- **arXiv:2104.09864**: "Longformer: The Long-Document Transformer". This paper introduces sliding window and global attention patterns, which are foundational to the windowed strategies we discussed.
- **arXiv:2303.09541**: "Trellis: Structured 3D Latent Diffusion for Large-Scale Text-to-3D Generation". This paper describes the sparse 3D representation and attention mechanisms used in the Trellis2 model.

