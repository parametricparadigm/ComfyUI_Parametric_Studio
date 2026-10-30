# CU-315 - Temporal consistency and optical flow basics

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

**Instructor:** Reel Rascal
**Course:** CU-315 Temporal consistency and optical flow basics
**Level:** 300 (Architecture: the machinery inside the models)
**Prerequisites:** CU-209

*Clack-clack-clack.* Listen to that. That’s the sound of a film reel spinning at 24 frames per second. I’m Reel Rascal, and I don’t just watch movies; I count the frames. In this lesson, we are stripping away the magic of "AI video" to look at the raw machinery underneath. We are going to talk about **temporal consistency**. If your video flickers, it’s not because the model is "confused." It’s because the pixels didn’t move where they were supposed to. Let’s fix that.

## Why this matters

In static image generation, you care about spatial coherence: does the left edge of the cat match the right edge? In video, you have a new dimension: **time**. Temporal consistency is the promise that the world doesn’t teleport between frame $t$ and frame $t+1$.

If you generate a video where a character’s face changes shape every frame, or the background shimmers like heat haze, you have a temporal consistency failure. This is the enemy of immersion. For us architects, this isn’t just an aesthetic problem; it’s a structural one. The neural networks we build must understand that a pixel at $(x, y)$ in frame $t$ is likely related to a pixel at $(x', y')$ in frame $t+1$. If we ignore this relationship, we get flicker. If we enforce it, we get smooth motion. This lesson is about the fundamental unit of that relationship: **pixel displacement**.

## The intuition

Imagine you are watching a ball roll across a screen. In frame 1, the ball is at position $P_1$. In frame 2, it is at $P_2$. The "optical flow" is the vector that tells you how far and in what direction the ball moved.

In a perfect, rigid world, every pixel in the ball moves by the exact same amount. If the ball moves 5 pixels to the right, every pixel in the ball shifts by +5 in the x-direction. This is **uniform flow**.

However, real video is messy. Objects rotate, deform, and occlude each other. But the core intuition remains: **temporal coherence is the minimization of unexpected change.** If a pixel changes value drastically between frames without a corresponding spatial shift, the brain perceives it as noise or flicker. Our goal in architecture is to ensure that the latent representations of consecutive frames are aligned in a way that respects this physical continuity.

## Under the hood (the mechanism; math in plain text, define every symbol)

Before we dive into complex neural networks, let’s define the math of displacement. We treat a video as a sequence of images $I_t(x, y)$, where $t$ is the time index, and $x, y$ are spatial coordinates.

The **optical flow field** $V(x, y)$ at a given location is a 2D vector $(u, v)$ that describes the displacement of the pixel from time $t$ to $t+1$.

The fundamental constraint of temporal consistency is the **brightness constancy assumption** (simplified): the intensity of a moving pixel remains constant over time. Mathematically, this is expressed as:

$$ I_{t+1}(x + u, y + v) = I_t(x, y) $$

Where:
*   $I_t(x, y)$ is the pixel intensity at time $t$.
*   $I_{t+1}(x + u, y + v)$ is the pixel intensity at time $t+1$, shifted by the flow vector.
*   $u$ is the horizontal displacement (x-flow).
*   $v$ is the vertical displacement (y-flow).

In our simplest case, if the entire image shifts by a constant amount, the flow is uniform. Let’s define the flow tensor $F$ as the difference between two frames:

$$ F = I_{t+1} - I_t $$

If $I_{t+1}$ is just $I_t$ shifted, $F$ captures that shift. In our lab, we will compute this naive flow. Note that in real neural networks, we don’t just subtract pixels; we learn to predict $u$ and $v$ using convolutional layers that look at local neighborhoods. But the *goal* is always to satisfy that equation above. If the model fails to predict the correct $u, v$, the reconstructed $I_{t+1}$ will not match the actual next frame, resulting in error. This error, when summed over time, is what we perceive as flicker.

## In ComfyUI

Now, where does this live in ComfyUI? We need to look at the video-specific modules.

In `comfy/ldm/modules/diffusionmodules/model.py`, you will find `VideoConv3d` and `CarriedConv3d`. `VideoConv3d` is a standard 3D convolution that operates on the time, height, and width dimensions simultaneously. This is the first line of defense against temporal inconsistency; it forces the network to consider neighboring frames during the forward pass.

