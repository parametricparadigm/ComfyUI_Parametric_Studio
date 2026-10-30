# CU-509 - History 9: Transformers replace U-Nets: DiT and rectified flow

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Ladies and gentlemen, welcome to the lecture hall. Put away your U-Net diagrams. They are charming, but they are relics. For years, we believed that the U-Net architecture was the only way to structure the denoising process. We believed that spatial hierarchy—downsampling, upsampling, skip connections—was mandatory. We were wrong.

In this lesson, we examine the seismic shift in generative AI: the replacement of the U-Net backbone with the Diffusion Transformer (DiT). This is not merely an architectural swap; it is a fundamental change in how we view the geometry of generation. We are moving from curved, complex trajectories in latent space to straight, efficient lines. This shift enables scalability that U-Nets simply cannot match, allowing models to grow in depth and width without collapsing under their own complexity. As Madame Attention, I will show you that when you let the transformer attend to every patch, you unlock a new regime of performance.

## The intuition

Imagine you are transporting a crowd from Point A (pure noise) to Point B (a crisp image). In standard diffusion, the crowd takes a winding, chaotic path. They swirl, they loop, they hesitate. To get them from A to B, you need many small steps, carefully guided by a complex vector field.

Rectified Flow changes the story. It asks: *What if the path were a straight line?*

If the path is a straight line, the velocity is constant. You don’t need to calculate a new direction at every step; you just keep moving forward. This is the core intuition of rectified flow: learning an Ordinary Differential Equation (ODE) that transports points from the noise distribution $\pi_0$ to the data distribution $\pi_1$ along the straightest possible paths.

Why do we care about straight lines? Because they are the shortest distance between two points. More importantly, straight paths can be simulated exactly without time discretization errors. This means we can take large steps during inference. In the lab, we will see that a single Euler step can suffice for high-quality results, a feat impossible with the curved trajectories of standard diffusion. This efficiency is what makes DiT architectures so powerful: they are not just better at attending to context; they are traveling a more efficient route through latent space.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us define the geometry. We have two distributions: $\pi_0$ (noise) and $\pi_1$ (data). We draw a point $x_0$ from $\pi_0$ and a point $x_1$ from $\pi_1$.

In rectified flow, we define the path $x_t$ between these points as a linear interpolation:

$x_t = (1 - t) x_0 + t x_1$

where $t$ is the time step, ranging from 0 to 1.

The velocity $v$ along this path is the derivative of $x_t$ with respect to $t$:

$v = \frac{dx_t}{dt} = x_1 - x_0$

Notice something critical: $v$ does not depend on $t$. It is constant. This is the "rectification." The model learns to predict this constant velocity vector.

In a standard diffusion model, the velocity field is highly curved and time-dependent. The model must learn a complex function $v(x_t, t)$ that changes direction as $t$ progresses. In rectified flow, the target is a straight line. The optimization problem is a nonlinear least squares problem that minimizes the deviation from straightness.

The DiT architecture facilitates this by operating on latent patches. Instead of processing the entire image as a single tensor through convolutions, the DiT flattens the latent space into a sequence of tokens (patches). Each token attends to every other token via self-attention. This global receptive field allows the model to learn the complex correlations between distant parts of the image, which is essential for maintaining the straightness of the flow in high-dimensional spaces.

The conditioning (text, class labels) is injected via adaptive layer normalization or cross-attention, allowing the transformer blocks to modulate the flow based on the prompt. The result is a model that scales linearly with the number of parameters, achieving lower FID scores as we increase the Gflops of the forward pass.

## In ComfyUI

In ComfyUI, this architecture is not a single node but a collection of modules that replace the traditional UNet.

For the DiT backbone, look at `comfy/ldm/modules/diffusionmodules/mmdit.py`. The class `MMDiT` is the main entry point for Multi-Modal Diffusion Transformer models (like SD3/Flux). It uses `DismantledBlock`, which is a DiT block with gated adaptive layer norm conditioning. This is where the "who attends to whom" logic is refined; the conditioning signals modulate the attention weights directly.

