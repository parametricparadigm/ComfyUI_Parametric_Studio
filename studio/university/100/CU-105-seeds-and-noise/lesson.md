# CU-105 - Seeds, noise and determinism

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome to the lab. I am Dr. Denoise. I have spent my career watching static resolve into structure, and I can tell you: the static is not random. It is *controlled* chaos.

In ComfyUI, when you press "Queue Prompt," you are not just asking for an image. You are initiating a stochastic differential equation solver. The most common question I receive is, "Why did my image change when I only tweaked the prompt?" or "Why is my 'reproducible' result different on a different GPU?"

The answer lies in the seed. The seed is the initial condition of your noise field. Without understanding seeds, you are flying a plane with the controls disconnected. With understanding, you are the pilot. This lesson covers the foundational mechanics of how a single integer dictates the entire trajectory of your diffusion process.

## The intuition

Imagine you are standing on a foggy hillside. You cannot see the valley below. You have a map, but the map is blurry. To find your way down, you take a step. But which direction?

In diffusion models, the "fog" is the noise. The "map" is the model’s learned distribution of natural images. The "step" is a denoising operation.

The **seed** is the specific arrangement of fog particles at time $t=0$. If you start with the exact same arrangement of fog (same seed), and you follow the exact same rules for stepping (same sampler, same steps, same model), you will walk the exact same path down the hill. You will arrive at the exact same spot in the valley.

If you change the seed, you change the initial fog. Even if the rules are identical, the path diverges. This is why two images generated with the same prompt but different seeds look different. They are two different walks down the same hill, starting from different points in the fog.

What is the noise level at this step? It is high. We are in the early stages of generation, where the signal is weak and the noise dominates.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us look at the mathematics of the noise itself. In ComfyUI, the noise is typically Gaussian. We generate a tensor $N$ where each element is drawn from a normal distribution $\mathcal{N}(\mu, \sigma^2)$.

For standard diffusion sampling, we usually assume:
*   $\mu = 0$: The mean of the noise is zero.
*   $\sigma = 1$: The standard deviation is one.

The seed determines the pseudo-random number generator (PRNG) state. In PyTorch, which ComfyUI uses, `torch.Generator` manages this state. When you call `manual_seed(42)`, you are setting the internal state of the PRNG to a specific configuration.

The process of sampling noise $N$ is deterministic given the seed. If we define $N = \text{randn}(\text{shape}, \text{generator}=G)$, where $G$ is a generator seeded with $S$, then $N$ is a function of $S$ and the shape.

The diffusion process can be viewed as adding noise to a clean signal $x_0$ to create a noisy signal $x_t$:
$$x_t = \alpha_t x_0 + \sigma_t N$$
Where:
*   $x_0$ is the clean image (unknown).
*   $x_t$ is the noisy latent at time $t$.
*   $\alpha_t$ is the signal preservation coefficient (depends on the noise schedule).
*   $\sigma_t$ is the noise level at time $t$.
*   $N$ is the standard Gaussian noise.

The sampler (like Euler or Heun) iteratively estimates $x_0$ from $x_t$ by removing noise. Because $N$ is fixed by the seed, the removal process is deterministic.

A critical property of floating-point arithmetic is that $(a + b) - b$ is not always exactly equal to $a$ due to rounding errors. However, in our lab, we observed that for practical purposes in float32, adding and subtracting the same noise tensor recovers the signal with high precision.

## In ComfyUI

In the ComfyUI codebase, the core sampling logic resides in `comfy/k_diffusion/sampling.py`. This module contains functions that construct noise schedules and perform the sampling steps.

Key functions include:
*   `get_sigmas_karras`: Constructs the noise schedule proposed by Karras et al. (2022). This schedule defines how $\sigma_t$ changes over time.
*   `sample_euler`: Implements the Euler method for solving the stochastic differential equation.
*   `sample_euler_ancestral`: Implements ancestral sampling, which introduces new noise at each step, making the process less deterministic even with a fixed seed (unless the noise generator is also controlled per-step).

