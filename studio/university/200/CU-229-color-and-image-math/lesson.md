# CU-229 - Color spaces, gamma and image math

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back, students. I am Bit Bandit, and I live in the last few bits of your float32 tensors. You think you are just moving pixels around? No. You are manipulating light, and light does not care about your perceptual preferences.

In ComfyUI, you often see nodes that blend images, apply filters, or convert color spaces. If you do the math in the wrong space, your images will look "washed out" or "muddy." Why? Because sRGB is not linear. It is a perceptual curve designed for human eyes, not for physics. When you average two sRGB values, you are not averaging the light; you are averaging the *encoding* of the light. This lesson teaches you to see the difference between the number you see and the light it represents.

## The intuition

Imagine a dimmer switch. In a linear world, turning the knob halfway gives you half the light. In sRGB, the curve is compressed in the shadows and expanded in the highlights. If you take a black pixel (0.0) and a white pixel (1.0) and average them in sRGB space, you get 0.5. But 0.5 in sRGB is not "half the light." It is a specific perceptual gray.

If you convert both to linear light, average them, and convert back, you get a much brighter gray. Why? Because the sRGB curve compresses the upper range. The "midpoint" of light intensity is actually higher on the sRGB scale than 0.5. If you ignore this, your blends will look darker than they should be. This is the "gamma trap."

## Under the hood (the mechanism; math in plain text, define every symbol)

The sRGB standard defines a piecewise function to convert between linear light and sRGB values. Let $x$ be the linear light value (0 to 1) and $y$ be the sRGB value (0 to 1).

**Linear to sRGB:**
If $x \le 0.0031308$, then $y = 12.92 \cdot x$.
If $x > 0.0031308$, then $y = 1.055 \cdot (x^{(1/2.4)}) - 0.055$.

**sRGB to Linear:**
If $y \le 0.04045$, then $x = y / 12.92$.
If $y > 0.04045$, then $x = ((y + 0.055) / 1.055)^{2.4}$.

The exponent $2.4$ is the "gamma" approximation. The linear segment near zero prevents numerical instability and preserves detail in shadows.

When you blend two images, say $A$ and $B$, with a weight $w$ (where $w$ is between 0 and 1), the correct linear blend is:
$L_{out} = w \cdot L_A + (1-w) \cdot L_B$
where $L$ is the linear light value.

If you do this in sRGB space:
$S_{out} = w \cdot S_A + (1-w) \cdot S_B$
This is mathematically incorrect for light mixing. The error is largest in the mid-tones.

## In ComfyUI

Our sources do not provide specific node names for color space conversion in the core ComfyUI distribution, but the `tests-unit/comfy_extras_test` folder contains tests for `image_color_space_acescg_test.py` and `compositor_blend_test.py`. This indicates that ComfyUI extensions handle color space management and blending logic. The `TestBoundaryRules` class in `compositor_blend_test.py` validates mathematical boundaries for image blend modes, suggesting that correct linear-space math is enforced in these extensions. For standard nodes, always check if the node documentation specifies "linear" or "sRGB" blending. If it is not specified, assume sRGB and be cautious.

## Lab

We ran a Python script using PyTorch to demonstrate the difference between sRGB and linear blending. The script defines `srgb_to_linear` and `linear_to_srgb` functions based on the standard formulas. It then blends black (0.0) and white (1.0) 50/50 in both spaces and averages a gradient.

Here are the exact `RESULT` lines from the lab output:

`RESULT blend_srgb_space = 0.5`
This proves that a simple 50/50 average of sRGB values 0.0 and 1.0 yields 0.5. This is the "naive" blend.

`RESULT blend_linear_to_srgb = 0.735357`
This proves that when we convert 0.0 and 1.0 to linear, average them (getting 0.5 linear), and convert back to sRGB, the result is 0.735357. This is significantly brighter than 0.5. The linear midpoint is perceptually lighter.

`RESULT avg_srgb_gradient = 0.5`
This shows the average of a linearly spaced sRGB gradient (0.0 to 1.0) is 0.5. This is the arithmetic mean of the sRGB values.

`RESULT avg_linear_to_srgb = 0.610789`
This shows the average of the same gradient after converting to linear, averaging the linear values, and converting back to sRGB. The result is 0.610789. This confirms that averaging in linear space yields a different (brighter) result than averaging in sRGB space.

`RESULT roundtrip_max_error = 5.96046e-08`
This verifies that our conversion functions are inverses of each other. The maximum error is less than $10^{-7}$, which is within floating-point precision limits. This ensures that our math is consistent and that any differences in blending are due to the color space, not conversion errors.

## Common mistakes

1.  **Blending in sRGB space:** This is the most common error. It makes blends look darker and less vibrant. Always convert to linear, blend, and convert back.
2.  **Ignoring the linear segment:** Some implementations use a simple power law ($x^{2.4}$) for all values. This is incorrect for sRGB. The piecewise function with the linear segment near zero is required for accuracy, especially in shadows.
3.  **Assuming all nodes are linear:** Not all ComfyUI nodes perform linear blending. Check the documentation. If a node is designed for "perceptual" blending, it may intentionally stay in sRGB.
4.  **Floating-point precision:** When converting back and forth, small errors can accumulate. The lab shows a max error of $5.96046e-08$, which is negligible for most applications, but be aware of it in high-precision workflows.

## Go deeper

The evidence does not provide specific arXiv paper IDs for this lesson. However, the sRGB standard is defined by the IEC 61966-2-1 standard. For a deeper understanding of color spaces and gamma, refer to the original sRGB specification and related literature on perceptual uniformity in color spaces.

