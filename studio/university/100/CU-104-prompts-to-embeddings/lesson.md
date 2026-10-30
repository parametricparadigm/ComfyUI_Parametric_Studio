# CU-104 - Prompts become numbers: tokens and embeddings

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome to the foundation. You have pressed "Queue Prompt." You believe you have sent a sentence. You are wrong. You have sent a list of integers.

In ComfyUI, text is not understood; it is *indexed*. Before a single pixel of noise is denoised, your prompt must be translated into a sequence of vectors that the model can attend to. If you do not understand how "the cat" becomes a row of floating-point numbers, you are flying blind. You are shouting into the void, hoping the void shouts back.

This lesson dissects the first step of the pipeline: the tokenizer and the text encoder. We will look at how ComfyUI handles this for various architectures, from Llama to T5, and why the shape of your data matters as much as its content.

## The intuition

Imagine a library. The books are your words. The shelf positions are your token indices.

When you type "the cat sat," the tokenizer does not read the meaning. It looks up "the" in a dictionary (the vocabulary) and finds it is at position 0. "Cat" is at position 1. "Sat" is at position 2.

Now, imagine each shelf position has a unique scent. The scent of "the" is faint and neutral. The scent of "cat" is warm and furry. The scent of "sat" is static and grounded.

The **embedding** is the scent. It is a vector—a list of numbers—that represents the semantic "smell" of that token. When the model processes your prompt, it is not reading words. It is smelling a sequence of scents. If two prompts smell similar, the model will generate similar images. If they smell different, the images diverge.

In our lab, we will prove this. We will show that identical prompts have a cosine similarity of exactly 1.0 (identical scent), while different prompts have a lower similarity (different scent).

## Under the hood (the mechanism; math in plain text, define every symbol)

The process is a two-stage lookup.

**Stage 1: Tokenization**
Let $T$ be your text string. The tokenizer $Z$ maps $T$ to a sequence of integers $I = [i_1, i_2, ..., i_n]$, where each $i_k$ is an index into the vocabulary $V$.
$$ I_k = Z(T_k) $$
In ComfyUI, this is handled by classes like `BPETokenizer` or `LlamaTokenizerFast` in `comfy/text_encoders/bpe_tokenizer.py`. These are not just simple lookups; they handle sub-word units (BPE) to manage unknown words.

**Stage 2: Embedding Lookup**
Let $E$ be the embedding matrix, a tensor of shape $|V| \times d$, where $d$ is the embedding dimension. The embedding for token $i_k$ is the row $E[i_k]$.
$$ v_k = E[i_k] $$
The result is a tensor of shape $n \times d$.

**Stage 3: Pooling (Optional but Common)**
Many models, like CLIP, require a single vector for the entire prompt, not a sequence. This is done via mean pooling.
Let $v_{pooled} = \frac{1}{n} \sum_{k=1}^{n} v_k$.
This collapses the sequence into a single vector of dimension $d$.

**Similarity Metric**
To compare two prompts, we use Cosine Similarity. For two vectors $a$ and $b$:
$$ \text{cosine\_sim}(a, b) = \frac{a \cdot b}{\|a\| \|b\|} $$
This value ranges from -1 to 1. 1 means identical direction (same meaning), 0 means orthogonal (unrelated), -1 means opposite.

In our lab, we use `torch.nn.Embedding` to create $E$. We define a small vocabulary of 10 words. We embed them into an 8-dimensional space. We then mean-pool the embeddings and compute cosine similarity.

## In ComfyUI

ComfyUI does not use a single text encoder. It is a chameleon. The `comfy/text_encoders` folder contains implementations for a vast array of models.

