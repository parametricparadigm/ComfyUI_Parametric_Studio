# CU-513 - History 13: Seeing in 3D: NeRF, Gaussian splats and structured latents

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the compressed world. In previous lectures, we treated the latent space as a flat, 2D manifold where pixels are just coordinates. But reality is not flat; it has depth, volume, and light that changes as you move. To generate 3D content, we must move beyond simple pixel prediction and into the realm of volumetric representation.

This lesson explores the two dominant paradigms for 3D generation: **Neural Radiance Fields (NeRF)** and **3D Gaussian Splatting**. We will examine how modern systems like `TripoSplat` and `ChromaRadiance` bridge the gap between 2D diffusion models and 3D geometry. The core tension here is computational: NeRFs offer continuous, high-fidelity representations but are slow to render; Gaussian Splatting offers explicit, real-time rendering but requires careful management of explicit primitives. Understanding this trade-off is essential for architecting efficient 3D-aware diffusion pipelines.

## The intuition

Imagine you are standing in a foggy forest.

**NeRF** is like describing the fog with a mathematical function. You don’t store the fog; you store the *rules* for how dense and colored the fog is at any point $(x,y,z)$ and viewing direction $(\theta, \phi)$. To see a pixel, you cast a ray into the forest and sample this function thousands of times along the ray. It is precise, continuous, and differentiable, but asking the function for every pixel in a high-resolution image is computationally expensive. It is an *implicit* representation.

**Gaussian Splatting** is like the forest being made of millions of tiny, semi-transparent, colored balloons (Gaussians). Each balloon has a position, a size (scale), an orientation (rotation), and a color. To render an image, you project these balloons onto the 2D screen and blend them together. This is an *explicit* representation. Because you are just moving and blending pre-computed shapes, it is incredibly fast—capable of real-time rendering.

In ComfyUI, we see this evolution in the `comfy/ldm/triposplat` and `comfy/ldm/chroma_radiance` modules. `ChromaRadiance` integrates NeRF-style positional embeddings into a flow-matching transformer, allowing the model to "think" in 3D space. `TripoSplat` goes further, using a diffusion model to generate latents that are then decoded into explicit Gaussian parameters, enabling the fast, splat-based rendering we desire.

## Under the hood (the mechanism; math in plain text, define every symbol)

The fundamental operation in both methods is **volume rendering** or **splatting**, which composites contributions from different depths.

For NeRF, we use front-to-back compositing. For a ray passing through $N$ slices, the final color $C$ is:

$$ C = \sum_{i=1}^{N} \alpha_i T_i c_i $$

Where:
*   $\alpha_i$ is the opacity (density) at slice $i$.
*   $c_i$ is the color (radiance) at slice $i$.
*   $T_i$ is the transmittance, representing the probability that light reaches slice $i$ without being absorbed by previous slices. It is defined recursively:
    $$ T_1 = 1 $$
    $$ T_i = T_{i-1} (1 - \alpha_{i-1}) $$

In `TripoSplat`, the decoder outputs explicit Gaussian parameters. A Gaussian is defined by:
*   $\mathbf{x}$: Position (xyz).
*   $\mathbf{s}$: Scale (anisotropic covariance).
*   $\mathbf{q}$: Rotation (quaternion).
*   $\mathbf{c}$: Color (RGB).
*   $\alpha$: Opacity.

The `GaussianModel` class in `comfy/ldm/triposplat/gaussian.py` stores these. The rendering process projects these 3D Gaussians to 2D screen space. The `render_splat` function in `preview.py` handles this projection, using parameters like `yaw` and `pitch` to define the camera view. The key advantage is that once the Gaussians are optimized, rendering is a simple rasterization step, avoiding the iterative sampling of NeRF.

## In ComfyUI

Our sources provide specific evidence for the following implementations:

1.  **`comfy/ldm/triposplat`**: This module contains the core implementation for the TripoSplat model. It uses a diffusion-based transformer (`LatentSeqMMFlowModel`) to generate latents, which are then decoded into explicit 3D Gaussian parameters. Key classes include `GaussianModel` for storing parameters and `OctreeGaussianDecoder` for hierarchical decoding. The `preview.py` file includes `render_splat`, which renders these Gaussians to an image using a view matrix constructed from `yaw` and `pitch`.
2.  **`comfy/ldm/chroma_radiance`**: This module implements the `ChromaRadiance` model, a variant of the Chroma transformer designed for flow matching on sequences. It integrates NeRF capabilities via `NerfEmbedder` and `NerfGLUBlock`. The `forward_nerf` method executes the forward pass for NeRF-related computations, while `forward_tiled_nerf` offers a memory-optimized version by processing inputs in chunks.
3.  **`comfy_extras/nodes_gaussian_splat.py`**: This file defines `RenderSplat` and `TransformSplat` nodes, allowing users to manipulate and visualize Gaussian splats within the ComfyUI graph. It also includes serialization functions like `_gaussian_ply_bytes` for exporting the data.

## Lab

The lab simulates the core volume rendering equation used in NeRF and adapted for splatting. We define three slices with fixed opacities ($\alpha = 0.5$) and distinct colors (Red, Green, Blue). We calculate the transmittance $T$ and the final composited color $C$.

Here are the real `RESULT` lines from the lab output:

```text
RESULT final_color = 0.5 0.25 0.125
RESULT transmittance = 1 0.5 0.25
```

**What each proves:**
1.  `RESULT final_color = 0.5 0.25 0.125`: This proves the correctness of the front-to-back compositing formula. The red component is $0.5$ because the first slice has $\alpha=0.5$ and $T=1.0$ ($0.5 \times 1.0 \times 1.0 = 0.5$). The green component is $0.25$ because the second slice has $\alpha=0.5$ and $T=0.5$ ($0.5 \times 0.5 \times 1.0 = 0.25$). The blue component is $0.125$ because the third slice has $\alpha=0.5$ and $T=0.25$ ($0.5 \times 0.25 \times 1.0 = 0.125$).
2.  `RESULT transmittance = 1 0.5 0.25`: This proves the recursive calculation of transmittance. $T_1 = 1$. $T_2 = T_1 (1 - \alpha_1) = 1 \times (1 - 0.5) = 0.5$. $T_3 = T_2 (1 - \alpha_2) = 0.5 \times (1 - 0.5) = 0.25$. This decay in transmittance is why deeper layers contribute less to the final image, a fundamental property of volumetric rendering.

## Common mistakes

1.  **Confusing Implicit and Explicit**: Assuming that because a model uses a transformer, it is "implicit." In `TripoSplat`, the transformer generates *explicit* Gaussian parameters. The "implicit" part is the diffusion process in latent space, but the final 3D representation is explicit.
2.  **Ignoring Memory in NeRF**: Using `forward_nerf` without `forward_tiled_nerf` on large scenes can exhaust VRAM. The tiled version is crucial for memory optimization, as noted in the `chroma_radiance` documentation.
3.  **Misinterpreting Transmittance**: Forgetting that transmittance is cumulative. A high opacity in the foreground drastically reduces the contribution of background layers, which is essential for correct depth perception in rendered images.

## Go deeper

To understand the theoretical foundations and the specific algorithms implemented in ComfyUI, refer to these papers:

*   **arXiv:2003.08934**: *NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis*. This paper introduces the 5D coordinate function and volume rendering technique that `ChromaRadiance` builds upon.
*   **arXiv:2308.04079**: *3D Gaussian Splatting for Real-Time Radiance Field Rendering*. This paper details the explicit Gaussian representation, anisotropic covariance optimization, and the fast visibility-aware rendering algorithm used in `TripoSplat`.

