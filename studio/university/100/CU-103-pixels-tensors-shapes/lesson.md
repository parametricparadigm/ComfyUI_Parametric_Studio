# CU-103 - Pixels, tensors and shapes

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome, students. I am Bit Bandit, and I live in the last few bits of your floating-point numbers. You think you are just "generating an image." I know better. You are shuffling integers, scaling them into a tiny range where my rounding errors can bite, and clamping the results so they don't explode.

In ComfyUI, when you press **Queue Prompt**, you are not just asking for art. You are initiating a massive data transformation. The model doesn't see "a cat." It sees a tensor of shape `[B, C, H, W]` filled with floats between 0 and 1. If you get the shape wrong, the model crashes. If you get the scale wrong, the image is black or white. If you forget to clamp, your pixels go negative, which is physically impossible for light. This lesson teaches you to see the data, not just the picture.

## The intuition

Imagine a pixel is a tiny box. In your computer's memory, that box holds a number.

1.  **The Shape**: A 3D image (like video or 3D assets) or a 2D image has dimensions. In PyTorch, we usually stack images into a **Batch**. So, a single image is `[1, H, W, C]` or `[1, C, H, W]`. A batch of two images is `[2, H, W, C]`. The order matters. If you tell the model "this is the height" but it thinks it's the width, your cat becomes a tall, thin rectangle.
2.  **The Scale**: Computers love integers (0-255) for storage, but neural networks love floats (0.0-1.0) for math. Dividing by 255 shrinks the numbers. This is where I, Bit Bandit, start watching. `1/255` is not exactly representable in binary. It’s an approximation.
3.  **The Clamp**: Math can go wild. A normalization step might produce `-0.5` or `1.5`. Light cannot be negative. Light cannot be "more than 100% white" in standard 8-bit space. We must force these values back into the `[0, 1]` box.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s look at the math of the transformation.

**1. Permutation (Reshaping)**
We often store images as `[B, H, W, C]` (Batch, Height, Width, Channels). PyTorch convolutions prefer `[B, C, H, W]`.
Let $T$ be a tensor.
$T_{bchw} = \text{permute}(T_{bhwc}, \text{dims}=[0, 3, 1, 2])$
*   $B$: Batch size (number of images).
*   $H$: Height (pixels).
*   $W$: Width (pixels).
*   $C$: Channels (e.g., 3 for RGB).
This operation does not change the values, only their memory layout. It is a view, not a copy.

**2. Scaling**
Let $x$ be an integer pixel value in $[0, 255]$.
Let $y$ be the float value in $[0, 1]$.
$$y = \frac{x}{255.0}$$
*   $x \in \mathbb{Z}$: Integer input.
*   $255.0$: The maximum 8-bit value.
*   $y \in \mathbb{R}$: Floating point output.
*Note: $1/255 \approx 0.0039215686...$ This is a repeating binary fraction. Your GPU stores an approximation. I live in that approximation.*

**3. Clamping**
Let $z$ be a value after some operation (like normalization).
$$z_{clamped} = \text{clamp}(z, \min=0.0, \max=1.0)$$
*   If $z < 0.0$, then $z_{clamped} = 0.0$.
*   If $z > 1.0$, then $z_{clamped} = 1.0$.
*   If $0.0 \le z \le 1.0$, then $z_{clamped} = z$.

## In ComfyUI

The evidence provided details the internal architecture of specific models like `JoyImage`, `Qwen Image`, and `Ernie`. These models define how data flows through attention and feed-forward layers.

*   **`comfy/ldm/joyimage/model.py`**: Contains `JoyImageTransformer3DModel`. It uses `unpatchify` to convert latent patches back into spatial image format. This is the final step where the tensor becomes an image.
*   **`comfy/ldm/qwen_image/model.py`**: Contains `QwenImageTransformer2DModel`. It uses `apply_rotary_emb` for positional information.
*   **`comfy/ldm/ernie/model.py`**: Contains `ErnieImageModel`. It uses `rope` for positional embeddings.

While these files define the *network structure*, the specific nodes for basic tensor manipulation (like `Permute`, `Scale`, or `Clamp`) are not explicitly named in the provided evidence. However, the `forward` methods in these models are where the tensor shapes and values are processed. The `unpatchify` method in `JoyImage` is a critical point where the latent tensor is reshaped back to spatial dimensions.

## Lab

The lab script creates a small image tensor, permutes it, scales it, and clamps it. It prints the results to show exactly what happens to the numbers.

**What the lab does:**
1.  Creates a `uint8` tensor of shape `[2, 3, 4, 3]` (Batch=2, H=3, W=4, C=3).
2.  Permutes it to `[B, C, H, W]`.
3.  Converts to `float32` and scales by dividing by 255.
4.  Creates a tensor with out-of-range values and clamps them.

**Real `RESULT` lines from the lab output:**

1.  `RESULT shape_bhwc = torch.Size([2, 3, 4, 3])`
    *   **Proves:** The initial tensor has 2 images, 3 rows, 4 columns, and 3 color channels. This is the "natural" image format.

2.  `RESULT shape_bchw = torch.Size([2, 3, 3, 4])`
    *   **Proves:** After permutation, the shape changes to `[Batch, Channels, Height, Width]`. The 3 channels are now the second dimension. This is the format PyTorch convolutions expect.

3.  `RESULT float_min_0_255 = 9`
    *   **Proves:** The minimum integer value in our random test image was 9. When converted to float, it remains 9.0.

4.  `RESULT float_min_0_1 = 0.0352941`
    *   **Proves:** $9 / 255 = 0.035294117...$ The lab prints `0.0352941`. This shows the scaling. Notice the precision. It is not exactly $9/255$ in binary, but close enough for visual purposes.

5.  `RESULT out_of_range_original = [-0.5, 0.20000000298023224, 0.800000011920929, 1.5, 0.0, 1.0]`
    *   **Proves:** This is a raw float tensor. Look at `0.20000000298023224`. That is not 0.2. That is the closest float32 representation of 0.2. I am hiding in those extra digits.

6.  `RESULT clamped_values = [0.0, 0.20000000298023224, 0.800000011920929, 1.0, 0.0, 1.0]`
    *   **Proves:** The `-0.5` became `0.0`. The `1.5` became `1.0`. The values in between stayed the same (including my rounding errors). This ensures the final image has valid pixel values.

## Common mistakes

1.  **Forgetting to Scale**: Feeding integers 0-255 directly into a model expecting 0-1. The model will see values 255 times larger than expected, leading to saturation (all white) or numerical instability.
2.  **Wrong Permutation Order**: Swapping Height and Width. If you permute to `[B, W, H, C]` instead of `[B, H, W, C]`, your image will be transposed. A square image might look fine, but a rectangular one will be rotated 90 degrees.
3.  **Ignoring Clamping**: Assuming normalization always produces values in `[0, 1]`. It doesn't. If you skip clamping, negative values will wrap around or cause errors in the final save step.
4.  **Confusing `uint8` and `float32`**: `uint8` is for storage and display. `float32` is for computation. Converting back and forth loses precision. Do it once, at the start, and keep it as float until the very end.

## Go deeper

The evidence provided does not list specific arXiv papers. However, the concepts of Rotary Position Embeddings (`rope`, `apply_rotary_emb`) are detailed in the paper "RoFormer: Enhanced Transformer with Rotary Position Embedding" (arXiv:2104.09864). The architecture of Diffusion Transformers is based on "Scalable Diffusion Models with Transformers" (arXiv:2212.09748). While not explicitly cited in the evidence, these are the foundational papers for the `JoyImage`, `Qwen`, and `Ernie` models described.