*   **Llama Variants**: `comfy/text_encoders/llama.py` contains `Llama2_`, the core transformer implementation. It uses `precompute_freqs_cis` for Rotary Position Embeddings (RoPE), which helps the model understand the order of tokens.
*   **T5**: `comfy/text_encoders/t5.py` implements `T5` and `T5Attention`. T5 is a text-to-text transformer, often used in SDXL and Flux for richer semantic understanding.
*   **Flux**: `comfy/text_encoders/flux.py` contains `FluxClipModel` and `Flux2TEModel`. Flux uses a dual-encoder approach, combining CLIP and T5.
*   **Tokenizers**: `comfy/text_encoders/bpe_tokenizer.py` provides `BPETokenizer`, a pure Python byte-level BPE tokenizer, and `LlamaTokenizerFast`, a drop-in replacement for the Hugging Face transformers library.

The `CLIP` class in `comfy/sd.py` is the high-level interface that orchestrates these components. It handles the loading of the text encoder weights and the execution of the forward pass.

Note: Specific node names for text encoding in the ComfyUI UI (like "CLIP Text Encode") are not covered in our source evidence, but the underlying classes listed above are the engine driving them.

## Lab

The lab script builds a toy tokenizer and embedding table to demonstrate the core concept: **text becomes vectors, and vectors have geometry.**

We define a vocabulary of 10 words. We create an embedding table of shape `[10, 8]`. We process two pairs of prompts:
1.  **Identical**: "the cat sat on mat" vs "the cat sat on mat"
2.  **Different**: "the dog ran in park" vs "the sun sat on mat"

We embed the tokens, mean-pool the sequences, and compute cosine similarity.

Here are the exact `RESULT` lines from the lab output:

```
RESULT shape_emb_1 = [5, 8]
```
**Proof**: The prompt "the cat sat on mat" has 5 tokens. Each token is mapped to an 8-dimensional vector. The output shape is `[5, 8]`. This confirms the tokenization and embedding lookup worked correctly.

```
RESULT shape_pooled_1 = [8]
```
**Proof**: After mean-pooling the 5 token vectors, we are left with a single vector of dimension 8. This is the "scent" of the entire prompt.

```
RESULT sim_identical = 1
```
**Proof**: The cosine similarity between two identical prompts is exactly 1.0. This is the mathematical definition of identical direction in vector space. If you type the same prompt twice, the model sees the same vector.

```
RESULT sim_different = -0.152111
```
**Proof**: The cosine similarity between "the dog ran in park" and "the sun sat on mat" is -0.152111. This is significantly lower than 1.0. In fact, it is negative, indicating that in this 8-dimensional toy space, these two prompts point in roughly opposite directions. This proves that different text inputs result in geometrically distinct vectors.

## Common mistakes

1.  **Assuming Word Order Doesn't Matter**: In our simple mean-pooling lab, order is lost. However, real models like Llama and T5 use attention mechanisms (see `Llama2_` and `T5Attention`) that are highly sensitive to order. "Cat sat on mat" is not the same as "Mat sat on cat."
2.  **Ignoring Tokenizer Limits**: If you use a word not in the vocabulary, the tokenizer will break it into sub-words (BPE) or mark it as unknown. This changes the embedding. Always check your model's tokenizer.
3.  **Confusing Embedding Dimension with Latent Dimension**: The embedding dimension (e.g., 768 for CLIP, 4096 for Llama) is the size of the text vector. The latent dimension (e.g., 4 for SD1.5, 16 for SDXL) is the size of the image noise. They are different spaces. The cross-attention mechanism bridges them.
4.  **Forgetting Padding**: In real inference, prompts are padded to a maximum length. The mask (as shown in the lab's `pad_and_mask` function) ensures that padding tokens do not contribute to the mean-pooled vector. If you ignore masks, your prompt's "scent" will be diluted by the "scent" of nothing.

## Go deeper

To understand the origins of these architectures, read:

*   **arXiv:2103.00020**: *Learning Transferable Visual Models From Natural Language Supervision* (CLIP). This paper introduced the concept of learning visual representations from raw text, which is the foundation of the `CLIP` class in ComfyUI.
*   **arXiv:1910.10683**: *Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer* (T5). This paper introduced the T5 architecture, which is implemented in `comfy/text_encoders/t5.py` and used in modern models like Flux and SDXL.

