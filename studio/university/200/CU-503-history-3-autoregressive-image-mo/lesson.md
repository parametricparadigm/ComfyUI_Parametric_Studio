# CU-503 - History 3: Pixel by pixel, autoregressive image models

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back. You have spent the last few weeks watching diffusion models blur the boundaries between noise and signal, treating the image as a holistic field to be denoised in parallel. It is elegant, it is fast, and it is dominant. But it is not the only way to look.

Today, we step back to the foundational logic of sequential generation. We are examining **autoregressive image models**. In this paradigm, an image is not a field to be refined; it is a sentence to be spoken. One pixel at a time. Left to right, top to bottom.

Why care? Because understanding the strict causal dependency of autoregression clarifies the fundamental trade-off in generative AI: **parallelism versus precision**. Diffusion models sacrifice sequential context for speed. Autoregressive models sacrifice speed for a rigorous, token-by-token construction of reality. As we will see in the `comfy/ldm/pixeldit` architecture, even modern "diffusion" hybrids often borrow the structural rigor of sequential processing to handle high-resolution details.

## The intuition

Imagine you are painting a portrait. A diffusion model is like a photographer developing a photo in a darkroom: you start with a foggy, noisy sheet and gradually wipe away the fog until the image emerges. You can wipe any part of the sheet at any time; the process is largely parallel.

An autoregressive model is like a painter working with a fine brush. You must paint the top-left corner before you can paint the top-right. You cannot paint the bottom-right until the top-right is done. Every stroke you make is conditioned on every stroke that came before it.

This creates a **causal mask**. When the model predicts pixel $i$, it is allowed to "attend" to pixels $0$ through $i-1$. It is blind to pixels $i+1$ through $N$. This is the same logic that powers Large Language Models (LLMs), but applied to spatial data. The "language" here is the raw pixel values (or patches of pixels). The "grammar" is the spatial coherence of the image.

The key insight is **sequential dependency**. The prediction of the current pixel is not independent; it is a function of the entire history of the image so far. This allows the model to enforce global consistency locally. If you paint a blue sky in the top left, the model "remembers" this when it reaches the top right, ensuring the sky remains blue.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us formalize this. An image $I$ is a grid of pixels. We flatten this grid into a 1D sequence of length $N$. Let $x_i$ be the value of the $i$-th pixel in this sequence.

The autoregressive model learns the joint probability distribution $P(x_1, x_2, ..., x_N)$ by factoring it into a product of conditional probabilities:

$$P(x_1, ..., x_N) = \prod_{i=1}^{N} P(x_i | x_1, ..., x_{i-1})$$

Here:
*   $x_i$ is the target pixel value at position $i$.
*   $x_1, ..., x_{i-1}$ are the **context**: all previously generated pixels.
*   $P(x_i | x_1, ..., x_{i-1})$ is the probability of generating pixel $x_i$ given the history.

In a neural network implementation, this is typically achieved using a Transformer or Recurrent Neural Network (RNN). The input to the network at step $i$ is the sequence of embeddings for $x_1$ through $x_{i-1}$. The network outputs a distribution over possible values for $x_i$.