For other DiT implementations, such as HunYuanDiT, see `comfy/ldm/hydit/models.py`. The class `HunYuanDiT` processes latent inputs through `HunYuanDiTBlock` layers. These blocks use `Attention` and `CrossAttention` mechanisms from `attn_layers.py`, incorporating Rotary Positional Embeddings (RoPE) via `apply_rotary_emb` to maintain spatial awareness.

In the audio domain, `comfy/ldm/ace/ace_step15.py` contains `AceStepDiTModel`, the core diffusion transformer for audio generation. It uses `AceStepAttention` and `RotaryEmbedding` to handle the temporal and spectral dimensions of audio latents.

These modules demonstrate that the DiT is not a monolith but a flexible framework. Whether it is `MMDiT` for images or `AceStepDiTModel` for audio, the core principle remains: transformers replace convolutions, and rectified flow straightens the path.

## Lab

The lab verifies the geometric properties of rectified flow in a 2D space. We define a start point (noise) and an end point (data) and verify that the path between them is a straight line with constant velocity.

The lab output is as follows:

`RESULT start = 0 0`
`RESULT end = 1 1`
`RESULT velocity = 1 1`
`RESULT midpoint = 0.5 0.5`
`RESULT rectified_flow_verified = True`

Let us dissect these results:

1.  `RESULT start = 0 0`: This defines $x_0$, the initial noise state. It is the origin in our 2D latent space.
2.  `RESULT end = 1 1`: This defines $x_1$, the target data state. It is the destination.
3.  `RESULT velocity = 1 1`: This is $v = x_1 - x_0$. The velocity is constant. It does not change with time. This proves the "straight line" property. If the velocity were changing, the path would be curved.
4.  `RESULT midpoint = 0.5 0.5`: At $t=0.5$, the position is exactly halfway between start and end. This confirms the linear interpolation formula $x_t = (1-t)x_0 + tx_1$.
5.  `RESULT rectified_flow_verified = True`: This final assertion confirms that the path equation holds for all tested time steps ($t=0.0, 0.25, 0.5, 0.75, 1.0$). It proves that the flow is rectified: the path is straight, and the velocity is constant.

This simple 2D example encapsulates the entire philosophy of rectified flow. In high-dimensional latent spaces, the DiT learns to approximate this straight-line behavior, enabling efficient sampling with fewer steps.

## Common mistakes

1.  **Confusing DiT with U-Net:** Do not think of DiT as a "faster U-Net." It is a different architectural paradigm. U-Nets rely on local convolutions and skip connections; DiTs rely on global attention and patch tokens. Mixing these concepts leads to confusion about why DiTs scale better.
2.  **Ignoring the conditioning mechanism:** In DiT, conditioning is not just an input; it modulates the attention layers. If you ignore how `DismantledBlock` or `HunYuanDiTBlock` injects conditioning, you will not understand how the model steers the flow.
3.  **Assuming rectified flow is always perfect:** While rectified flow aims for straight paths, real-world data distributions are complex. The model learns an approximation. However, the key advantage is that even approximate straight paths are more efficient to simulate than curved ones.
4.  **Overlooking positional embeddings:** In DiT, spatial information is not inherent in the convolution kernel. It must be explicitly encoded. Look at `get_2d_sincos_pos_embed` or `apply_rotary_emb` in the ComfyUI code. Without these, the transformer would not know which patch is where, and the flow would collapse.

## Go deeper

To fully grasp the machinery, read the foundational papers:

1.  **arXiv:2212.09748**: "Scalable Diffusion Models with Transformers" (Peebles & Xie). This paper introduces DiT and demonstrates that increasing the Gflops of the transformer backbone consistently lowers FID. It is the definitive proof that transformers can replace U-Nets.
2.  **arXiv:2209.03003**: "Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow" (Liu et al.). This paper formalizes rectified flow and shows that straight paths can be simulated with a single Euler step. It is the mathematical backbone of the efficiency gains we discussed.

These papers are not just history; they are the blueprint for the models you run in ComfyUI today. Study them, and you will see that the future of generative AI is not just about bigger models, but about smarter, straighter paths.

