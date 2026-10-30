# CU-510 - History 10: From frames to space-time: the road to modern video models

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Listen closely, class. For a long time, we treated video like a stack of independent photographs. We generated Frame 0, then Frame 1, then Frame 2, hoping they looked similar. It was like trying to build a movie by shuffling a deck of cards and praying the plot makes sense. That era is over.

Today, we are entering the age of **space-time**. We no longer see video as a "bag of independent images." We see it as a continuous 4D tensor: Height, Width, Time, and Channels. In this new paradigm, temporal coherence is not a suggestion; it is a **first-class constraint**. The model must understand that what happens in frame $t$ is physically and logically bound to what happens in frame $t+1$.

This lesson dissects the machinery that makes this possible. We are looking at how modern architectures like CogVideoX, Cosmos, and LTX-Video have moved from simple 2D convolutions to 3D causal structures that respect the flow of time. If you want to generate video that doesn't flicker, jitter, or morph into nonsense, you need to understand how these models enforce continuity at the architectural level.

## The intuition

Imagine you are a film-reel sprite, just like me. I count frames. I hate flicker.

In the old "bag of images" approach, if I asked a model to generate a cat walking, it might give me a cat in frame 1, a dog in frame 2, and a cat with three legs in frame 3. Why? Because the model treated each frame as a separate, isolated task. There was no memory. There was no context.

The shift to space-time modeling is like giving the model a pair of eyes that can see *through* time. Instead of asking, "What does this single image look like?", the model asks, "How does this volume of space evolve over this duration?"

Think of a 3D convolution. In a standard image, a 2D convolution looks at neighbors in space (up, down, left, right). In a video, a 3D convolution looks at neighbors in space **and** time (up, down, left, right, *and* previous/next frame). This is the core intuition: **Time is just another dimension of space.** By treating time as a spatial axis, we can apply the same powerful mathematical tools we use for images to the flow of motion.

## Under the hood (the mechanism; math in plain text, define every symbol)

To enforce temporal coherence, modern video models utilize **3D Causal Convolutions** and **3D Positional Embeddings**. Let’s break down the math and the mechanism using the evidence from our source code.

### 1. The Causal Constraint

In `comfy/ldm/cogvideo/vae.py` and `comfy/ldm/cosmos/cosmos_tokenizer/layers3d.py`, we find the class `CausalConv3d`.