In the lab we will run, we simulate this with a simple heuristic: predicting the next pixel as the mean of all previous pixels. While a real model uses complex attention mechanisms (like those in `MMDiTJointAttention` or `RotaryAttention` found in ComfyUI's `pixeldit` module), the core logic remains: **the current output depends strictly on the preceding inputs.**

Contrast this with diffusion. In diffusion, the model predicts a denoised version of the *entire* image at once, conditioned on a noise level $\sigma$. There is no strict $x_i$ depends on $x_{i-1}$ constraint in the spatial domain; the dependencies are learned implicitly through the attention mechanism across the whole latent space.

## In ComfyUI

While ComfyUI is heavily optimized for diffusion pipelines, it supports architectures that utilize sequential or pixel-level processing.

The `comfy/ldm/pixeldit` folder is a prime example of this hybrid approach. It implements the **PixelDiT** (PixDiT) architecture. While PixDiT is a diffusion model, it operates at the **pixel level** rather than the latent level for its final decoding stages.

Key components include:
*   `PixDiT_T2I`: The main text-to-image model, hardcoded for 1024px resolution.
*   `PixelTokenEmbedder`: This module lifts each individual RGB pixel to the hidden size. This is crucial. Instead of processing a 16x16 latent patch, it processes individual pixels, allowing for fine-grained sequential or local attention.
*   `PiTBlock`: A pixel-level transformer block.
*   `RotaryAttention`: Used for positional encoding, ensuring the model knows the spatial relationship between pixels.

The `PidNet` decoder further extends this by injecting low-quality latent features into the pixel-level transformer. This allows the model to use the global structure from a diffusion latent while refining the details pixel-by-pixel. This is a nod to the autoregressive philosophy: even in a diffusion framework, the final "look" is often determined by local, sequential refinements.

Note: Pure autoregressive image models (like PixelRNN or PixelCNN) are less common in standard ComfyUI workflows compared to diffusion, but the underlying mechanisms of causal masking and sequential prediction are present in these pixel-level transformer blocks.

## Lab

In this lab, we simulate the core logic of autoregressive prediction using a simple 2x2 image. We flatten the image into a 1D sequence and predict each pixel based on the mean of all previous pixels. This is a trivial model, but it perfectly illustrates the **causal dependency**: pixel 3 cannot be predicted until pixels 0, 1, and 2 are known.

We will run the following script:

```python
import torch

# Define a small 2x2 image
true_image = torch.tensor([[0.1, 0.2],
                           [0.3, 0.4]], dtype=torch.float32)

# Flatten the image
flat_true = true_image.flatten()

# Predict each pixel autoregressively
predictions = []
for i in range(len(flat_true)):
    prev_pixels = flat_true[:i]
    if len(prev_pixels) == 0:
        pred = 0.0
    else:
        pred = torch.mean(prev_pixels).item()
    predictions.append(pred)

# Compute MSE
pred_tensor = torch.tensor(predictions, dtype=torch.float32)
mse = torch.mean((pred_tensor - flat_true) ** 2).item()

print(f"RESULT mse = {mse:.6g}")
print(f"RESULT pred_0 = {predictions[0]:.6g}")
print(f"RESULT pred_1 = {predictions[1]:.6g}")
print(f"RESULT pred_2 = {predictions[2]:.6g}")
print(f"RESULT pred_3 = {predictions[3]:.6g}")
```

**Lab Output:**

```
RESULT mse = 0.020625
RESULT pred_0 = 0
RESULT pred_1 = 0.1
RESULT pred_2 = 0.15
RESULT pred_3 = 0.2
```

**Analysis:**
1.  `RESULT pred_0 = 0`: The first pixel has no history. The model defaults to 0. This proves the **cold start** problem of autoregression: the first token is generated without context.
2.  `RESULT pred_1 = 0.1`: The second pixel is predicted as the mean of the first pixel (0.1). This proves that the prediction is **conditioned on the immediate past**.
3.  `RESULT pred_2 = 0.15`: The third pixel is the mean of the first two (0.1 + 0.2) / 2 = 0.15. This shows the **accumulation of context**. The model is not just looking at the last pixel, but the entire sequence so far.
4.  `RESULT pred_3 = 0.2`: The fourth pixel is the mean of the first three (0.1 + 0.2 + 0.3) / 3 = 0.2. This confirms the **sequential dependency** extends to the full history.
5.  `RESULT mse = 0.020625`: The Mean Squared Error is small but non-zero. This proves that a simple mean-based heuristic is not a perfect model, but it captures the trend. A real neural network would learn complex non-linear dependencies to reduce this error further.

## Common mistakes

1.  **Confusing Latent with Pixel Autoregression:** Many students assume "autoregressive" means "slow." While true for pixel-level autoregression (like PixelRNN), modern models often autoregress over **patches** or **tokens**, not individual pixels. This reduces the sequence length $N$ significantly, making it faster.
2.  **Ignoring the Causal Mask:** In a Transformer, if you forget to apply the causal mask, the model can "cheat" by looking at future pixels. This leads to data leakage and poor generalization. Always ensure your attention mask enforces $i > j$ for queries and keys.
3.  **Assuming Diffusion is Parallel in All Aspects:** While diffusion denoising is parallel, the *training* of the model involves learning dependencies across the entire image. The inference is parallel, but the learned representation is holistic. Autoregression, by contrast, builds the representation sequentially.

## Go deeper

To understand the origins of this approach, read:

*   **arXiv:1601.06759**: *Pixel Recurrent Neural Networks* by van den Oord et al. This paper introduced the PixelRNN, which sequentially predicts pixels using a 2D recurrent structure. It established the baseline for autoregressive image modeling, demonstrating that a model can learn the complex dependencies of natural images by processing them pixel by pixel.

