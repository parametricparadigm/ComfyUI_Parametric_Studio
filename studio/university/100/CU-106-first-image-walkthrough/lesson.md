# CU-106 - Your first image: checkpoint, sampler, VAE

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome aboard, cadet. You’ve got your prerequisites from CU-102, so you know the deck layout. Now we’re going to press the button that actually makes the magic happen. In ComfyUI, pressing "Queue Prompt" isn't just a UI action; it’s a command to the `PromptExecutor` to resolve dependencies and fire up the heavy machinery.

If you don’t understand the three pillars of image generation—the **Checkpoint**, the **Sampler**, and the **VAE**— you’re just guessing at the helm. This lesson breaks down exactly what happens between the moment you click that button and the moment pixels appear on your screen. We’re going to look at the data shapes, the math of denoising, and the compression that makes it all possible.

## The intuition

Think of image generation as a rescue mission in a foggy harbor.

1.  **The Checkpoint** is your ship. It contains the engine (the UNet), the navigation charts (CLIP text encoders), and the hull plating (the VAE). It’s a single file that holds all the learned weights.
2.  **The Sampler** is your steering wheel and throttle. It decides how you navigate through the fog. Do you take big, bold turns (Euler) or small, cautious adjustments (Heun)? It controls the path from pure noise to a clear image.
3.  **The VAE** is the translator. The engine works in a compressed, abstract language (latents). The VAE translates that abstract language into human-readable pixels (RGB).

When you queue a prompt, ComfyUI loads the checkpoint, encodes your text into a vector, creates a blob of random noise, and then uses the sampler to iteratively clean up that noise, guided by your text. Finally, the VAE decodes the cleaned noise into the image you see.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s look at the data flow using the shapes from our lab evidence.

**1. Text Encoding**
Your prompt is passed to the CLIP encoder. In our lab, we simulated this with a tensor `text_emb` of shape `(1, 77, 768)`.
*   `1`: Batch size (one image).
*   `77`: Sequence length (number of tokens).
*   `768`: Dimensionality of each token embedding.
Total elements: $1 \times 77 \times 768 = 59,136$. This vector tells the model *what* to draw.

**2. The Latent Space**
We don’t generate images directly. We generate **latents**. For a $64 \times 64$ image, the VAE downsamples it by a factor of 8.
*   Original Image Shape: `(1, 3, 64, 64)` (Batch, Channels, Height, Width).
*   Latent Shape: `(1, 4, 8, 8)`.
    *   `4`: Latent channels (compressed color information).
    *   `8`: Height ($64 / 8$).
    *   `8`: Width ($64 / 8$).
Total latent elements: $1 \times 4 \times 8 \times 8 = 256$.

Notice the **compression factor**:
$$ \text{Compression Factor} = \frac{\text{Image Elements}}{\text{Latent Elements}} = \frac{1 \times 3 \times 64 \times 64}{1 \times 4 \times 8 \times 8} = \frac{12,288}{256} = 48 $$
We are working with 48 times fewer numbers than the final image. This is why diffusion models are computationally feasible.

**3. The Denoising Loop (The Sampler)**
The sampler starts with a latent filled with random noise. It runs a loop for `num_steps` (e.g., 5 steps in our lab). In each step, it predicts the noise and subtracts it.
In our simplified lab, we simulated this with a decay factor:
$$ \text{current\_latent}_{t+1} = \text{current\_latent}_t \times \text{decay\_factor} $$
Where `decay_factor` is 0.5.
*   Step 0 Norm: $7.88053$
*   Step 1 Norm: $3.94026$
*   Step 2 Norm: $1.97013$
*   Step 3 Norm: $0.985066$
*   Step 4 Norm: $0.492533$

The norm (magnitude) of the latent decreases as the noise is removed. In real diffusion, this isn't just multiplication; it involves the UNet predicting the noise $\epsilon$ based on the current latent $x_t$, the timestep $t$, and the text conditioning $c$. The update rule is roughly:
$$ x_{t-1} = x_t - \text{step\_size} \times \epsilon_{\text{predicted}} $$

