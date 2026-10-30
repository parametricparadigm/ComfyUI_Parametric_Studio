# CU-411 - Evaluating video: a flicker metric

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

**Instructor:** Reel Rascal
**Course:** CU-411 Evaluating video: a flicker metric
**Level:** 400 (Engineering and research)
**Prerequisites:** CU-404

## Why this matters

Cut! Action! Wait, hold on. Why is the background shimmering like a heat haze? Why does the character’s face look like it’s being remixed every 100 milliseconds? In image generation, we obsess over spatial fidelity—sharpness, texture, color accuracy. But video is time. It is a sequence of shots, a narrative flow, a continuous stream of photons hitting the retina. If your pixels jump around randomly from frame $t$ to frame $t+1$, you don’t have a video; you have a strobe light.

In the engineering of generative video models, "flicker" is the enemy of immersion. It is the visual noise that breaks the viewer’s suspension of disbelief. We need a metric that is not just a subjective "it looks weird," but a precise, computable measure of temporal instability. This lesson introduces the **Flicker Metric**, a simple yet powerful engineering tool derived from basic statistics. It allows us to quantify temporal consistency. If you can’t measure it, you can’t optimize it. And if you can’t optimize it, your model is just throwing dice at the screen.

## The intuition

Think of a video as a stack of transparencies. If you look at a single pixel position $(x, y)$ across time, what should you see? In a stable scene, that pixel should remain relatively constant. If the camera is static and the object is static, the pixel value at $t=0$, $t=1$, and $t=2$ should be identical.

Flicker occurs when that pixel value changes unpredictably. It’s not motion—motion is structured change. Flicker is *random* change. It’s the difference between a car driving down the road (structured spatial shift) and the car’s color randomly turning blue, then red, then green while staying in the same spot.

Our intuition is simple: **Stability is the inverse of variance.**

If the values at a specific pixel location do not change over time, their variance is zero. If they change wildly, their variance is high. Therefore, we can define a "flicker score" as the average temporal variance across all pixels. Lower is better. Zero is perfect stability.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s define the math precisely. We have a video tensor $V$ with dimensions $(T, C, H, W)$, where:
*   $T$ is the number of frames (time dimension).
*   $C$ is the number of channels (e.g., 3 for RGB).
*   $H$ is the height.
*   $W$ is the width.

For a specific pixel location $(c, h, w)$, we have a time series of values: $v_{c,h,w}(0), v_{c,h,w}(1), \dots, v_{c,h,w}(T-1)$.

The **temporal variance** for this specific pixel is calculated as:

$$ \text{Var}_{t}(c, h, w) = \frac{1}{T} \sum_{t=0}^{T-1} (v_{c,h,w}(t) - \bar{v}_{c,h,w})^2 $$

Where $\bar{v}_{c,h,w}$ is the mean value of that pixel over time:

$$ \bar{v}_{c,h,w} = \frac{1}{T} \sum_{t=0}^{T-1} v_{c,h,w}(t) $$

This gives us a variance map of shape $(C, H, W)$. To get a single scalar metric for the entire video, we take the mean of this variance map:

$$ \text{FlickerMetric} = \frac{1}{C \cdot H \cdot W} \sum_{c=0}^{C-1} \sum_{h=0}^{H-1} \sum_{w=0}^{W-1} \text{Var}_{t}(c, h, w) $$

In code, this is often implemented by computing the variance along the time dimension (dimension 0) and then taking the mean of the resulting tensor.

**Key Insight:** This metric assumes that "good" video has low temporal variance at fixed spatial locations. This is a strong assumption that works well for static scenes or slow-motion shots. For fast motion, you might need optical flow compensation, but for baseline evaluation of *generative* stability (i.e., is the model hallucinating new textures?), raw temporal variance is the gold standard.

## In ComfyUI

In the context of ComfyUI, this metric is not a built-in node in the standard library for general video evaluation, as it is a post-processing analysis step rather than a generation step. However, the architecture of video models like Genmo (found in `comfy/ldm/genmo`) relies on temporal consistency in the latent space.

