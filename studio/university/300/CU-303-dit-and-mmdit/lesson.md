# CU-303 - DiT and MM-DiT blocks

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the studio. In CU-301, we looked at the U-Net, a convolutional beast that processes images in a hierarchical, local manner. But in CU-303, we are dismantling that hierarchy. We are replacing the U-Net with a Transformer. Why? Because attention is not local; it is global. Every token can talk to every other token. This is the architecture of the modern frontier: the Diffusion Transformer, or DiT.

You will see this architecture in `comfy/ldm/cosmos` for video, `comfy/ldm/hydit` for HunYuanDiT, and `comfy/ldm/pixeldit` for PixelDiT. They all share a core philosophy: treat the latent space as a sequence of tokens, and let attention decide what matters. If you do not understand how these blocks modulate information based on the diffusion timestep, you are flying blind. You are not controlling the generation; you are merely observing it.

## The intuition

Imagine a painting in progress. In a U-Net, the brushstrokes are local; a pixel only knows its neighbors. In a DiT, the entire canvas is visible to every brushstroke. But here is the critical nuance: the "brush" changes depending on how much noise is currently in the painting.

This is where **AdaLN** (Adaptive Layer Normalization) comes in. It is the conductor of the orchestra. The diffusion timestep $t$ tells the model, "We are at step 50 of 1000." The AdaLN mechanism takes this time information and transforms it into **scale** and **shift** parameters. These parameters are then applied to the features inside every transformer block.

Think of it this way: when the image is pure noise (high $t$), the scale and shift might encourage the model to focus on global structure. When the image is nearly clean (low $t$), the modulation shifts to encourage fine-grained detail. The attention mechanism decides *who* looks at *whom*, but AdaLN decides *how strongly* and *in what direction* that attention is applied. Without AdaLN, the transformer would treat a noisy latent and a clean latent with the same indifference. With AdaLN, the model is aware of its own state.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us look at the mechanics. The core operation in a DiT block is the modulation of the hidden states.

Let $x$ be the input feature tensor of shape $[B, N, D]$, where $B$ is the batch size, $N$ is the number of tokens (patches), and $D$ is the feature dimension.
Let $t$ be the timestep embedding vector of shape $[B, D]$.

In a standard DiT implementation, such as the `Block` class in `comfy/ldm/cosmos/predict2.py` or `HunYuanDiTBlock` in `comfy/ldm/hydit/models.py`, we derive modulation parameters from $t$. Typically, a linear layer projects $t$ into a vector that is split into scale and shift components.

The modulation function is defined as:
$$x_{modulated} = x \cdot (1 + \text{scale}) + \text{shift}$$

Here, `scale` and `shift` are vectors of shape $[B, D]$. To apply this to the token dimension $N$, we broadcast `scale` and `shift` across the $N$ dimension. In code, this is often implemented by unsqueezing the scale and shift to shape $[B, 1, D]$ so they can multiply and add to $x$ of shape $[B, N, D]$.

This is not just a linear transformation. It is a conditional affine transformation. The "identity" case occurs when `scale` is 0 and `shift` is 0. In this case, $x_{modulated} = x \cdot (1 + 0) + 0 = x$. This property is crucial for stability; if the timestep embedding were zero, the block would act as a pass-through, preserving the input features.

In **MM-DiT** (Multimodal DiT), as seen in `comfy/ldm/pixeldit/model.py` with `MMDiTJointAttention`, the architecture extends this by maintaining separate query, key, and value projections for image and text streams. However, the fundamental modulation principle remains: the timestep conditions the flow of information between these streams.

## In ComfyUI

In ComfyUI, these architectures are not monolithic; they are modular.

*   **Cosmos**: The `comfy/ldm/cosmos` folder implements the `MiniTrainDIT` and `GeneralDIT` classes. The `Block` class here combines self-attention, cross-attention, and MLP layers with AdaLN modulation. It uses `VideoRopePosition3DEmb` for 3D rotary position embeddings, essential for video where temporal order matters.
*   **HunYuanDiT**: The `comfy/ldm/hydit` folder provides `HunYuanDiTBlock`. It uses `apply_rotary_emb` to maintain spatial awareness. The `modulate` function in `models.py` applies the shift and scale modulation we discussed.
*   **PixelDiT**: The `comfy/ldm/pixeldit` folder implements `MMDiTBlockT2I`. It uses `MMDiTJointAttention` to handle the bidirectional flow between text and image tokens. The `apply_adaln_` function in `modules.py` handles the adaptive normalization.

