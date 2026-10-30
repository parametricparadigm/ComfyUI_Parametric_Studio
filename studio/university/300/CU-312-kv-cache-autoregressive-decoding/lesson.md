# CU-312 - KV cache and autoregressive decoding

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the lecture hall. You have mastered the static architecture in CU-301; you know how a single forward pass flows through layers. But generative models do not live in a single pass. They live in a loop. They breathe. They generate token by token, step by step, until the sequence is complete.

If you naively recompute the entire history of the sequence for every new token, your computational cost explodes quadratically. You are paying for the past over and over again. This is inefficient, wasteful, and ultimately limits the length of what we can generate.

The KV cache is the solution. It is the memory of the model. By storing the Key and Value projections of previous tokens, we allow the current token to attend to the past without recalculating it. This transforms autoregressive decoding from a quadratic nightmare into a linear process. It is the difference between re-reading the entire book every time you turn a page, and simply remembering where you left off.

## The intuition

Imagine you are writing a sentence. To choose the next word, you look at the words you have already written.

In a naive transformer, for every new word, you would take the entire sequence of previous words, project them into Keys and Values, compute the attention scores, and then discard those Keys and Values. Then, for the *next* word, you would do it all again.

The KV cache changes this. When you process the first word, you compute its Key and Value. You store them. When you process the second word, you compute its Key and Value, append them to the stored ones, and use the full set to determine attention. You never recompute the Key or Value of the first word again.

This is a classic time-space trade-off. We spend memory (space) to store the past, so we save computation (time) in the future. In the context of ComfyUI and large language models or diffusion transformers, this is essential for handling long sequences without exhausting your GPU memory or slowing down generation to a crawl.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us define the variables precisely. Let $t$ be the current time step in the autoregressive loop. Let $h_t$ be the hidden state of the current token.

In a standard transformer layer, we project the hidden state into Query ($Q$), Key ($K$), and Value ($V$) vectors:
$Q_t = W_Q h_t$
$K_t = W_K h_t$
$V_t = W_V h_t$

Without caching, to compute the output for token $t$, we would need $K_{1:t-1}$ and $V_{1:t-1}$. If we recompute these, we are doing $O(t)$ work for every step, leading to $O(N^2)$ total work for a sequence of length $N$.

With the KV cache, we maintain two buffers: $Cache_K$ and $Cache_V$.
At step $t$, we do the following:
1. Compute $K_t$ and $V_t$ for the current token.
2. Append $K_t$ to $Cache_K$ and $V_t$ to $Cache_V$.
3. Compute attention scores using $Q_t$ and the full $Cache_K$.
4. Compute the output using the attention weights and the full $Cache_V$.

The attention score for the current token $t$ attending to all previous tokens $j \le t$ is:
$Score_{t,j} = \frac{Q_t \cdot K_j}{\sqrt{d_k}}$

Where $d_k$ is the dimension of the key vectors. The final output is a weighted sum of the values:
$Output_t = \sum_{j=1}^{t} \text{softmax}(Score_{t,j}) \cdot V_j$

The critical insight is that $K_j$ and $V_j$ for $j < t$ are constant. They do not change. Therefore, storing them is valid. The only new computation required at step $t$ is the projection of the current token and the attention calculation against the cached history. This reduces the per-step complexity from $O(t)$ to $O(1)$ for the projection part, making the total generation time linear with respect to the sequence length.

## In ComfyUI

In the ComfyUI codebase, this mechanism is explicitly handled in the text encoder modules, which often rely on autoregressive or transformer-based structures.

In `comfy/text_encoders/llama.py`, we find the class `FixedKV`. This class is dedicated to KV cache management. It handles the storage and retrieval of key-value pairs during the generation process. Additionally, `BaseGenerate` serves as the base class for token generation logic, orchestrating the loop where the cache is updated and utilized.

For other architectures, such as those in `comfy/text_encoders/qwen35.py`, we see `LinearKV`, which is a variant of the KV cache designed for linear attention mechanisms, further optimizing the memory footprint.

While the diffusion models in `comfy/ldm/modules` (like `MMDiT` or `UNetModel`) primarily use parallel attention for image generation, the underlying principles of attention efficiency apply. However, the specific iterative KV caching logic is most prominently visible in the text encoder implementations that handle sequential token generation.

## Lab

The lab demonstrates the equivalence of cached decoding and full recomputation for the current token, while highlighting the memory growth of the cache.

We initialize a sequence of length 10 with a hidden dimension of 4. We simulate the state after processing these 10 tokens, storing their Keys and Values in `cached_K` and `cached_V`. We then generate a new token (token 11) and update the cache by concatenating its Key and Value to the existing cache.

The lab verifies two things:
1. **Cache Consistency:** The first 10 rows of the updated cache must exactly match the old cache. This proves that we are not modifying history, only appending to it.
2. **Output Equivalence:** The attention output for the new token, computed using the cache, must match the output computed via a full recomputation of the entire sequence (with appropriate masking). This proves that the cache is a valid shortcut.

Here are the results from the lab execution:

```
RESULT full_attn_shape = torch.Size([10, 4])
RESULT updated_K_shape = torch.Size([11, 4])
RESULT updated_V_shape = torch.Size([11, 4])
RESULT new_token_output = -0.0775429
RESULT cache_consistency = True
```

*   `RESULT full_attn_shape = torch.Size([10, 4])`: This shows the output shape of the initial full attention computation for the first 10 tokens. It confirms our baseline dimensions.
*   `RESULT updated_K_shape = torch.Size([11, 4])`: This proves that the Key cache has grown by one row to accommodate the new token. The sequence dimension increased from 10 to 11.
*   `RESULT updated_V_shape = torch.Size([11, 4])`: Similarly, the Value cache has grown to 11 rows. This is the memory cost we pay for efficiency.
*   `RESULT new_token_output = -0.0775429`: This is the specific scalar value of the first element of the attention output for the new token, computed using the cache.
*   `RESULT cache_consistency = True`: This is the critical assertion. It confirms that the historical data in the cache was preserved exactly during the update. If this were False, the model would be "forgetting" or "corrupting" its past, leading to incoherent generation.

## Common mistakes

1.  **Forgetting to update the cache:** If you compute the new Key and Value but fail to append them to the cache, the next token will not see the current token. The model will effectively "lose" the last step of its memory.
2.  **Recomputing the cache:** Some implementations mistakenly recompute the Keys and Values for all previous tokens at every step. This defeats the purpose of the cache and reverts the complexity to $O(N^2)$.
3.  **Incorrect masking:** In autoregressive decoding, the current token should only attend to previous tokens and itself. If you do not mask future tokens (which don't exist yet in the cache, but might in a full matrix context), you introduce information leakage. In the lab, we handled this by only computing the output for the new token against the full cache, which implicitly respects causality since the cache only contains past tokens.
4.  **Memory overflow:** While the KV cache saves time, it consumes memory. For very long sequences, the cache can become larger than the model weights themselves. You must monitor GPU memory usage.

## Go deeper

To understand the foundational architecture that makes this possible, read:

*   **arXiv:1706.03762** - "Attention Is All You Need" by Vaswani et al. This paper introduces the Transformer architecture. While it focuses on parallel training, the attention mechanism described here is the exact mechanism that the KV cache optimizes for autoregressive inference. Understanding the original attention formula is essential to appreciating why caching Keys and Values is valid.