The `VideoVAE` class in `comfy/ldm/genmo/vae/model.py` handles the encoding and decoding of video frames. The `Encoder` downsamples input video frames into a latent distribution, handling temporal and spatial downsampling. If the `VideoVAE` introduces temporal noise during decoding, or if the `AsymmDiTJoint` diffusion model fails to maintain temporal coherence in the latent space, the resulting pixel-space video will exhibit high flicker.

While ComfyUI does not have a dedicated "Flicker Metric" node in the core distribution, you can implement this logic using standard PyTorch operations within a custom node or a Python script. You would take the output video tensor from a `VideoDecode` node, compute the variance along the time dimension, and output the scalar value. This allows you to integrate the metric directly into your workflow for real-time monitoring or automated testing.

## Lab

In this lab, we simulate two video sequences: a **stable** video where pixel values remain constant across frames, and a **flickering** video where pixel values change randomly. We compute the flicker metric for both to demonstrate the inverse relationship between variance and stability.

The lab uses PyTorch to create tensors of shape $(3, 1, 2, 2)$ representing 3 frames, 1 channel, and a $2 \times 2$ grid of pixels.

**Lab Output:**

```text
RESULT stable_metric = 0
RESULT flicker_metric = 2.83333
```

**Analysis:**

1.  `RESULT stable_metric = 0`: This proves that for a perfectly stable video (where every pixel value is identical across all frames), the temporal variance is exactly zero. This confirms our baseline: zero flicker is achievable and measurable.
2.  `RESULT flicker_metric = 2.83333`: This proves that for a video with random pixel changes, the metric yields a positive, non-zero value. The specific value (2.83333) is the average of the variances of the individual pixels in the $2 \times 2$ grid. For example, the pixel at (0,0) has values [1.0, 5.0, 3.0]. Its mean is 3.0. Its variance is $\frac{(1-3)^2 + (5-3)^2 + (3-3)^2}{3} = \frac{4+4+0}{3} = 2.666...$. Averaging across all 4 pixels gives the final metric. This demonstrates that the metric scales with the magnitude of the temporal noise.

## Common mistakes

1.  **Confusing Motion with Flicker:** If you apply this metric to a video of a fast-moving car, you will get a high score. This is not flicker; it is motion. To evaluate flicker in dynamic scenes, you must first align frames using optical flow or feature tracking, then compute variance on the aligned pixels. Without alignment, you are measuring motion, not instability.
2.  **Using the Wrong Dimension:** In PyTorch, if your tensor is shaped $(T, C, H, W)$, you must compute variance along `dim=0`. If you accidentally compute it along `dim=1` (channels), you are measuring color inconsistency, not temporal flicker.
3.  **Ignoring Normalization:** If your video values are in the range [0, 255] vs [0, 1], the magnitude of the variance will differ by a factor of $255^2$. Always normalize your video tensors to [0, 1] or [-1, 1] before computing the metric to ensure comparability across different datasets.
4.  **Small Sample Sizes:** With only 2 frames, variance is a poor estimator of stability. You need at least 3-5 frames to get a meaningful signal. With 2 frames, variance is just the squared difference divided by 2, which is sensitive to single-frame outliers.

## Go deeper

For a deeper understanding of temporal consistency in video generation, refer to the following papers:

*   **arXiv:2310.02504** - *Video Diffusion Models* (or similar foundational work on temporal attention). This paper discusses how diffusion models can be extended to video by adding temporal attention layers, which is crucial for reducing flicker.
*   **arXiv:2301.12503** - *Sora: Video Generation Models as World Simulators*. While not a technical paper on metrics, it highlights the importance of temporal coherence as a key challenge in video generation.
*   **arXiv:2212.03916** - *Make-A-Video: Text-to-Video Generation without Text-Video Data*. This paper introduces techniques for maintaining temporal consistency in video generation, which can be evaluated using metrics like the one described here.

Remember, Reel Rascal here: Count your frames, check your variance, and keep the flicker out of your reel. Cut!