These classes are the building blocks. When you load a model in ComfyUI, you are instantiating these specific blocks, stacking them, and feeding them latent tensors.

## Lab

In this lab, we simulate the core mechanics of a DiT block: patchification and AdaLN modulation. We use a small latent tensor to demonstrate how spatial data becomes tokens and how timestep conditioning alters the features.

We run the following script:
1.  We patchify a $[1, 4, 16, 16]$ latent into $2 \times 2$ patches.
2.  We apply AdaLN modulation using random scale and shift vectors.
3.  We verify the identity property when scale and shift are zero.
4.  We calculate the token count for 512px and 1024px images, assuming a VAE downsample factor of 8 and a patch size of 2.

Here are the results from the lab execution:

```text
RESULT token_count_16x16 = 64
RESULT num_tokens_512 = 1024
RESULT num_tokens_1024 = 4096
RESULT identity_check = True
RESULT modulated_diff = 1.38815
```

Let us dissect what these numbers prove:

1.  `RESULT token_count_16x16 = 64`: This confirms that a $16 \times 16$ latent with $2 \times 2$ patches yields $8 \times 8 = 64$ tokens. This is the sequence length $N$ that the attention mechanism must process.
2.  `RESULT num_tokens_512 = 1024`: For a 512px image, the VAE produces a $64 \times 64$ latent. With $2 \times 2$ patches, this becomes $32 \times 32 = 1024$ tokens. This is a standard sequence length for high-resolution DiTs.
3.  `RESULT num_tokens_1024 = 4096`: For a 1024px image, the latent is $128 \times 128$. With $2 \times 2$ patches, this becomes $64 \times 64 = 4096$ tokens. Notice the quadratic increase in tokens as resolution doubles. This is why DiTs are computationally expensive at high resolutions; attention complexity scales with $N^2$.
4.  `RESULT identity_check = True`: This proves that when `scale` and `shift` are zero, the modulation function returns the original tensor. This is the mathematical guarantee that the conditioning is additive and multiplicative in a controlled way.
5.  `RESULT modulated_diff = 1.38815`: This is the mean absolute difference between the original tensor and the modulated tensor. It shows that the modulation significantly alters the features, confirming that the timestep conditioning is actively shaping the data flow.

## Common mistakes

1.  **Ignoring the Patch Size**: Students often assume the latent size equals the token count. Remember, the patch size $P$ reduces the token count by a factor of $P^2$. A $16 \times 16$ latent with $P=2$ is not 256 tokens; it is 64.
2.  **Misunderstanding AdaLN**: Do not think of AdaLN as just another layer norm. It is a *conditional* layer norm. The scale and shift are not fixed weights; they are derived from the timestep. If you hardcode them, you break the diffusion process.
3.  **Confusing Self-Attention with Cross-Attention**: In MM-DiT, the image and text streams attend to each other. In standard DiT, the image tokens attend to themselves (self-attention) and to the text embedding (cross-attention). Mixing these up leads to incorrect architectural assumptions.
4.  **Neglecting Positional Embeddings**: DiTs are permutation-invariant by default. Without RoPE or sinusoidal embeddings, the model does not know which token is at the top-left and which is at the bottom-right. Always check if your implementation includes positional encoding.

## Go deeper

To truly master this, read the foundational papers:

*   **arXiv:2212.09748**: "Scalable Diffusion Models with Transformers" (Peebles & Xie). This is the original DiT paper. It establishes the baseline for using transformers in latent diffusion and introduces the AdaLN modulation scheme we discussed.
*   **arXiv:2403.03206**: "Scaling Rectified Flow Transformers for High-Resolution Image Synthesis" (Esser et al.). This paper introduces the MM-DiT architecture, which uses separate weights for image and text modalities. It is the theoretical basis for the `MMDiTJointAttention` you see in `comfy/ldm/pixeldit`.

Study these papers. Understand the math. Then, go back to ComfyUI and see how the code implements these ideas. The architecture is not magic; it is mathematics, made executable.