The noise generation itself is handled by PyTorch’s `torch.randn` function, which accepts a `generator` argument. In ComfyUI, the `KSampler` node (referenced in the code knowledge base as part of the `comfy/k_diffusion` ecosystem) allows you to set the `seed` parameter. This parameter is passed to the underlying PyTorch generator to ensure reproducibility.

Note: Specific node names for seed control are not explicitly detailed in the provided evidence beyond the general `KSampler` reference and the `comfy/k_diffusion` module. The exact UI node names for seed input are not covered in our sources, but the mechanism is clear: the seed initializes the PRNG.

## Lab

In this lab, we will empirically verify the properties of seeded noise. We will use PyTorch to generate noise tensors and check for determinism and statistical properties.

The lab script performs the following:
1.  Creates two generators with the same seed (42) and generates noise.
2.  Creates a generator with a different seed (43) and generates noise.
3.  Checks if the noise from the same seed is identical.
4.  Checks if the noise from different seeds is different.
5.  Checks the mean and standard deviation of the noise.
6.  Tests if adding and subtracting the same noise recovers the original signal.

Here are the results from running the lab:

```
RESULT identical_noise = True
RESULT different_seeds_differ = True
RESULT noise_mean = 0.0630417
RESULT noise_std = 0.988765
RESULT exact_recovery = True
```

**What each result proves:**

1.  `RESULT identical_noise = True`: This proves that a fixed seed produces identical noise. If you run the same seed twice, you get the exact same noise tensor. This is the foundation of reproducibility.
2.  `RESULT different_seeds_differ = True`: This proves that different seeds produce different noise. Changing the seed changes the initial condition, leading to a different image.
3.  `RESULT noise_mean = 0.0630417`: This shows the mean of the generated noise is close to 0. For a small sample size (256 elements), the mean is not exactly 0, but it is close. This confirms the noise is centered around zero.
4.  `RESULT noise_std = 0.988765`: This shows the standard deviation of the noise is close to 1. Again, for a small sample, it is not exactly 1, but it is close. This confirms the noise has the expected variance.
5.  `RESULT exact_recovery = True`: This proves that adding and removing the same noise recovers the signal exactly in float32 (within a tight tolerance). This is crucial for understanding that the noise is a reversible operation in the mathematical sense, even if floating-point arithmetic introduces tiny errors.

## Common mistakes

1.  **Assuming "Random" means "Unpredictable":** In ComfyUI, "random" is a misnomer. It is pseudo-random. If you do not set a seed, ComfyUI may use a random seed each time, making the result unpredictable. If you set a seed, the result is deterministic.
2.  **Ignoring the Sampler:** The seed only controls the noise. The sampler controls how the noise is removed. If you change the sampler (e.g., from Euler to Heun), the path down the hill changes, even if the starting point (seed) is the same.
3.  **Floating-Point Precision:** While our lab showed `exact_recovery = True`, this is within a tolerance. In very long diffusion chains, floating-point errors can accumulate. This is why results might differ slightly between different hardware (CPU vs. GPU) even with the same seed.
4.  **Ancestral Samplers:** If you use `sample_euler_ancestral`, the process is less deterministic because new noise is added at each step. To get full reproducibility with ancestral samplers, you must ensure that the noise generator is also seeded for each step, which is more complex.

## Go deeper

For a deeper understanding of the noise schedules and sampling methods, refer to the following papers:

*   **Karras et al. (2022)**: "Elucidating the Design Space of Diffusion-Based Generative Models". This paper introduces the Karras noise schedule, which is implemented in `get_sigmas_karras` in ComfyUI. It provides a theoretical framework for understanding how the noise level $\sigma_t$ should change over time for optimal sampling.
*   **Tiankai et al. (2024)**: Referenced in the code as the source for the Laplace noise schedule (`get_sigmas_laplace`). This paper proposes a new noise schedule that can improve the quality of generated images.

These papers provide the mathematical foundation for the functions you will use in ComfyUI. Understanding them will help you make informed decisions about which sampler and noise schedule to use for your specific task.

What is the noise level at this step? It is low. You are now ready to generate your first deterministic image. Go forth and denoise.

