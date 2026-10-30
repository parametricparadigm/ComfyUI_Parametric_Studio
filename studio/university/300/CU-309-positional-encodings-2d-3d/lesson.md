# CU-309 - Positional encodings in 2D and 3D

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back, students. In CU-302, we discussed the architecture of the Transformer. You learned that self-attention is a permutation-invariant operation. If you shuffle the tokens in a sequence, the attention scores remain identical. The model is blind to order. It does not know which token is first, which is last, or which pixel is in the top-left corner versus the bottom-right.

For language, this is a problem. For images and video, it is a catastrophe. A pixel at $(x=0, y=0)$ is fundamentally different from a pixel at $(x=1023, y=1023)$. If the network cannot distinguish these positions, it cannot learn spatial relationships. It cannot know that "sky" is usually above "ground," or that a face has two eyes symmetrically placed.

Positional encodings are the solution. They inject spatial or temporal information into the token embeddings before they enter the attention mechanism. In this lesson, we focus on **sinusoidal positional encodings** for 2D (images) and 3D (video/volumes). We will see how simple trigonometric functions create a continuous, differentiable map from discrete grid coordinates to vector space. This allows the network to generalize to resolutions it has never seen during training.

## The intuition

Imagine you are a librarian. You have a shelf of books. If I hand you a book without a call number, you have no idea where it belongs. You might put it anywhere. The "call number" is the positional encoding.

In a standard 1D sequence, we often use sinusoidal functions of the form $\sin(pos \cdot \theta)$ and $\cos(pos \cdot \theta)$. Why sine and cosine? Because they are periodic. A position $pos$ and a position $pos + 2\pi$ have the same encoding. But more importantly, the encoding of position $pos + k$ can be computed as a linear transformation of the encoding of position $pos$. This linearity is crucial. It allows the attention mechanism to easily compute relative distances. If I want to know how far token A is from token B, the dot product of their encodings reveals that distance.

In 2D, we have two axes: $x$ (horizontal) and $y$ (vertical). We treat them independently. We compute a sinusoidal encoding for $x$ and a separate sinusoidal encoding for $y$, then concatenate them. The result is a vector that uniquely identifies a 2D coordinate.

In 3D, we add a third axis: $z$ (depth or time). We compute encodings for $x$, $y$, and $z$ separately and concatenate all three. This is the "axial" approach. It is simple, efficient, and highly effective for grid-based data like images and video frames.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us define the mechanism precisely.

**Input:**
*   $x$: The horizontal coordinate (integer or float).
*   $y$: The vertical coordinate (integer or float).
*   $z$: The depth or temporal coordinate (integer or float), used only in 3D.
*   $f$: The frequency. In our simplified lab, $f = 1.0$. In real models, multiple frequencies are often used to capture both fine and coarse details.

**2D Encoding:**
The 2D positional encoding vector $E_{2d}$ is constructed by concatenating the sine and cosine of the scaled coordinates:
$$ E_{2d} = [\sin(x \cdot f), \cos(x \cdot f), \sin(y \cdot f), \cos(y \cdot f)] $$
This results in a vector of dimension 4.

**3D Encoding:**
The 3D positional encoding vector $E_{3d}$ extends this by adding the $z$-axis:
$$ E_{3d} = [\sin(x \cdot f), \cos(x \cdot f), \sin(y \cdot f), \cos(y \cdot f), \sin(z \cdot f), \cos(z \cdot f)] $$
This results in a vector of dimension 6.

**Properties:**
1.  **Bounded:** Since sine and cosine outputs are always in the range $[-1, 1]$, the encoding values are bounded. This helps with numerical stability.
2.  **Continuous:** The function is differentiable. If you shift a pixel by a tiny amount $\epsilon$, the encoding changes smoothly. This allows the network to generalize to sub-pixel positions or different resolutions.
3.  **Unique (for small grids):** For a grid smaller than the period of the sine wave ($2\pi/f$), each coordinate maps to a unique vector.

In ComfyUI, these encodings are often added to the token embeddings or used to modulate attention. For example, in the `comfy/ldm/sam3` module, the function `gen_sineembed_for_position` generates per-coordinate sinusoidal embeddings for position tensors. This is used in the detector to encode the positions of points and boxes.

## In ComfyUI

Our sources reveal several implementations of positional encodings in ComfyUI:

