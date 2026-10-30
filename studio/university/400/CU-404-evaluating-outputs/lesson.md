# CU-404 - Evaluating outputs: metrics, checks and their limits

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

In the workshop, we don’t just "look" at a generated image or video to see if it looks "good." We measure it. But here is the hard truth I learned the expensive way: **metrics are not truth.** They are proxies. A high score doesn’t guarantee a good result, and a low score doesn’t always mean a bad one.

In CU-404, we move beyond "does it look like a cat?" to "how do we quantify the distance between what we asked for and what we got?" We will examine two fundamental metrics: **PSNR** (Peak Signal-to-Noise Ratio) and **Structural Correlation** (Pearson Correlation). We will see how they behave under different types of distortion—blur, brightness shifts, and spatial shifts—and why relying on a single number is a recipe for disaster in production pipelines.

## The intuition

Imagine you are comparing two photos of the same landscape.

1.  **PSNR** is like a strict accountant. It looks at every single pixel. If you shift the entire photo by one pixel to the right, the accountant screams, "Every pixel is wrong! The score is terrible!" Even though the human eye sees the exact same landscape, just moved. PSNR is sensitive to **pixel-level differences**.
2.  **Structural Correlation** is like a structural engineer. It looks at the *shape* and *pattern* of the data. If you shift the photo, the pattern remains. The correlation stays high. If you blur the photo, the pattern softens, but the general trend remains. Correlation is sensitive to **linear relationships** in the data, invariant to global shifts and scales.

The lesson? **PSNR tells you about fidelity; Correlation tells you about structure.** You need both.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s define the math precisely. We have an original image tensor $O$ and a distorted image tensor $D$, both of shape $(H, W)$.

### 1. Peak Signal-to-Noise Ratio (PSNR)

PSNR measures the ratio between the maximum possible power of a signal and the power of corrupting noise that affects its fidelity.

$$
\text{MSE} = \frac{1}{N} \sum_{i=1}^{N} (O_i - D_i)^2
$$

Where:
*   $N$ is the total number of pixels ($H \times W$).
*   $O_i$ and $D_i$ are the pixel values at position $i$.
*   $\text{MSE}$ is the Mean Squared Error.

$$
\text{PSNR} = 10 \cdot \log_{10} \left( \frac{\text{MAX}^2}{\text{MSE}} \right)
$$

Where:
*   $\text{MAX}$ is the maximum possible pixel value (e.g., 255 for 8-bit images).
*   If $\text{MSE} = 0$, $\text{PSNR} = \infty$.

**Key Insight:** PSNR is logarithmic. A 10 dB increase means the noise power is 10 times lower. It is extremely sensitive to small, uniform errors across the whole image.

### 2. Structural Correlation (Pearson)

This measures the linear relationship between the two images.

$$
r = \frac{\sum (O_i - \bar{O})(D_i - \bar{D})}{\sqrt{\sum (O_i - \bar{O})^2} \sqrt{\sum (D_i - \bar{D})^2}}
$$

Where:
*   $\bar{O}$ and $\bar{D}$ are the mean pixel values of the original and distorted images.
*   The numerator is the covariance.
*   The denominator is the product of the standard deviations.
*   $r$ ranges from $-1$ to $1$. $1$ means perfect positive linear correlation.

**Key Insight:** Correlation is invariant to affine transformations. If $D_i = a \cdot O_i + b$, then $r = 1$, regardless of $a$ or $b$. This is why brightness shifts don't hurt correlation.

## In ComfyUI

The evidence provided does not contain specific ComfyUI nodes for calculating PSNR or Pearson Correlation directly within the standard node library. The `comfy/text_encoders` and `comfy/ldm/genmo` modules focus on model architecture (encoders, VAEs, DiTs), not post-hoc evaluation metrics.

However, in a real ComfyUI workflow, you would typically:
1.  Use a **Load Image** node for the ground truth.
2.  Use your generation model (e.g., `AsymmDiTJoint` from `comfy/ldm/genmo`) to produce the output.
3.  Export both to disk.
4.  Run a Python script (like our lab) or a custom node (not covered in our sources) to compute these metrics.

