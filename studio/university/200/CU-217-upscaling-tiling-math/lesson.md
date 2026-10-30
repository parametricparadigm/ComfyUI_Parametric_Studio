# CU-217 - Upscaling and tiling math

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the latent space. In CU-201, we learned that the VAE compresses your image into a dense grid of latent vectors. But what happens when you want to make that image bigger? Or when your GPU’s memory is too small to hold the entire high-resolution latent tensor at once?

This is where the geometry of tiling becomes critical. If you simply slice an image into pieces, process them, and paste them back together, you will see ugly seams. The model has no memory of what happened in the neighboring tile. To fix this, we use **overlap**. But overlap is not just a "nice to have"; it is a strict mathematical requirement to ensure that every pixel in the final image is influenced by enough context to be seamless.

In this lesson, we derive the exact integer arithmetic required to calculate the number of tiles and their offsets. We will ensure that we cover the entire target area without leaving gaps, while minimizing the redundant computation that comes with excessive overlap. This is the difference between a professional workflow and a broken one.

## The intuition

Imagine you are painting a massive mural, but you only have a small canvas (your VRAM limit). You cannot paint the whole mural at once. So, you paint one section, then move your canvas slightly to the right, painting a new section that overlaps the previous one.

Why overlap? Because the edges of your painted section are "uncertain." The brushstrokes near the edge of the canvas are less confident than those in the center. By overlapping, you ensure that the "uncertain" edges of one tile are covered by the "confident" center of the next tile. When you blend them, the result is smooth.

However, if you overlap too much, you waste time painting the same area twice. If you overlap too little, you leave gaps where no paint exists. The math we are about to derive finds the sweet spot: the minimum number of tiles needed to cover the target, given a fixed tile size and a fixed overlap.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us define our variables clearly. We are working in pixel space for the tiling logic, though the same math applies to latent space if you adjust the dimensions by the VAE downscale factor.

*   $W_{target}$: The width of the final image we want to produce.
*   $H_{target}$: The height of the final image we want to produce.
*   $S$: The size of a single tile (square, so $S \times S$).
*   $O$: The overlap in pixels between adjacent tiles.
*   $Step$: The distance we move the tile origin for each subsequent tile.

The step size is determined by the tile size minus the overlap:
$$Step = S - O$$

We need to calculate the number of tiles, $N$, required to cover a dimension of size $D$ (where $D$ is either $W_{target}$ or $H_{target}$).

The first tile starts at coordinate $0$ and covers the range $[0, S]$.
The second tile starts at coordinate $Step$ and covers the range $[Step, Step + S]$.
The $i$-th tile (0-indexed) starts at coordinate $i \times Step$.

To cover the entire dimension $D$, the end of the last tile must be at least $D$. The end of the $i$-th tile is $i \times Step + S$.
We need the smallest integer $N$ such that:
$$(N - 1) \times Step + S \ge D$$

Rearranging for $N$:
$$(N - 1) \times Step \ge D - S$$
$$N - 1 \ge \frac{D - S}{Step}$$
$$N \ge \frac{D - S}{Step} + 1$$

Since $N$ must be an integer, we take the ceiling:
$$N = \left\lceil \frac{D - S}{Step} \right\rceil + 1$$

**Special Case:** If $D \le S$, we only need one tile. The formula above would yield $\lceil \text{negative or zero} \rceil + 1$, which might result in 1 or 2 depending on implementation details, so we explicitly check if $D \le S$ and return 1.

Once we have $N$, the starting coordinates for each tile $i$ (where $i$ ranges from $0$ to $N-1$) are:
$$Start_i = i \times Step$$

The ending coordinate for each tile is:
$$End_i = \min(Start_i + S, D)$$

The $\min$ function ensures that the last tile does not extend beyond the target image boundary. This is crucial for memory allocation and blending weights.

## In ComfyUI

The evidence provided references `tiled_vae` in `comfy/ldm/seedvr/vae.py`, which performs spatial tiling for VAE encoding/decoding to manage memory, blending tiles with overlap. This confirms that the mechanism described above is actively used in ComfyUI for high-resolution video and image processing.

However, the specific node names or UI parameters for configuring the tile size and overlap in a standard ComfyUI workflow are **not covered in our sources**. The evidence points to the internal implementation within the `seedvr` module, but does not list a specific "Tile Upscale" node in the general node registry. You should look for nodes that explicitly mention "tiled" or "chunked" processing in their descriptions, or check the documentation for the specific model you are using (e.g., SeedVR2) to see if it exposes these parameters.

## Lab

In this lab, we simulate the tiling calculation for a 1024x1024 target image using 512x512 tiles with a 64-pixel overlap. We verify the scaling factor, the number of tiles, and the exact coordinates of each tile.

The lab output confirms our math:

```text
RESULT scale_x = 2
```
This proves that the target size is exactly double the original size, validating the 2x upscaling scenario.

```text
RESULT n_tiles_x = 3
```
This proves that we need 3 tiles to cover the width. Let's verify: $Step = 512 - 64 = 448$. $N = \lceil (1024 - 512) / 448 \rceil + 1 = \lceil 512 / 448 \rceil + 1 = \lceil 1.14 \rceil + 1 = 2 + 1 = 3$. Correct.

```text
RESULT tile_coords_x = [[0, 512], [448, 960], [896, 1024]]
```
This proves the exact offsets.
- Tile 0: Starts at 0, ends at 512.
- Tile 1: Starts at 448 ($1 \times 448$), ends at 960 ($448 + 512$).
- Tile 2: Starts at 896 ($2 \times 448$), ends at 1024 ($\min(896 + 512, 1024)$).
Notice that the last tile is clipped to 1024, not 1408. This prevents out-of-bounds errors.

```text
RESULT grid_sum = 9
```
This proves that we have a 3x3 grid of valid tiles, totaling 9 tiles. This is the total number of forward passes through the VAE or diffusion model required for this specific configuration.

## Common mistakes

1.  **Forgetting the Ceiling:** Using integer division instead of ceiling division will result in gaps. If $(D - S)$ is not perfectly divisible by $Step$, you will miss the last sliver of the image. Always use `math.ceil`.
2.  **Ignoring the Clip:** If you do not clamp the end coordinate to $D$, your last tile will be larger than $S$. This can cause memory errors or blending artifacts because the blending weights will be calculated for a larger area than expected.
3.  **Overlap Too Small:** If $O$ is too small, the "confident" center of one tile may not overlap with the "uncertain" edge of the next. You will see visible seams. A good rule of thumb is $O \ge 16$ or $O \ge 32$ pixels, depending on the model's receptive field.
4.  **Non-Integer Steps:** Ensure that $Step$ is an integer. If $S$ and $O$ are integers, $Step$ will be. But if you are working in latent space, remember that the VAE downscale factor (usually 8) must divide the tile size evenly to avoid misalignment between pixel and latent grids.

## Go deeper

The evidence does not provide specific arXiv IDs for the tiling math itself, as this is a standard computer graphics and image processing technique. However, the `seedvr` module is based on the **SeedVR2** model. You should look for the SeedVR2 paper for details on how the causal 3D VAE and the tiling strategy interact with the temporal dimension. The tiling math here is 2D spatial, but in video, you must also consider temporal tiling and the `CausalMemoryCache` mentioned in the evidence to ensure continuity across frames.

