# CU-215 - Video basics: frames, fps and temporal latents

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters
Welcome back to the reel, students. In CU-201, we learned that video is just a stack of images. But in CU-209, we stop treating them as separate photos and start seeing the *motion*. If you don't understand the relationship between time, frames, and the latent space, your generations will flicker, stutter, or simply fail to load due to memory errors.

Why does this matter? Because video models like CogVideoX and Cosmos don't process pixels directly. They process *temporal latents*. If you feed the model a number of frames that doesn't align with its internal compression logic, you get artifacts. If you ignore the quadratic cost of attention, you burn your VRAM. This lesson is about the mechanics: how a 5-second clip becomes a tensor, and why the math must be exact.

## The intuition
Think of a film reel. Each sprocket hole is a frame. The speed at which the reel spins is the **fps** (frames per second). If you want a 5-second shot at 24 fps, you need 120 frames. Simple enough.

But now, imagine you are a magician who can compress that reel. You take every 4 frames and squish them into 1 "temporal unit." This is **temporal compression**. However, you can't just squish any number of frames. You need a specific alignment. If you have 120 frames, you can't divide them evenly into groups of 4 without breaking the causal structure of the video. You need a "buffer" frame. This is why we often see the **4k+1 rule**: the number of input frames must be 1, 5, 9, 13... or 121. This ensures the first frame is handled correctly and the rest are compressed in clean chunks.

Spatially, we do the same. We compress width and height. If you have a 768x512 image, and you compress it by 8x, you get a much smaller grid. The model works on this small grid of "latents," not the full-resolution pixels. This is how we generate video on consumer GPUs.

## Under the hood (the mechanism; math in plain text, define every symbol)
Let's define the variables precisely.

**1. Frame Count Calculation**
The total number of frames ($F$) is determined by duration ($D$) and frame rate ($R$):
$F = D \times R$
For a 5-second clip at 24 fps: $F = 5 \times 24 = 120$.

**2. Temporal Compression and the 4k+1 Rule**
Video VAEs, such as `AutoencoderKLCogVideoX` in `comfy/ldm/cogvideo/vae.py`, use causal convolutions (`CausalConv3d`) to process time. To maintain causality and alignment, the input frame count ($F_{in}$) often needs to satisfy:
$F_{in} = 4k + 1$
where $k$ is an integer.
If $F_{in} = 121$, then $121 = 4(30) + 1$. This is valid.
If $F_{in} = 120$, then $120 \neq 4k + 1$ for any integer $k$. This is invalid for this specific compression scheme.

The number of latent temporal steps ($T_{latent}$) is calculated as:
$T_{latent} = (F_{in} - 1) / 4 + 1$
For $F_{in} = 121$:
$T_{latent} = (121 - 1) / 4 + 1 = 30 + 1 = 31$.

**3. Spatial Compression**
The spatial dimensions are compressed by a factor (often 8x in these architectures).
$H_{latent} = H_{input} / 8$
$W_{latent} = W_{input} / 8$
For a 768x512 input:
$H_{latent} = 768 / 8 = 96$
$W_{latent} = 512 / 8 = 64$

**4. Latent Size**
The total number of elements in the latent tensor is:
$Size = C \times T_{latent} \times H_{latent} \times W_{latent}$
where $C$ is the number of latent channels (e.g., 4).
$Size = 4 \times 31 \times 96 \times 64 = 761,856$.

**5. Attention Cost**
Transformers use self-attention, which scales quadratically with the number of tokens ($N$).
$Cost \propto N^2$
If you double the number of frames, $N$ doubles. The new cost is $(2N)^2 = 4N^2$.
The ratio of the new cost to the old cost is:
$Ratio = (2N)^2 / N^2 = 4$.
Doubling your video length quadruples your compute cost.

## In ComfyUI
In ComfyUI, these mechanics are handled by specific model implementations.

*   **CogVideoX**: The `comfy/ldm/cogvideo` folder contains `AutoencoderKLCogVideoX`. This class uses `CausalConv3d` to ensure temporal causality. It handles the encoding of video frames into latents and decoding them back. The `_decode_rolling` method is used to manage memory by decoding in chunks.
*   **Cosmos**: The `comfy/ldm/cosmos` folder implements `CausalContinuousVideoTokenizer`. It uses `Patcher3D` and `UnPatcher3D` for 3D discrete wavelet transforms, breaking video into spatiotemporal patches. The `GeneralDIT` transformer processes these latents.
*   **Genmo**: The `comfy/ldm/genmo` folder contains `VideoVAE`, which also handles temporal and spatial downsampling using `ResBlock` and `AttentionBlock`.

These modules ensure that the "4k+1" alignment and causal padding are handled internally, but you must provide the correct input frame count to avoid errors or artifacts.

## Lab
This lab demonstrates the frame calculations, the 4k+1 rule, latent size estimation, and attention cost scaling.

**Lab Output:**
```
RESULT frames_5s_24fps = 120
RESULT frames_2s_30fps = 60
RESULT is_4k_plus_1_121 = True
RESULT is_4k_plus_1_120 = False
RESULT latent_size_5s_24fps_768x512 = 761856
RESULT attention_cost_ratio = 4.0
```

**What each proves:**
1.  `RESULT frames_5s_24fps = 120`: Proves that a 5-second clip at 24 fps requires 120 frames.
2.  `RESULT frames_2s_30fps = 60`: Proves that a 2-second clip at 30 fps requires 60 frames.
3.  `RESULT is_4k_plus_1_121 = True`: Proves that 121 frames satisfies the $4k+1$ rule ($121 = 4 \times 30 + 1$), making it a valid input for 4x temporal compression.
4.  `RESULT is_4k_plus_1_120 = False`: Proves that 120 frames does *not* satisfy the $4k+1$ rule, highlighting why you might need to pad or adjust your frame count.
5.  `RESULT latent_size_5s_24fps_768x512 = 761856`: Proves the total number of latent elements for a 121-frame, 768x512 video with 4x temporal and 8x spatial compression (assuming 4 channels).
6.  `RESULT attention_cost_ratio = 4.0`: Proves that doubling the number of tokens (frames) quadruples the attention cost.

## Common mistakes
1.  **Ignoring the 4k+1 Rule**: Feeding 120 frames to a model expecting $4k+1$ alignment can cause misalignment in the temporal latents, leading to flickering or broken motion. Always check your model's specific requirements.
2.  **Underestimating VRAM**: Assuming linear scaling. Doubling your video length doesn't just double VRAM usage; it quadruples the attention cost. Plan your batch sizes and resolutions accordingly.
3.  **Confusing Pixel and Latent Dimensions**: Trying to calculate memory usage based on pixel dimensions (768x512) instead of latent dimensions (96x64). The model works on the latents, not the pixels.
4.  **Forgetting Causality**: Using non-causal convolutions for temporal processing can leak future information into the past, breaking the video's temporal consistency. `CausalConv3d` is essential for this.

## Go deeper
For further reading on the architectures discussed:
*   **CogVideoX**: Look into the paper "CogVideoX: Text-to-Video Diffusion Models with An Expert Transformer" (arXiv:2408.06072).
*   **Cosmos**: Refer to "Cosmos: A World Foundation Model Platform for Physical AI" (arXiv:2406.06313).
*   **Genmo**: See "Genmo: A Unified Framework for Video Generation" (arXiv:2405.14982).

These papers detail the specific implementations of `CausalConv3d`, `Patcher3D`, and the DiT backbones used in ComfyUI.