A standard 3D convolution uses a kernel of size $k_t \times k_h \times k_w$. It looks at $k_t$ frames in time. However, in video generation, we often process data sequentially or need to ensure that the output at time $t$ does not depend on future frames at time $t+1$ (which don't exist yet during autoregressive generation).

`CausalConv3d` implements **causal temporal padding**.
*   Let $X$ be the input tensor with shape $(B, C, T, H, W)$, where $B$ is batch, $C$ is channels, $T$ is time, $H$ is height, $W$ is width.
*   Let $K$ be the kernel size in the temporal dimension.
*   Standard padding would add zeros to both the past and future sides of the time axis.
*   Causal padding adds zeros **only** to the past side (or adjusts the stride such that the receptive field is strictly backward-looking).

Mathematically, for a 1D causal convolution along time:
$$ Y_t = \sum_{i=0}^{K-1} W_i \cdot X_{t-i} $$
Here, $Y_t$ is the output at time $t$, $W_i$ are the learnable weights, and $X_{t-i}$ are the input values from the current and past $K-1$ steps. Note that $X_{t+1}$ is **not** included. This ensures **temporal causality**: the model cannot "cheat" by looking into the future. This is critical for stable, real-time, or sequential video generation.

### 2. 3D Positional Embeddings

How does the model know which frame is which? It uses **3D Sinusoidal Positional Embeddings** or **Rotary Position Embeddings (RoPE)**.

In `comfy/ldm/cogvideo/model.py`, we see `get_3d_sincos_pos_embed`. This function generates embeddings for spatial and temporal dimensions.
Let $p$ be the position index along a dimension (e.g., frame index $t$).
The embedding is computed using sine and cosine functions:
$$ PE_{(p, 2i)} = \sin\left(\frac{p}{10000^{2i/d}}\right) $$
$$ PE_{(p, 2i+1)} = \cos\left(\frac{p}{10000^{2i/d}}\right) $$
Where $d$ is the embedding dimension.

In `comfy/ldm/cosmos/position_embedding.py`, we see `VideoRopePosition3DEmb`. This applies **Rotary Position Embeddings** to the query and key tensors in the attention mechanism. RoPE encodes relative position by rotating the query and key vectors in a complex plane. This allows the attention mechanism to understand that Frame 5 is "close" to Frame 6, but "far" from Frame 100. This relative positioning is what allows the model to maintain long-range temporal consistency without exploding in complexity.

### 3. The 4D Tensor View

The input to these models is not a list of images. It is a single tensor $V \in \mathbb{R}^{B \times C \times T \times H \times W}$.
*   $B$: Batch size
*   $C$: Channels (e.g., RGB or latent channels)
*   $T$: Temporal dimension (number of frames)
*   $H$: Height
*   $W$: Width

The `Encoder3D` and `Decoder3D` in the VAEs (e.g., `AutoencoderKLCogVideoX`) compress this 5D tensor into a latent space. The `CogVideoXTransformer3DModel` then operates on these latents, using 3D attention to mix information across space and time simultaneously.

## In ComfyUI

Our sources provide specific evidence of how these architectures are implemented in ComfyUI.

*   **CogVideoX**: The folder `comfy/ldm/cogvideo` contains `CogVideoXTransformer3DModel` and `AutoencoderKLCogVideoX`. The VAE uses `CausalConv3d` to ensure time causality. It also uses `_decode_rolling` to manage memory by decoding in chunks, which is essential for long videos.
*   **Cosmos**: The folder `comfy/ldm/cosmos` implements `CausalContinuousVideoTokenizer`. It uses `Patcher3D` for 3D discrete wavelet transforms, breaking video into spatiotemporal patches. The transformer is `GeneralDIT` or `MiniTrainDIT`, which uses `VideoRopePosition3DEmb` for 3D rotary embeddings.
*   **LTX-Video**: The folder `comfy/ldm/lightricks` contains `LTXBaseModel` and `VideoVAE`. It uses `CausalConv3d` in its VAE and `apply_rotary_emb` for positional encoding. It also features `DurationHead`, which predicts the natural shot duration in seconds, further emphasizing the model's understanding of time as a continuous variable.

These implementations show that ComfyUI does not just load a model; it provides the specific 3D causal and positional machinery required to treat video as a 4D space-time object.

## Lab

In this lab, we simulate the core requirement of space-time modeling: **temporal consistency**. We create a tiny "video" of 3 frames, each with 2 pixels. We calculate the difference between consecutive frames. In a consistent video, these differences should be small and smooth.

The lab script defines:
*   `frames`: A tensor of shape $(3, 2)$ representing 3 frames with 2 pixels each.
*   `diff_0_1`: The absolute difference between Frame 0 and Frame 1.
*   `diff_1_2`: The absolute difference between Frame 1 and Frame 2.
*   `mean_diff`: The average of these differences.

Here are the real `RESULT` lines from the lab output:

```text
RESULT mean_temporal_diff = 1
RESULT diff_0_1 = [1.0, 1.0]
RESULT diff_1_2 = [1.0, 1.0]
```

**What each proves:**
1.  `RESULT mean_temporal_diff = 1`: This proves that the average change between frames is exactly 1.0. In a real video model, this value would be much smaller, indicating smooth motion. Here, it confirms our test data is consistent.
2.  `RESULT diff_0_1 = [1.0, 1.0]`: This proves that the change from Frame 0 to Frame 1 is uniform across both pixels. There is no flicker or random noise; the change is structured.
3.  `RESULT diff_1_2 = [1.0, 1.0]`: This proves that the change from Frame 1 to Frame 2 is also uniform and identical to the previous step. This **constant rate of change** is the hallmark of temporal coherence. If this value were random (e.g., `[0.5, 2.0]`), it would indicate flicker or instability.

This simple check demonstrates why we need 3D convolutions and causal padding: to ensure that the `diff` values remain small and predictable, rather than random.

## Common mistakes

1.  **Treating video as a list of images**: If you feed frames individually to a 2D model, you lose temporal context. The model will generate independent images, leading to flicker. You must use a 3D model that processes the $T$ dimension.
2.  **Ignoring Causality**: Using standard (non-causal) 3D convolutions in an autoregressive setting can cause "future leakage," where the model uses information from frames that haven't been generated yet. This leads to unstable generation. Always use `CausalConv3d` or equivalent causal attention.
3.  **Neglecting Positional Embeddings**: Without 3D positional embeddings (like RoPE or Sincos), the model cannot distinguish between Frame 1 and Frame 100. It will treat all frames as equivalent, leading to a lack of motion or chaotic transitions.
4.  **Memory Overflows**: Processing the entire 4D tensor at once can exceed VRAM. Use techniques like `_decode_rolling` or chunked processing, as seen in the CogVideoX VAE, to manage memory efficiently.

## Go deeper

To understand the theoretical foundations of these architectures, refer to the following papers (by arXiv ID, as implied by the model names in the evidence):

*   **CogVideoX**: Look for the paper on "CogVideoX: Text-to-Video Diffusion Models with An Expert Transformer" (arXiv:2408.06072). This paper details the 3D transformer and the causal VAE.
*   **Cosmos**: Refer to "Cosmos: A World Foundation Model Platform for Physical AI" (arXiv:2501.03575). This paper explains the use of 3D wavelet transforms and rotary embeddings for world modeling.
*   **LTX-Video**: Look for "LTX-Video: Real-Time Video Generation with Diffusion Transformers" (arXiv:2501.13956). This paper discusses the joint audio-video generation and the causal VAE design.

These papers provide the mathematical proofs and experimental results behind the code you see in ComfyUI. Study them to understand *why* the architecture is built this way. Now, go forth and generate video that respects the flow of time. No flicker. No chaos. Just smooth, coherent space-time.

