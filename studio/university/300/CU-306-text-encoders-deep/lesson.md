# CU-306 - Text encoders: CLIP, T5 and LLM encoders

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters
Welcome back to the studio. You have mastered the diffusion process; you know how noise becomes image. But who tells the noise *what* to become? That is the text encoder. It is the bridge between human language and the latent space. In ComfyUI, this is not a single black box. It is a family of architectures, each with a different philosophy on how to read a sentence.

We are moving from the simple "bag of words" era to the era of context. Whether you are using the classic `CLIP` for stability, the robust `T5` for complex semantics, or the massive LLM-based encoders like `Llama` or `Qwen`, the core question remains: How does the model decide which part of your prompt influences which part of the image? Today, we dissect the machinery that answers that question.

## The intuition
Imagine a sentence: "A red car drives fast."
In a **bidirectional** encoder (like BERT or the CLIP text tower), the word "red" can look at "car" and "drives." It sees the whole context at once. It is like a room where everyone can see everyone else.
In a **causal** encoder (like GPT or Llama), the word "red" only sees itself. The word "car" sees "red" and "car." The word "fast" sees "red," "car," "drives," and "fast." It is a one-way mirror.

This distinction is critical. When you use a causal LLM as a text encoder, you are often taking the representation of the *last* token. Why? Because in a causal model, the last token has seen everything that came before it. It is the only token that has the full context of the sentence. The first token is blind to the future; the last token is the sum of the past.

## Under the hood (the mechanism; math in plain text, define every symbol)
At the heart of all these encoders is Self-Attention. Let us define the math plainly.

Let $x$ be your input sequence of token embeddings. Let $d$ be the dimension of these embeddings.
We compute three matrices: Query ($Q$), Key ($K$), and Value ($V$). In our simplified lab, $Q=K=V=x$.

The attention score is calculated as:
$$ \text{scores} = \frac{Q K^T}{\sqrt{d}} $$

Here, $Q K^T$ computes the dot product between every query and every key. This tells us how much each token should "attend" to every other token. We divide by $\sqrt{d}$ to keep the values stable.

Then, we apply a **mask**.
1.  **Bidirectional Mask**: A matrix of all 1s. Every position is allowed to attend to every other position.
2.  **Causal Mask**: A lower-triangular matrix. Position $i$ can only attend to positions $0$ through $i$. Positions $j > i$ are masked out.

We apply the mask by setting disallowed scores to a very large negative number (effectively $-\infty$). Then we apply Softmax:
$$ \text{attn\_weights} = \text{softmax}(\text{scores}) $$

Finally, the output is the weighted sum of values:
$$ \text{output} = \text{attn\_weights} \times V $$

In ComfyUI, you will see this logic implemented in various forms. For LLMs, you might see `Llama2_` in `comfy/text_encoders/llama.py` handling the core transformer logic. For T5, you will see `T5Attention` in `comfy/text_encoders/t5.py`, which adds relative position bias to the standard attention. For Qwen, the `QwenImageTransformerBlock` in `comfy/ldm/qwen_image/model.py` uses `apply_rotary_emb` to handle positional information, ensuring the model knows the order of tokens.

## In ComfyUI
ComfyUI organizes these encoders in the `comfy/text_encoders` folder.
*   **CLIP**: The classic. It uses a bidirectional transformer. The output is typically pooled to a single vector or a sequence of vectors that are projected into the diffusion model's space.
*   **T5**: Implemented in `comfy/text_encoders/t5.py`. It is a bidirectional encoder-decoder architecture. The `T5` class handles the forward pass. It is known for better handling of long prompts and complex grammar than CLIP.
*   **LLM Encoders**: This is the modern frontier.
    *   `comfy/text_encoders/llama.py` contains `Llama2_`, the core implementation for Llama models. It uses `precompute_freqs_cis` for Rotary Position Embeddings (RoPE).
    *   `comfy/text_encoders/qwen35.py` contains `Qwen35`, which supports Multi-Token Prediction (MTP) and uses `GatedDeltaNet` for attention.
    *   `comfy/text_encoders/gemma4.py` contains `Gemma4Base` for Gemma variants.

When you load a model in ComfyUI, the specific class in these files is instantiated. The text is tokenized (using `BPETokenizer` or `LlamaTokenizerFast` from `comfy/text_encoders/bpe_tokenizer.py`), passed through the transformer layers, and the final hidden states are extracted. For causal models, ComfyUI often extracts the last token's embedding as the primary conditioning signal, or uses a specific pooling strategy defined by the model's architecture.

## Lab
We ran a small experiment to visualize the difference between bidirectional and causal attention. We created a sequence of 5 random vectors and computed attention weights for both mask types.

Here are the key results from the lab output:

1.  `RESULT causal_visible_count_token_0 = 1`
    **Proof**: The first token in a causal model can only see itself. It has no context.
2.  `RESULT causal_visible_count_token_4 = 5`
    **Proof**: The last token in a causal model can see all 5 tokens. It has the full context.
3.  `RESULT causal_first_token_attn_to_0 = 1`
    **Proof**: Since the first token can only attend to itself, its attention weight to position 0 is 1.0 (100%).
4.  `RESULT causal_last_token_attn_to_4 = 0.88373`
    **Proof**: The last token attends heavily to itself (0.88), but also distributes attention to previous tokens.
5.  `RESULT causal_last_token_earlier_sum = 0.11627`
    **Proof**: The sum of attention weights the last token gives to all *previous* tokens is 0.116. This proves that the last token aggregates information from the entire sequence, not just itself.
6.  `RESULT bidir_visible_count_token_0 = 5`
    **Proof**: In a bidirectional model, even the first token can see all 5 tokens. Context is available from the start.

This lab confirms the intuition: Causal models build context sequentially. The last token is the "summary" of the sentence. Bidirectional models have global context from the start.

## Common mistakes
1.  **Assuming all LLMs are the same**: `Llama`, `Qwen`, and `Gemma` have different attention mechanisms. `Qwen35` uses `GatedDeltaNet`, while `Llama2_` uses standard RoPE. Do not assume weights are interchangeable.
2.  **Ignoring the tokenizer**: The `BPETokenizer` or `LlamaTokenizerFast` must match the model. If you use a Llama model with a CLIP tokenizer, the embeddings will be garbage.
3.  **Misunderstanding pooling**: For causal models, taking the *first* token as the conditioning vector is usually wrong. It lacks context. Always check if your workflow uses the last token or a specific pooling method.
4.  **Forgetting position embeddings**: `apply_rotary_emb` is crucial. Without it, the model doesn't know the order of words. "Cat eats dog" is different from "Dog eats cat."

## Go deeper
To understand the origins of these architectures, read the foundational papers:
*   **arXiv:2103.00020**: "Learning Transferable Visual Models From Natural Language Supervision" (CLIP). This paper introduced the concept of learning image representations from raw text, enabling zero-shot transfer.
*   **arXiv:1910.10683**: "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" (T5). This paper established the unified text-to-text framework that T5 uses, treating all NLP tasks as text-to-text problems.

These papers are the bedrock. The LLM encoders in ComfyUI are built upon the same transformer principles, scaled up and adapted for image generation.

> UNVERIFIED: name not in evidence:  for complex semantics, or the massive LLM-based encoders like 


