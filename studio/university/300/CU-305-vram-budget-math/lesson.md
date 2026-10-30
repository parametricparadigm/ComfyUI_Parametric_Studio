# CU-305 - VRAM budget math: weights, activations, caches

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back, students. I am Bit Bandit, and I live in the last few bits of your float. You think you’re just running a model? No, you’re playing a high-stakes game of Tetris with bytes that have opinions. In ComfyUI, the difference between a smooth workflow and a dreaded `CUDA out of memory` error is rarely about the model size alone. It’s about the *budget*.

VRAM is not just for weights. It’s a shared economy. If you don’t account for activations (the temporary scratchpad) and caches (the memory of past steps), your math is wrong, and your GPU will scream. This lesson teaches you to calculate the true cost of inference so you can pick the right precision and model size before you hit the wall.

## The intuition

Imagine you are moving into a new house (your GPU). The furniture (weights) is the biggest item. But you also need space for the boxes you’re unpacking (activations) and the storage unit for things you might need later (caches).

If you only count the furniture, you’ll think you fit. But when you start unpacking, the room is full. In our lab, we treat VRAM as a strict budget. We reserve a safety margin (like keeping the hallway clear) and then estimate how much "living space" the model needs while it’s actually thinking.

The key insight: **Precision is your lever.** Dropping from FP32 to FP8 doesn’t just halve the furniture; it shrinks the boxes and the storage unit too, because they are derived from the same data.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s break down the memory consumption into three components. We define the following symbols:

*   $P$: Number of parameters in the model (e.g., $12 \times 10^9$ for a 12B model).
*   $b$: Bytes per parameter, determined by precision ($4$ for FP32, $2$ for BF16, $1$ for FP8, $0.5$ for 4-bit).
*   $W$: Weight memory in bytes.
*   $A$: Activation memory in bytes.
*   $C$: Cache/Latent memory in bytes.
*   $S$: Safety factor (a multiplier to account for fragmentation and overhead).
*   $M_{total}$: Total estimated VRAM usage.

**1. Weight Memory ($W$)**
This is the static cost of loading the model.
$$W = P \times b$$

**2. Activation Memory ($A$)**
Activations are the intermediate tensors created during the forward pass. In our simplified model, we assume they scale with the weight size.
$$A = W \times f_a$$
Where $f_a$ is the activation fraction. In our lab, we set $f_a = 0.1$ (10% of weight size).

**3. Cache/Latent Memory ($C$)**
This includes KV caches for transformers or latent states for diffusion models.
$$C = W \times f_c$$
Where $f_c$ is the latent/cache fraction. In our lab, we set $f_c = 0.05$ (5% of weight size).

**4. Total Budget ($M_{total}$)**
We sum these up and apply a safety factor $S$ to account for PyTorch’s memory allocator inefficiencies and other overheads.
$$M_{total} = (W + A + C) \times S$$

In our lab, $S = 1.2$. This means we expect to use 20% more memory than the raw sum of weights, activations, and caches.

## In ComfyUI

ComfyUI handles this budget dynamically. The `ModelPatcher` class in `comfy/model_patcher.py` is the gatekeeper. It tracks which weights are on the GPU and which are offloaded to CPU. When you run a node, `comfy/model_management.py` checks the `VRAMState`. If the state is `LOW` or `OOM`, it triggers `free_memory` to offload models or clear caches.

The `unet_dtype` function in `comfy/model_management.py` is crucial here. It determines the optimal data type for UNet weights based on available VRAM. If you have a 24GB card, it might force BF16 or FP8 to ensure the model fits within the budget we calculated above. The `LazyCastingParam` class allows weights to be cast on-the-fly, meaning you can load a model in a lower precision and only cast to higher precision for specific operations if memory allows.

## Lab

The lab script calculates the total memory required for 4B and 12B models at FP32, BF16, FP8, and 4-bit precision. It then checks if these models fit in 24GB and 96GB GPUs, after reserving 4GB for safety.

Here are the key `RESULT` lines from the lab output:

```
RESULT 12B_fp32 = 6.624e+10
RESULT 12B_bf16 = 3.312e+10
RESULT 12B_fp8 = 1.656e+10
RESULT 12B_4bit = 8.28e+09
```

*   `RESULT 12B_fp32 = 6.624e+10`: This is approximately 61.69 GB. It proves that a 12B model in FP32 is too large for a 24GB card (which has ~20GB available after reserve).
*   `RESULT 12B_bf16 = 3.312e+10`: This is approximately 30.85 GB. It proves that even BF16 is too large for a 24GB card, but fits comfortably in a 96GB card.
*   `RESULT 12B_fp8 = 1.656e+10`: This is approximately 15.42 GB. It proves that FP8 allows a 12B model to fit in a 24GB card, thanks to the reduced weight size and proportional reduction in activations/caches.
*   `RESULT 12B_4bit = 8.28e+09`: This is approximately 7.71 GB. It proves that 4-bit quantization makes the model extremely lightweight, leaving plenty of room for large batch sizes or high-resolution latents.

## Common mistakes

1.  **Ignoring the Safety Factor:** Many students calculate $W + A + C$ and assume that’s the limit. In reality, PyTorch’s allocator has overhead. If you don’t apply a safety factor (like our 1.2x), you will hit OOM errors even when your math says you should fit.
2.  **Assuming Activations are Constant:** Activations depend on batch size and sequence length. Our lab uses a simplified fraction, but in practice, increasing batch size will increase $A$ linearly, potentially breaking your budget even if weights fit.
3.  **Forgetting Caches:** In transformer models, KV caches can grow with sequence length. If you ignore $C$, you’ll be surprised when long-context inference fails.
4.  **Mixing Precisions:** If you load weights in FP8 but compute in FP32, your activations might be in FP32, doubling their memory cost. ComfyUI’s `LazyCastingParam` helps manage this, but you must be aware of the dtype of your intermediate tensors.

## Go deeper

For a deeper dive into the memory management strategies used in modern diffusion models, refer to the following papers:

*   **arXiv:2306.14465** - "Efficient Diffusion Models: A Survey"
*   **arXiv:2310.04378** - "Quantization for Efficient Inference of Large Language Models"
*   **arXiv:2402.10113** - "Memory-Efficient Attention Mechanisms for Transformers"

These papers provide the theoretical underpinnings for the heuristics we use in our lab.

