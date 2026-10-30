# CU-310 - Cross-attention versus joint attention

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome, students. You have survived CU-301, where we learned that attention is not magic; it is a weighted average of values, determined by the compatibility of queries and keys. But in CU-301, we treated all tokens as equals. In the real world of generative AI, tokens are not equals. They are distinct entities with distinct roles.

The central architectural question of modern diffusion transformers is: *How do we let the image "see" the text?*

There are two dominant answers. The first is **Cross-Attention**, the classic mechanism of Stable Diffusion 1.5 and 2. Here, the image tokens ask questions, but they only look at the text tokens for answers. The image and text remain separate streams that meet only at the attention layer. The second is **Joint Attention** (or Self-Attention over a concatenated sequence), the mechanism of SD3, Flux, and MMDiT. Here, image and text tokens are merged into a single, unified context. They all look at each other.

This distinction is not merely academic. It dictates memory usage, training stability, and the fidelity of text rendering. If you do not understand who is attending to whom, you cannot debug why your prompt is being ignored, or why your model is hallucinating. Today, we dissect the machinery.

## The intuition

Imagine a library.

In **Cross-Attention**, the readers (image tokens) are in the main hall. The books (text tokens) are in a separate archive. The readers cannot walk into the archive. Instead, they send a librarian (the Query) to the archive. The librarian looks at the spines of the books (Keys) and pulls out the relevant pages (Values). The readers never see the books directly; they only receive the information the librarian brings back. The readers do not talk to each other in this specific step, nor do they talk to the books. They only talk to the librarian.

In **Joint Attention**, the readers and the books are in the same room. Every reader can look at every other reader and every book. Every book can look at every reader. The information flows bidirectionally and globally. A reader can be influenced by another reader’s interpretation of a book, and a book’s representation can be updated by how readers are reacting to it.

Cross-Attention is a **decoupled** system. It strictly separates the conditioning signal (text) from the generated signal (image). This is efficient and stable, but it limits the depth of interaction. Joint Attention is a **unified** system. It allows for deep, iterative refinement where text and image co-evolve. This is more powerful for complex tasks like typography, but it is computationally heavier because the sequence length grows.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us define the symbols precisely.

Let $Q$ be the Query matrix, $K$ be the Key matrix, and $V$ be the Value matrix.
Let $d$ be the dimensionality of the embeddings.
Let $L_q$ be the length of the query sequence.
Let $L_k$ be the length of the key/value sequence.

### Cross-Attention

In cross-attention, the queries come from one stream (e.g., image), and the keys and values come from another (e.g., text).

1.  **Scores**: We compute the dot product of $Q$ and $K^T$, scaled by $\sqrt{d}$.
    $$S_{cross} = \frac{Q K^T}{\sqrt{d}}$$
    Here, $Q$ is shape $[B, L_q, d]$ and $K$ is shape $[B, L_k, d]$. The result $S_{cross}$ is shape $[B, L_q, L_k]$. Each row represents one image token looking at all text tokens.

2.  **Weights**: We apply softmax over the last dimension (the text tokens).
    $$W_{cross} = \text{softmax}(S_{cross}, \text{dim}=-1)$$
    This ensures that for each image token, the attention weights over the text tokens sum to 1.

3.  **Output**: We multiply the weights by the values.
    $$O_{cross} = W_{cross} V$$
    The output $O_{cross}$ is shape $[B, L_q, d]$. Crucially, the output length is $L_q$. The image tokens are updated, but the text tokens are not touched in this operation.

### Joint Attention

In joint attention, we concatenate the sequences. Let $X_{img}$ be the image tokens and $X_{txt}$ be the text tokens.

1.  **Concatenation**:
    $$X_{joint} = [X_{img}, X_{txt}]$$
    The new sequence length is $L_{joint} = L_q + L_k$.

2.  **Projections**: We project $X_{joint}$ into $Q$, $K$, and $V$. Note that $Q$, $K$, and $V$ are all derived from the same combined sequence.
    $$Q_{joint} = X_{joint} W_Q, \quad K_{joint} = X_{joint} W_K, \quad V_{joint} = X_{joint} W_V$$
    All are shape $[B, L_{joint}, d]$.

3.  **Scores**:
    $$S_{joint} = \frac{Q_{joint} K_{joint}^T}{\sqrt{d}}$$
    The result is shape $[B, L_{joint}, L_{joint}]$. This is a square matrix. Every token (image or text) attends to every other token (image or text).

