# CU-218 - Seeds, batches and variations in video

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the reel room, folks. I’m Reel Rascal, and today we are tackling the ghost in the machine: why does my video flicker when I lock the seed? You’ve mastered the basics in CU-105, and you’ve seen how conditioning works in CU-209. Now, we dive into the mechanics of **temporal consistency**.

In image generation, a seed is a magic wand. You set it, you get the same picture. In video, it’s more like a camera on a shaky tripod. The seed locks the *initial state* of the noise, but video latents exist across time. If you don’t understand how that noise propagates through the temporal dimension, your "consistent" video will still have micro-jitters, flickering textures, or drifting objects. This lesson explains why a single seed doesn’t guarantee a static video, and how the batch structure of your latents dictates the variation you see.

## The intuition

Think of the latent space as a 3D block of data: Batch, Channels, Height, Width. For video, we add a Time dimension. When you generate a video, you aren’t generating one image; you are generating a sequence of frames that must cohere.

The seed initializes the random number generator (RNG). This RNG produces a stream of pseudo-random numbers. In a standard image, you draw a block of numbers to fill the latent. In a video, you draw a larger block that spans time.

Here is the key intuition: **The seed locks the *source* of the noise, not the *result* of the temporal processing.** Even if the initial noise is identical, the diffusion process treats each frame in the sequence as part of a continuous flow. If the model’s attention mechanisms or temporal layers are not perfectly deterministic in their floating-point operations, or if the noise itself is sampled independently per frame in the latent space, you will see variation.

More importantly, in a batch, each sample is independent. But within a single video sample, the frames are linked. The "flicker" you fight is often the result of the noise field having high-frequency variations across the time axis that the model struggles to smooth out perfectly.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s look at the data structure. In our lab, we define a latent tensor with shape `(batch_size, channels, height, width)`. For video, this would typically be `(batch_size, channels, time, height, width)`.

The noise is generated using a standard normal distribution. Let’s define the variables:
*   `batch_size`: The number of independent video samples generated in one pass.
*   `channels`: The number of feature channels in the latent space (e.g., 16 for many VAEs).
*   `height`, `width`: The spatial dimensions of the latent.
*   `time`: The number of frames in the video sequence.

The noise tensor `noise` is created by sampling from a distribution where the mean is 0 and the standard deviation is 1. We can denote the value at a specific position as `noise[b, c, t, h, w]`.

When we lock the seed, we are fixing the sequence of random numbers that fill this tensor. However, note that `noise[b, c, t, h, w]` for `t=0` is different from `noise[b, c, t+1, h, w]` for `t=1`. They are different samples from the same distribution.

The "variation" across frames is inherent to the noise field. If you compare `first_frame` (at `t=0`) and `second_frame` (at `t=1`), they are statistically independent draws from the noise distribution. This means their pixel values (or latent values) will differ. The diffusion model’s job is to denoise these frames while enforcing temporal consistency. If the model fails to fully correlate the noise across time, the residual noise differences manifest as flicker.

In our lab, we verify this by checking that consecutive frames in a random batch are different. This is expected. The seed ensures that if you run the script again, `first_frame` will have the *exact same values* as before, and `second_frame` will have the *exact same values* as before. But `first_frame` will still be different from `second_frame`.

## In ComfyUI

In ComfyUI, the seed is typically set via a `KSampler` node or a `BasicScheduler` node. The seed value is passed to the underlying PyTorch RNG.

For video models like LTXV or SeedVR2, the latent structure is handled by specific nodes. The evidence mentions `nodes_lt_keyframes_test.py` which validates logic for appending and managing keyframes in LTXV video latents. This suggests that keyframes are used to anchor the temporal consistency. If you use keyframes, you are explicitly controlling the noise at specific time steps, which reduces variation.

The `test_seedvr2_temporal_chunk.py` file tests automatic temporal chunking based on VRAM availability. This is crucial. If your video is too long for VRAM, ComfyUI might chunk the temporal dimension. If the chunks are not handled with overlapping context or consistent noise seeding across chunks, you will see seams or flicker at the chunk boundaries.

The `comfy/ldm/triposplat` module, while focused on 3D Gaussian Splatting, uses `halton_sequence` and `hammersley_sequence` for low-discrepancy sampling. While not directly used for standard video diffusion, this highlights the importance of structured sampling in maintaining consistency. For video, we rely on the standard normal distribution, but the principle of controlled randomness applies.

## Lab

The lab script generates a batch of random noise and compares the first two frames of the first sample. It proves that even with a fixed seed, consecutive frames in the latent space are different.

Here are the results from the lab:

```
RESULT batch_size = 4
RESULT first_frame_mean = 0.0859302
RESULT second_frame_mean = 0.0497632
```

1.  `RESULT batch_size = 4`: This confirms we are generating 4 independent samples. Each sample has its own unique noise realization, even though they share the same seed initialization logic.
2.  `RESULT first_frame_mean = 0.0859302`: This is the mean value of the latent channels for the first frame (`t=0`) of the first sample. It is close to 0, as expected for a standard normal distribution.
3.  `RESULT second_frame_mean = 0.0497632`: This is the mean value for the second frame (`t=1`). It is different from the first frame’s mean. This proves that the noise is not constant across time. The variation between `0.0859302` and `0.0497632` is the raw material for temporal flicker if not properly denoised.

The fact that the output is identical when run twice (with the same seed) proves that the seed *does* lock the noise state. But the difference between the two frames proves that the temporal dimension introduces natural variation.

## Common mistakes

1.  **Assuming a seed locks the video:** A seed locks the *noise*, not the *video*. If your model has stochastic components (like dropout or attention randomness), the video can still vary. Always check if your model uses deterministic inference.
2.  **Ignoring temporal chunking:** If you are generating long videos, ensure that your temporal chunking strategy maintains noise consistency across chunks. Look for nodes that handle "carry" or "overlap" in temporal processing.
3.  **Using different seeds for keyframes:** If you use keyframes to anchor your video, ensure that the keyframes themselves are generated with consistent seeds or are fixed. If the keyframes flicker, the whole video will flicker.
4.  **Not checking VRAM constraints:** As seen in `test_seedvr2_temporal_chunk.py`, VRAM limits can force chunking. If your VRAM is low, the model might process frames in smaller batches, which can introduce inconsistencies if not handled correctly.

## Go deeper

The evidence does not provide specific arXiv IDs for the papers related to video diffusion seeds or temporal consistency. However, the mechanisms described here are foundational to diffusion models. For a deeper dive, look into papers on "temporal consistency in video diffusion" and "stochastic sampling in latent diffusion models." The `comfy/ldm/triposplat` module’s use of Halton and Hammersley sequences is a good starting point for understanding low-discrepancy sampling, which can be applied to improve consistency in other contexts.