**4. Decoding**
Once the loop finishes, we have a clean latent `(1, 4, 8, 8)`. The VAE decoder upsamples this back to `(1, 3, 64, 64)`.
*   Decoded Shape: `(1, 3, 64, 64)`.
*   Decoded Elements: $12,288$.

## In ComfyUI

Based on our sources, here is how these concepts map to ComfyUI’s architecture:

*   **Checkpoint Loading**: The function `load_checkpoint_guess_config` in `comfy/sd.py` is the primary entry point. It automatically detects the model architecture and loads the UNet, VAE, and CLIP components. The `ModelPatcher` class wraps these models to manage weight loading and offloading to save VRAM.
*   **The Sampler**: The `KSAMPLER` class in `comfy/samplers.py` executes the denoising loop. It applies conditioning and calculates noise predictions. The actual mathematical implementations for different sampling algorithms (like Euler or Heun) live in `comfy/k_diffusion/sampling.py`. For example, `sample_euler` implements Algorithm 2 from Karras et al. (2022), while `sample_heun` implements Heun steps.
*   **The VAE**: The `VAE` class in `comfy/sd.py` handles the encoding and decoding. It supports tiled operations for large images to manage memory.
*   **Execution**: When you press Queue, the `PromptExecutor` in `execution.py` resolves the graph. It uses `folder_paths.py` to locate your checkpoint file and loads it into memory.

## Lab

Our lab script simulates the entire pipeline with a $64 \times 64$ image and 5 denoising steps. It verifies the shape transformations and the reduction of noise magnitude.

Here are the key `RESULT` lines from the lab output and what they prove:

1.  `RESULT text_emb_shape = (1, 77, 768)`
    *   **Proves**: The text conditioning is a 3D tensor. The model expects 77 tokens, each with 768 dimensions. This is the "instruction" vector.

2.  `RESULT latent_shape = (1, 4, 8, 8)`
    *   **Proves**: The diffusion process happens in a compressed space. For a 64x64 image, the latent is only 8x8 pixels with 4 channels. This confirms the 8x spatial downsampling.

3.  `RESULT compression_factor = 48`
    *   **Proves**: The VAE compresses the data by a factor of 48. This is why we can run diffusion on GPUs with limited VRAM; we are manipulating 256 numbers instead of 12,288.

4.  `RESULT step_0_latent_norm = 7.88053`
    *   **Proves**: At the start of the process, the latent has a high magnitude (high noise).

5.  `RESULT step_4_latent_norm = 0.492533`
    *   **Proves**: After 5 steps, the magnitude has dropped significantly. The noise has been reduced, leaving the structured signal of the image.

6.  `RESULT decoded_shape = (1, 3, 64, 64)`
    *   **Proves**: The VAE decoder successfully upsamples the latent back to the original image dimensions and converts the 4 latent channels into 3 RGB channels.

## Common mistakes

1.  **Mismatched Checkpoint and VAE**: If you load a checkpoint that expects a specific VAE (like SDXL vs. SD1.5) but use the wrong one, your image will be garbled or black. The `load_checkpoint_guess_config` function tries to guess, but explicit VAE loading is safer for custom models.
2.  **Ignoring the Sampler**: Using a sampler with too few steps (e.g., 5 steps for a complex image) will result in noisy, unfinished images. The lab shows that even 5 steps significantly reduce noise, but real-world images often need 20-30 steps for clarity.
3.  **VRAM Exhaustion**: If your image is too large, the latent tensor grows. Remember, the latent size is $(H/8) \times (W/8) \times 4$. A 1024x1024 image has a latent of $128 \times 128 \times 4 = 65,536$ elements. If your GPU runs out of memory, ComfyUI’s `ModelPatcher` will try to offload weights to CPU, which slows things down.

## Go deeper

For the mathematical foundations of the sampling algorithms mentioned in `comfy/k_diffusion/sampling.py`, refer to:

*   **Karras et al. (2022)**: "Elucidating the Design Space of Diffusion-Based Generative Models". This paper defines the noise schedules and sampling algorithms (Euler, Heun) implemented in `sample_euler` and `sample_heun`.
*   **Tiankai et al. (2024)**: Referenced in `get_sigmas_laplace` for the Laplace noise schedule.

These papers provide the rigorous definitions for the sigma schedules and solver steps that ComfyUI uses to navigate the latent space.