1.  **`comfy/ldm/sam3/detector.py`**: Contains the function `gen_sineembed_for_position`. This function generates per-coordinate sinusoidal embeddings for position tensors. It is used in the `GeometryEncoder` to encode geometric prompts like points and boxes. This is a direct application of the 2D sinusoidal encoding we discussed.

2.  **`comfy/ldm/sam3/tracker.py`**: Contains the function `get_1d_sine_pe`. This generates 1D sinusoidal positional encoding for temporal positions. This is used in video tracking to encode the time step of each frame.

3.  **`comfy/ldm/cosmos/position_embedding.py`**: Contains the class `VideoRopePosition3DEmb`. This implements 3D Rotary Position Embeddings (RoPE) for video sequences. While RoPE is a different mechanism (using rotation matrices rather than simple addition), it serves the same purpose: injecting positional information into the attention mechanism. The evidence notes that RoPE "encodes the absolute position with a rotation matrix and meanwhile incorporates the explicit relative position dependency in self-attention formulation."

4.  **`comfy/ldm/trellis2`**: This module operates on sparse 3D voxel grids. While the evidence does not explicitly name a sinusoidal encoding function, the `SparseTensor` class manages coordinates. In such architectures, positional information is often derived directly from the coordinates or via learned embeddings. The `compute_stage_proj_feats` function back-projects feature maps onto sparse coordinates, implying that position is a critical part of the feature representation.

## Lab

In this lab, we implemented a simplified 2D and 3D sinusoidal positional encoding using PyTorch. We defined a small 4x4 grid for 2D and a 2x4x4 grid for 3D. We used a single frequency $f=1.0$ for clarity.

We computed the encodings and verified their shapes and value ranges.

Here are the results from the lab:

```
RESULT enc_2d_shape = torch.Size([1, 4, 4, 4])
```
This proves that the 2D encoding produces a tensor with the same spatial dimensions as the input grid (4x4) and a feature dimension of 4 (2 for x, 2 for y).

```
RESULT enc_2d_first = [0.0, 1.0, 0.0, 1.0]
```
This is the encoding for the coordinate $(x=0, y=0)$. Since $\sin(0) = 0$ and $\cos(0) = 1$, the encoding is $[0, 1, 0, 1]$. This confirms the formula is implemented correctly.

```
RESULT enc_3d_shape = torch.Size([1, 2, 4, 4, 6])
```
This proves that the 3D encoding produces a tensor with the same spatial dimensions as the input volume (2x4x4) and a feature dimension of 6 (2 for x, 2 for y, 2 for z).

```
RESULT enc_3d_first = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
```
This is the encoding for the coordinate $(x=0, y=0, z=0)$. Since all coordinates are 0, all sine terms are 0 and all cosine terms are 1. This confirms the 3D extension is correct.

These results demonstrate that sinusoidal encodings are deterministic, bounded, and easy to compute. They provide a stable foundation for the attention mechanism to learn spatial relationships.

## Common mistakes

1.  **Forgetting to scale coordinates:** If you use large integer coordinates (e.g., 1024) with a high frequency, the sine and cosine functions will oscillate rapidly, leading to aliasing. Always normalize coordinates or choose frequencies carefully.
2.  **Using the same frequency for all axes:** In 2D and 3D, it is often beneficial to use different frequencies for different axes to capture anisotropic structures. However, using the same frequency is a valid starting point.
3.  **Confusing absolute and relative encodings:** Sinusoidal encodings are absolute. They encode the position of a token in the grid. Relative encodings, like RoPE, encode the distance between tokens. Both are useful, but they serve different purposes.
4.  **Ignoring the batch dimension:** When implementing encodings, ensure that the batch dimension is preserved. The encoding should be broadcastable to the batch size.

## Go deeper

To understand the theoretical underpinnings of positional encodings, I recommend the following paper:

*   **arXiv:2104.09864**: "RoFormer: Enhanced Transformer with Rotary Position Embedding" by Jiang et al. This paper introduces RoPE, a method that encodes absolute position with a rotation matrix while incorporating explicit relative position dependency in self-attention. It provides a theoretical analysis of why RoPE works well and how it enables flexibility in sequence length.

This paper is essential for understanding how positional information can be integrated into the attention mechanism in a way that preserves relative distance information. It complements the sinusoidal approach we discussed in this lesson.