*Note: Do not assume a built-in "PSNR Node" exists unless you have installed a specific community pack. The core ComfyUI codebase provided here does not list evaluation metric nodes.*

## Lab

We ran a synthetic experiment to visualize these limits. We created an $8 \times 8$ smooth diagonal gradient image. We then applied three distortions:
1.  **Blur:** A $3 \times 3$ box blur.
2.  **Brightness Shift:** Added 50 to all pixels.
3.  **Shift:** Rolled the image 1 pixel to the right.

Here are the exact `RESULT` lines from the lab output:

```
RESULT psnr_original = inf
RESULT corr_original = 1
RESULT psnr_blur = 29.4547
RESULT corr_blur = 0.998767
RESULT psnr_brightness = 14.1514
RESULT corr_brightness = 1
RESULT psnr_shift = 8.45098
RESULT corr_shift = 0.666667
```

**What each proves:**

1.  `psnr_original = inf` and `corr_original = 1`:
    *   **Proves:** The baseline is perfect. Identical images yield infinite PSNR (no error) and perfect correlation.

2.  `psnr_blur = 29.4547` and `corr_blur = 0.998767`:
    *   **Proves:** Blur is a "soft" distortion. It reduces PSNR significantly (from $\infty$ to ~29 dB), indicating pixel-level loss. However, correlation remains extremely high (~0.999), proving the structural pattern is largely preserved. A human would likely accept this image as "good."

3.  `psnr_brightness = 14.1514` and `corr_brightness = 1`:
    *   **Proves:** This is the critical failure mode of PSNR. A uniform brightness shift (+50) destroys PSNR (drops to ~14 dB, which is "bad" by PSNR standards). Yet, correlation is **1.0**. The structure is *perfectly* preserved. If you only looked at PSNR, you would reject a perfectly structured image that is just too bright.

4.  `psnr_shift = 8.45098` and `corr_shift = 0.666667`:
    *   **Proves:** Spatial misalignment is catastrophic for PSNR (8.45 dB is very low). Correlation drops to 0.66, which is moderate. This shows that while the gradient pattern is still somewhat recognizable (hence non-zero correlation), the pixel-wise mismatch is severe. For video or high-res images, a 1-pixel shift would be even more devastating to PSNR.

## Common mistakes

1.  **Trusting PSNR for perceptual quality:** As shown, a brightness shift can tank PSNR while leaving the image structurally perfect. Never use PSNR as your sole metric for "goodness."
2.  **Ignoring Correlation for alignment:** If your generated image is shifted by 1 pixel relative to the reference, PSNR will be terrible, but correlation might still be high. If you are training a model to align with a reference, you need a metric that penalizes spatial misalignment (like SSIM or LPIPS, not covered here, but implied by the limits of PSNR).
3.  **Assuming metrics are model-agnostic:** These metrics measure *difference*, not *quality*. A blurry image can have high correlation with a sharp one, but it’s still blurry. Metrics tell you *how different*, not *how good*.
4.  **Forgetting the scale:** PSNR is logarithmic. A difference of 1 dB is small; 10 dB is significant. Always interpret PSNR in context of the dynamic range.

## Go deeper

To understand why we care about these metrics in the context of generative models, look at these foundational papers:

*   **arXiv:1706.08500** (*GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium*): This paper introduces **FID** (Fréchet Inception Distance). FID is a more robust metric than PSNR for comparing distributions of generated vs. real images. It uses features from a pre-trained Inception network, capturing semantic similarity rather than just pixel difference. This is the "next step" beyond PSNR.
*   **arXiv:2103.00020** (*Learning Transferable Visual Models From Natural Language Supervision*): This paper (CLIP) demonstrates how to use natural language supervision to learn visual representations. This is crucial for **zero-shot evaluation**. Instead of comparing pixels, you can compare the *semantic meaning* of the generated image to the prompt using CLIP scores. This addresses the "limits" of pixel-based metrics by moving to feature space.

**Tinker Tune’s Final Note:**
Always report the metric. Always report the distortion. And always, *always* look at the image yourself. Metrics are tools, not judges.