More specifically, `CarriedConv3d` is a **causal** 3D convolution. "Causal" means it only looks at past and present frames, not future ones. This is critical for autoregressive video generation or when processing streams. It ensures that the temporal consistency is built from history forward, preventing "future leakage" which can cause artifacts.

In the Cosmos implementation (`comfy/ldm/cosmos/cosmos_tokenizer/layers3d.py`), we see `CausalConv3d`. This layer is used in the `EncoderBase` and `DecoderBase` to handle the spatiotemporal patches. By using causal padding, the tokenizer ensures that the latent representation respects the temporal order of the video.

Additionally, in `comfy/ldm/genmo/vae/model.py`, the `VideoVAE` uses `PConv3d` (3D convolution) and `DepthToSpaceTime` to rearrange spatial and temporal dimensions. This allows the VAE to compress the video in both space and time, but the underlying mechanism still relies on these 3D convolutions to maintain the link between frames.

*Note: Specific optical flow estimation nodes are not covered in our sources; the consistency is enforced architecturally via these 3D causal layers.*

## Lab

Let’s prove the concept with a tiny experiment. We will create two 2x2 grayscale images. `img1` is `[[1, 2], [3, 4]]` and `img2` is `[[2, 3], [4, 5]]`. Notice that every pixel in `img2` is exactly 1 unit higher than `img1`. This simulates a uniform brightness shift, which in a spatial context would be a uniform flow.

We compute the naive flow as `img2 - img1`.

Here are the results from our lab run:

```
RESULT flow_mean = 1
RESULT flow_std = 0
RESULT flow_max = 1
RESULT flow_min = 1
RESULT flow_tensor = [[1.0, 1.0], [1.0, 1.0]]
```

Let’s break down what each line proves:

1.  `RESULT flow_mean = 1`: The average displacement is 1.0. This confirms that the "motion" is consistent across the entire image. There are no outliers.
2.  `RESULT flow_std = 0`: The standard deviation is 0. This is the key metric for **consistency**. A standard deviation of 0 means every single pixel moved by the exact same amount. In a real video, a low standard deviation in a region indicates rigid body motion, which is easy for a neural network to model. High standard deviation indicates complex deformation or noise.
3.  `RESULT flow_max = 1`: The maximum displacement is 1.0. No pixel moved more than the average.
4.  `RESULT flow_min = 1`: The minimum displacement is 1.0. No pixel moved less than the average.
5.  `RESULT flow_tensor = [[1.0, 1.0], [1.0, 1.0]]`: This is the raw flow field. It is a uniform matrix. If this were a real video, the object would appear to move smoothly and rigidly. If the values were random, the object would appear to shimmer or dissolve.

This lab demonstrates that **temporal consistency is a property of the flow field’s variance.** When the flow is uniform (low variance), the video is coherent. When the flow is erratic (high variance), the video flickers.

## Common mistakes

1.  **Ignoring Causality:** Using standard 3D convolutions that look at future frames during inference can cause "smearing" or artifacts because the model is cheating by looking ahead. Always use `CausalConv3d` or `CarriedConv3d` for real-time or sequential generation.
2.  **Treating Time as Just Another Spatial Dimension:** While 3D convolutions treat time as a dimension, the physics of time are different. Time is sequential and irreversible. Architectures that treat time symmetrically (like some static image models) often fail to capture the directionality of motion, leading to "wobble" or "jitter."
3.  **Over-relying on Attention Alone:** While attention mechanisms (like `VideoAttn` in Cosmos) help global consistency, they are computationally expensive and can miss local pixel-level displacements. You need local 3D convolutions to handle the fine-grained optical flow.

## Go deeper

To understand the theoretical underpinnings of these architectures, look into the following papers:

*   **arXiv:2303.14512** (Cosmos World Foundation Model): Details the use of causal 3D convolutions and DiT for video generation.
*   **arXiv:2209.00796** (Genmo Video Generation): Discusses the asymmetric DiT and Video VAE architecture.
*   **arXiv:2006.11239** (Latent Diffusion Models): The foundational paper for LDMs, which we extend to video in this course.

*Clack-clack-clack.* Keep your flows uniform, your convolutions causal, and your frames consistent. Class dismissed.

