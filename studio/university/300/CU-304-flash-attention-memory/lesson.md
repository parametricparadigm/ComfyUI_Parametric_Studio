# CU-304 - Why attention is O(n^2) and how Flash/Sage fix the memory

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back. You have mastered the architecture in CU-301; you know *what* the model does. Today, we discuss *how* it survives. In ComfyUI, whether you are running SDXL, SD3, or Kandinsky 5, the bottleneck is rarely the convolutional layers. It is attention.

The standard definition of attention requires every token to look at every other token. If your sequence length is $n$, the computational cost is $O(n^2)$. More critically, the memory footprint is $O(n^2)$. For a 64k token sequence, this is not a "slow" problem; it is an "out of memory" problem. We will dissect why this quadratic explosion occurs and how algorithms like FlashAttention and SageAttention (via quantization) decouple memory usage from sequence length, allowing us to process long contexts without blowing up your VRAM.

## The intuition

Imagine a ballroom where every guest must shake hands with every other guest. If there are 10 guests, there are 90 handshakes. If there are 100 guests, there are 9,900. If there are 10,000 guests, there are nearly 50 million handshakes. The number of interactions grows quadratically.

In standard attention, we compute a matrix of scores $S = QK^T$. This matrix is $n \times n$. We must store this entire matrix in high-bandwidth memory (HBM) before we can apply softmax and multiply by $V$. For large $n$, this $n \times n$ matrix becomes the dominant memory consumer.

The "Flash" insight is that we do not need to see the whole ballroom at once. We can process the guests in small groups (tiles). We compute the attention for one tile, update our running statistics (max and sum for softmax), and discard the tile. We never form the full $n \times n$ matrix in HBM. We keep the computation on the fast, small on-chip SRAM. This is IO-awareness: we optimize for data movement, not just arithmetic.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let $Q, K, V$ be matrices of shape $(n, d)$, where $n$ is sequence length and $d$ is head dimension.

**Standard Attention:**
1.  Compute scores: $S = Q K^T$. Shape: $(n, n)$.
2.  Compute weights: $A = \text{softmax}(S / \sqrt{d})$. Shape: $(n, n)$.
3.  Compute output: $O = A V$. Shape: $(n, d)$.

Memory cost: $O(n^2)$ for $S$ and $A$.

**FlashAttention (Tiled/Online Softmax):**
We partition $K$ and $V$ into tiles of size $t$. We iterate over these tiles. For each tile $j$:
1.  Compute partial scores: $S_j = Q K_j^T$. Shape: $(n, t)$.
2.  Update running max $m$ and sum $l$ for the softmax denominator.
    *   $m_{new} = \max(m_{old}, \max(S_j))$
    *   $l_{new} = l_{old} \cdot \exp(m_{old} - m_{new}) + \sum \exp(S_j - m_{new})$
3.  Update output accumulator:
    *   $O_{new} = O_{old} \cdot \exp(m_{old} - m_{new}) + \exp(S_j - m_{new}) V_j$

Crucially, $S_j$ is only $(n, t)$. If $t \ll n$, the memory footprint is $O(n \cdot t)$, which is linear in $n$ if $t$ is fixed. We never store the full $(n, n)$ matrix.

**Sage/Quantized Attention:**
In ComfyUI, we also see `attention_comfy_kitchen_int8`. This reduces the precision of $Q, K, V$ from fp16 to int8. This halves the memory bandwidth requirement and allows more tiles to fit in SRAM, further accelerating the IO-bound process.

## In ComfyUI

ComfyUI abstracts this complexity behind a registry system. You do not manually select FlashAttention; the system does it for you.

In `comfy/ldm/modules/attention.py`, the function `optimized_attention_for_device` selects the best backend based on your hardware. It checks for available libraries and registers them via `register_attention_function`.

Key implementations include:
*   `attention_flash`: Wrapper for Flash Attention implementations.
*   `attention_sub_quad`: Implements sub-quadratic attention for memory efficiency.
*   `attention_comfy_kitchen_int8`: Implements quantized attention using int8 precision.
*   `attention_basic`: The fallback standard dot-product attention.

For models like Kandinsky 5 (`comfy/ldm/kandinsky5/model.py`), the `SelfAttention` and `CrossAttention` modules support chunked forward passes (`_forward_chunked`) to manage memory usage, effectively applying the tiling logic at the module level.

## Lab

In this lab, we quantify the memory explosion and verify that tiled attention produces identical results to standard attention while using a fraction of the memory.

We first calculate the memory footprint of the full $n \times n$ attention matrix in fp16 (2 bytes per element) for various sequence lengths. Then, we implement `online_softmax_tiled_attention` and compare its output to `standard_attention`. Finally, we compare the memory required for the full matrix versus the tiled matrix for a 64k sequence.

Here are the results from the lab:

`RESULT mem_n_1024 = 2`
This proves that for a 1k sequence, the attention matrix is only 2 MB. It is negligible.

`RESULT mem_n_65536 = 8192`
This proves that for a 64k sequence, the attention matrix is 8 GB. This is why standard attention fails on long sequences; it consumes 8 GB of VRAM just for the score matrix, before even storing $Q, K, V$.

`RESULT max_abs_diff = 2.08616e-07`
This proves that our tiled implementation is numerically equivalent to standard attention. The difference is within floating-point precision limits.

`RESULT full_mem_64k_mb = 8192`
Reiterates the 8 GB cost of the full matrix for 64k tokens.

`RESULT tiled_mem_64k_mb = 32`
This is the critical result. By using a tile size of 256, we reduce the peak memory usage for the attention scores from 8192 MB to 32 MB. This is a 256x reduction in memory for the attention computation.

`RESULT all_checks_passed = 1`
Confirms that the tiled attention matches standard attention across multiple tile sizes (64, 128, 256) and that the memory savings are consistent with the theoretical ratio.

## Common mistakes

1.  **Assuming FlashAttention changes the math.** It does not. It is an exact algorithm. If your results change when switching backends, you have a bug in your implementation or a numerical instability in your inputs, not a difference in attention logic.
2.  **Ignoring the IO bottleneck.** On modern GPUs, arithmetic is fast; memory movement is slow. If you implement tiling but still move data back and forth to HBM inefficiently, you will not see the speedup. FlashAttention is "IO-aware" for a reason.
3.  **Using `attention_basic` for long sequences.** In ComfyUI, if `optimized_attention_for_device` fails to select a faster backend, you may fall back to `attention_basic`. This will OOM on long sequences. Ensure your environment has the correct libraries installed so `attention_flash` or `attention_sub_quad` is selected.

## Go deeper

To understand the theoretical underpinnings, read:

*   **arXiv:2205.14135**: *FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness*. This paper introduces the tiling strategy and proves the IO complexity is optimal for a range of SRAM sizes. It highlights the 15% end-to-end speedup on BERT-large and 3x speedup on GPT-2.
*   **arXiv:2307.08691**: *FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning*. This paper addresses the inefficiencies in the first version, achieving 50-73% of theoretical maximum FLOPs/s on A100 GPUs by improving work partitioning between thread blocks and warps.