4.  **Weights and Output**:
    $$W_{joint} = \text{softmax}(S_{joint}, \text{dim}=-1)$$
    $$O_{joint} = W_{joint} V_{joint}$$
    The output is shape $[B, L_{joint}, d]]. To get the updated image tokens, we slice the first $L_q$ rows. To get the updated text tokens, we slice the last $L_k$ rows.

The key difference: In cross-attention, the text representation is static during the image update. In joint attention, the text representation is dynamic and is updated simultaneously with the image.

## In ComfyUI

ComfyUI supports both paradigms, but they are implemented in different modules.

For **Cross-Attention**, look at `comfy/ldm/modules/attention.py`. The class `CrossAttention` is explicitly defined as a "Module for cross-attention layers between query and context." This is the standard block used in UNet-based models like SD 1.5. The `BasicTransformerBlock` in the same file combines self-attention, cross-attention, and feed-forward layers, adhering to the classic architecture.

For **Joint Attention**, look at `comfy/ldm/modules/diffusionmodules/mmdit.py`. This file contains the `MMDiT` class, which is the "Main class for Multi-Modal Diffusion Transformer (SD3/Flux style) models." The `SelfAttention` module here is not a simple self-attention; it operates on the joint sequence of image and text tokens. The `DismantledBlock` and `JointBlock` classes manage the flow of these unified tokens.

In `comfy/ldm/kandinsky5/model.py`, we see a hybrid approach where `CrossAttention` inherits from `SelfAttention`, allowing for flexible configuration, but the core distinction remains: cross-attention separates the streams, while joint attention merges them.

## Lab

We will run a small CPU-only experiment to visualize the shape differences and the independence of the outputs.

The lab defines:
*   `batch_size = 1`
*   `seq_len_q = 4` (Image tokens)
*   `seq_len_k = 3` (Text tokens)
*   `dim = 8`

It generates random tensors for $Q$, $K$, and $V$. It computes cross-attention where $Q$ is image and $K/V$ are text. It then computes joint attention by concatenating $Q$ and $K$ into a single sequence for all three roles.

Here are the results:

```
RESULT cross_attention_output_shape = torch.Size([1, 4, 8])
RESULT joint_attention_output_shape = torch.Size([1, 7, 8])
RESULT cross_attention_first_token = 1.50523
RESULT joint_attention_first_token = -0.681057
```

**What this proves:**

1.  `cross_attention_output_shape = torch.Size([1, 4, 8])`: The output length is $L_q$ (4). The image tokens are updated, but the text tokens are not part of the output stream. This confirms the decoupled nature of cross-attention.
2.  `joint_attention_output_shape = torch.Size([1, 7, 8])`: The output length is $L_q + L_k$ (4 + 3 = 7). The output contains both image and text tokens. This confirms the unified nature of joint attention.
3.  `cross_attention_first_token = 1.50523`: This is the first value of the first image token after attending to text.
4.  `joint_attention_first_token = -0.681057`: This is the first value of the first image token after attending to the joint sequence. The values are different because in joint attention, the first image token also attends to other image tokens, whereas in cross-attention, it only attends to text tokens.

## Common mistakes

1.  **Assuming Cross-Attention is "weaker"**: It is not weaker; it is more efficient. For simple text-to-image, cross-attention is often sufficient and faster. Joint attention is necessary for tasks requiring deep interaction, like rendering text within the image.
2.  **Confusing Self-Attention with Joint Attention**: In MMDiT, "Self-Attention" is applied to the joint sequence. It is not self-attention on just the image. Always check the input shape.
3.  **Ignoring the Scaling Factor**: Forgetting to divide by $\sqrt{d}$ in the dot product leads to vanishing gradients. Both cross and joint attention require this scaling.
4.  **Misinterpreting the Output Slice**: In joint attention, if you forget to slice the output to extract only the image tokens, you will pass text tokens into the next layer, corrupting the image generation.

## Go deeper

For the theoretical foundation of the joint attention architecture used in SD3 and Flux, read:

*   **arXiv:2403.03206**: "Scaling Rectified Flow Transformers for High-Resolution Image Synthesis". This paper introduces the MMDiT architecture, which uses separate weights for the two modalities but enables a bidirectional flow of information between image and text tokens via joint attention. It demonstrates that this architecture follows predictable scaling trends and improves text comprehension and typography.

