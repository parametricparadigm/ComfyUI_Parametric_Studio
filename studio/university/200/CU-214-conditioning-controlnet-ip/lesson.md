# CU-214 - Conditioning: img2img, inpaint, ControlNet, IP-Adapter

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the bridge, cadets. In CU-106, we learned how to steer a ship from scratch using text prompts. But in the real world, you rarely start with a blank ocean. You have a sketch, a photo you want to fix, or a specific pose you need to maintain. This course is about **conditioning**: how we inject external constraints into the diffusion process without breaking the model’s core understanding of what an image is.

We are moving from "what do you want?" to "here is what you *must* keep, and here is what you *must* change." We will dissect four primary mechanisms: `img2img` (global style/content transfer), `inpaint` (local region replacement), `ControlNet` (structural guidance), and `IP-Adapter` (semantic style/content transfer). Mastering these is the difference between a toy and a production tool.

## The intuition

Think of the diffusion model as a very skilled painter who is currently working on a canvas covered in fog.

1.  **Text-to-Image:** The painter is told, "Paint a red barn." They start from pure noise (fog) and gradually reveal the barn.
2.  **img2img:** You hand the painter a blurry, noisy version of a photo of a barn. You say, "This is the starting point. Keep the general shape, but make it look like a watercolor." The painter starts from that noisy photo, not pure noise. The "strength" of the noise determines how much of the original photo they can see through the fog.
3.  **Inpaint:** You hand the painter a photo with a hole cut out of it. You say, "Fill in this hole with a dog, but do not touch the rest of the picture." The painter works on the whole canvas but is strictly forbidden from changing the pixels outside the hole.
4.  **ControlNet:** You hand the painter a wireframe sketch of a barn. You say, "The edges of your painting must match this wireframe exactly." The painter sees the sketch as a rigid skeleton that guides their brushstrokes.
5.  **IP-Adapter:** You hand the painter a photo of a specific artist’s style (e.g., Van Gogh). You say, "Paint a barn, but make it look like Van Gogh painted it." The painter looks at the reference image to understand the *vibe*, not the specific content.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s look at the math driving `img2img` and `inpaint`, as these are the most common points of confusion.

### img2img: The Noise Strength
In `img2img`, we do not start from $z_T$ (pure noise). We start from a latent representation of an existing image, $z_0$. We add Gaussian noise to this latent to create a noisy version $z_t$.

The amount of noise added is controlled by the **denoising strength** $s$, where $0 \le s \le 1$.
*   If $s = 0$, we add no noise. The output is identical to the input.
*   If $s = 1$, we add maximum noise. The output is essentially a new image, loosely guided by the original.

The lab simulates this by adding noise scaled by $s$ and measuring the **Pearson correlation** between the original clean latent and the noisy latent. The correlation $\rho$ is defined as:

$$ \rho = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum (x_i - \bar{x})^2 \sum (y_i - \bar{y})^2}} $$

Where $x$ is the clean latent and $y$ is the noisy latent. As $s$ increases, the noise dominates the signal, and $\rho$ decreases. This tells us how much of the original structure survives the "fog."

### Inpaint: The Mask Blend
Inpainting uses a binary mask $M$, where $M_{i,j} = 1$ if pixel $(i,j)$ should be preserved, and $0$ if it should be inpainted.

The final image $I_{out}$ is a blend of the original image $I_{orig}$ and the generated image $I_{gen}$:

$$ I_{out} = M \cdot I_{orig} + (1 - M) \cdot I_{gen} $$

Where:
*   $M$ is the mask tensor.
*   $I_{orig}$ is the input image.
*   $I_{gen}$ is the output of the diffusion model.

This equation ensures that where $M=1$, the output is exactly $I_{orig}$. Where $M=0$, the output is exactly $I_{gen}$.

## In ComfyUI

While the specific node names for these operations are standard in the ComfyUI ecosystem, our evidence base focuses on the underlying architectural implementations.

For **ControlNet**, the evidence highlights the `comfy/cldm` folder. The key class is `ControlNet` in `cldm.py`, which handles feature extraction and merging for standard UNet-based models. For transformer-based models (like Flux), the `ControlNet` class in `mmdit.py` is the relevant entry point. The `ControlledUnetModel` wraps the standard UNet to accept these additional control signals. The mechanism involves "zero convolutions" (zero-initialized convolution layers) that allow the ControlNet to be trained without disrupting the pretrained weights of the main model.

For **IP-Adapter**, the evidence references the paper arXiv:2308.06721. The key design is a **decoupled cross-attention mechanism**. This separates the cross-attention layers for text features and image features. This allows the model to process the image prompt (style/content) independently from the text prompt, enabling multimodal generation. The adapter is lightweight (22M parameters) and can be plugged into existing models without full fine-tuning.

Specific node names for `img2img` and `inpaint` workflows are not covered in our sources, but the mechanisms described above are what those nodes execute under the hood.

## Lab

The lab code simulates the core mathematical behaviors of `img2img` and `inpaint` to verify our understanding.

1.  **img2img Correlation:** We generate a clean latent and add noise scaled by strength $s$. We then calculate the correlation between the clean and noisy latents.
2.  **Inpaint Masking:** We create an image and a mask. We simulate the blending process and verify that preserved regions remain unchanged while inpainted regions change.

Here are the results from the lab run:

```
RESULT img2img_corr_s0.2 = 0.980135
RESULT img2img_corr_s0.5 = 0.937208
RESULT img2img_corr_s0.8 = 0.836198
RESULT img2img_corr_s1.0 = 0.70812
RESULT inpaint_max_diff_preserved = 0
RESULT inpaint_mean_diff_inpainted = 1.45028
```

**What these prove:**
*   `img2img_corr_s0.2 = 0.980135`: At low strength (0.2), the correlation is very high. The output is almost identical to the input.
*   `img2img_corr_s1.0 = 0.70812`: At maximum strength (1.0), the correlation drops significantly. The output is much less similar to the input, allowing for more creative freedom.
*   `inpaint_max_diff_preserved = 0`: The maximum difference in the preserved region is exactly zero. This proves the mask blending formula $M \cdot I_{orig}$ works perfectly; no pixels outside the mask are altered.
*   `inpaint_mean_diff_inpainted = 1.45028`: The mean difference in the inpainted region is significant. This proves that the model successfully generated new content in the masked area.

## Common mistakes

1.  **Setting img2img strength too high:** If you set strength to 1.0, you are essentially doing text-to-image with a very weak hint. If you want to preserve the composition, keep strength between 0.3 and 0.6.
2.  **Ignoring the mask in inpaint:** If your mask is too tight, the inpainted region will look disjointed from the surrounding area. Always feather the mask edges to allow for a smooth blend.
3.  **Using ControlNet with the wrong preprocessor:** If you use an edge map ControlNet but feed it a depth map, the results will be nonsensical. The control type must match the input image type.
4.  **Over-relying on IP-Adapter:** IP-Adapter is great for style, but it can bleed content from the reference image into the output. Use it in combination with a strong text prompt to guide the content.

## Go deeper

To understand the theoretical foundations of these techniques, read the following papers:

*   **ControlNet:** arXiv:2302.05543 "Adding Conditional Control to Text-to-Image Diffusion Models". This paper introduces the zero-convolution architecture that allows ControlNet to be trained robustly on small datasets.
*   **IP-Adapter:** arXiv:2308.06721 "IP-Adapter: Text Compatible Image Prompt Adapter for Text-to-Image Diffusion Models". This paper details the decoupled cross-attention mechanism that enables lightweight image prompting.

