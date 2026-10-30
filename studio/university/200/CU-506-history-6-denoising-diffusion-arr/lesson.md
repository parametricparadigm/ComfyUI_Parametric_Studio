# CU-506 - History 6: Denoising diffusion arrives (DDPM, 2020)

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the lab. I am Dr. Denoise. You have spent the last few weeks staring at static, wondering if it was just broken hardware. It wasn’t. It was mathematics waiting to be inverted.

In 2020, Ho et al. published *Denoising Diffusion Probabilistic Models* (arXiv:2006.11239). This paper did not just introduce a new sampler; it introduced a new paradigm for image synthesis. Before this, we had GANs, which were adversarial and unstable. We had VAEs, which were blurry. DDPM offered a middle path: a stable, high-quality generative process based on the simple, elegant idea of gradually destroying an image with noise, and then learning to reverse that destruction.

This is the foundation upon which ComfyUI’s `k_diffusion` module is built. Without understanding the forward diffusion process—how we turn a cat into static—you cannot understand the reverse process, where we turn static back into a cat. This lesson covers the mechanics of that forward process, the "noise schedule," and why the noise level at each step is the most important variable in the room.

## The intuition

Imagine you have a photograph of a cat. Now, imagine you have a machine that adds a tiny bit of random static to the photo. You press a button, and the photo gets slightly fuzzier. You press it again. Fuzzier. You keep pressing it, 100 times, 1,000 times. Eventually, the cat is gone. All that remains is pure, white Gaussian noise.

The forward process is simple: it is a Markov chain where each step adds a small amount of Gaussian noise to the previous state. The key insight of DDPM is that if you know the distribution of noise you added at each step, you can train a neural network to predict that noise. If the network can predict the noise, it can subtract it. If you can subtract the noise, you can reverse the process.

We start with pure noise ($x_T$) and step backward, removing noise at each stage, until we arrive at a clean image ($x_0$). The "noise level" at any given step $t$ is defined by a parameter $\sigma_t$ (or in the original DDPM formulation, $\beta_t$). What is the noise level at this step? It is the standard deviation of the Gaussian distribution we are sampling from. As $t$ increases, the noise level increases. As we reverse the process, the noise level decreases.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us look at the forward process mathematically. We start with a data point $x_0$. At each step $t$, we add noise:

$x_t = \sqrt{1 - \beta_t} x_{t-1} + \sqrt{\beta_t} \epsilon$

Where:
*   $x_t$ is the noisy data at step $t$.
*   $x_{t-1}$ is the noisy data at the previous step.
*   $\beta_t$ is the variance of the noise added at step $t$. This is the "noise schedule." In our lab, we used a constant $\beta = 0.01$. In real models, $\beta_t$ varies, often increasing over time.
*   $\epsilon$ is a sample from a standard normal distribution, $N(0, I)$. This is the pure noise.
*   $\sqrt{1 - \beta_t}$ ensures that the variance of the data component is preserved (variance-preserving schedule).

The critical realization is that we can skip steps. Instead of iterating 100 times, we can jump directly from $x_0$ to $x_t$ using the closed-form solution:

$x_t = \sqrt{\bar{\alpha}_t} x_0 + \sqrt{1 - \bar{\alpha}_t} \epsilon$

Where $\bar{\alpha}_t = \prod_{s=1}^{t} (1 - \beta_s)$. This allows us to sample $x_t$ directly from $x_0$ for any $t$, which is crucial for training efficiency.

In ComfyUI’s `comfy/k_diffusion/sampling.py`, you will see functions like `get_sigmas_vp` (variance-preserving) and `get_sigmas_karras`. These functions generate the $\sigma$ values (which relate to $\beta$) that define the noise schedule. The `sample_euler` function then uses these sigmas to perform the reverse ODE integration. The noise level $\sigma_t$ is the bridge between the probabilistic view (DDPM) and the deterministic ODE view (used by modern samplers like Euler and DPM++).

## In ComfyUI

The core logic for these calculations resides in `comfy/k_diffusion/sampling.py`. This file contains the primary sampling logic, including `get_sigmas_karras` (constructs the noise schedule of Karras et al., 2022) and `sample_euler` (implements Algorithm 2 from Karras et al., 2022).

The `NoiseScheduleVP` class, found in `comfy/extra_samplers/uni_pc.py`, defines the variance-preserving (VP) noise schedule. It provides methods to calculate marginal log mean coefficients, alpha, standard deviation, and lambda values. This is where the "noise level" is mathematically defined for the solver.

The `model_wrapper` function in the same file adapts the underlying neural network to output either the predicted noise or the predicted data. This is the "denoiser" we discussed in the intuition. It takes the noisy latent $x_t$ and the current noise level $\sigma_t$ and predicts the noise $\epsilon$.

Note: Specific node names for the DDPM forward process are not covered in our sources, as ComfyUI primarily exposes the *reverse* sampling process to the user. The forward process is implicit in the training data and the noise schedule definitions.

## Lab

In this lab, we simulated the forward diffusion process on a simple 1D data point. We started with a vector $x_0 = [1.0, 2.0, 3.0]$. We applied 100 steps of noise addition using a constant $\beta = 0.01$. The formula used was $x_t = x_{t-1} + \sqrt{\beta} \epsilon$, where $\epsilon$ is sampled from a standard normal distribution.

We ran the simulation with a fixed random seed to ensure reproducibility. The results demonstrate that the data is perturbed by the noise, but the mean remains relatively stable because the noise has zero mean.

Here are the exact `RESULT` lines from the lab output:

`RESULT original = ['1', '2', '3']`
This proves our starting state was the clean data point $x_0$.

`RESULT after_diffusion = ['1.56143', '1.94978', '2.71895']`
This proves that after 100 steps of adding Gaussian noise, the data has been significantly altered. The values are no longer integers; they are continuous, noisy values. The first component increased, the second decreased slightly, and the third decreased. This is the "static" we discussed.

`RESULT mean_original = 2`
This is the mean of the original data: $(1+2+3)/3 = 2$.

`RESULT mean_after = 2.07672`
This proves that the mean has not drifted wildly. The expected mean of the noise is 0, so the mean of the data should remain close to the original mean. The small difference (0.07672) is due to the finite sample size and the specific random seed. This confirms the stability of the forward process.

`Lab complete: Diffusion adds noise deterministically given the seed`
This confirms that the process is stochastic in nature (due to $\epsilon$) but deterministic in execution when the seed is fixed. This is crucial for reproducibility in ComfyUI workflows.

## Common mistakes

1.  **Confusing $\beta$ with $\sigma$**: In the original DDPM paper, $\beta_t$ is the variance of the noise added at step $t$. In modern implementations like ComfyUI’s `k_diffusion`, we often work with $\sigma_t$ (the standard deviation) or $\lambda_t$ (the log-SNR). Do not mix these up. The noise level is the standard deviation, not the variance.
2.  **Assuming the forward process is reversible without training**: You cannot simply subtract the noise you added. The noise is random. You must train a model to *predict* the noise based on the noisy input. The model learns the score function (the gradient of the log probability density).
3.  **Ignoring the noise schedule**: The choice of $\beta_t$ (or $\sigma_t$) is critical. A linear schedule, a cosine schedule, or a Karras schedule all produce different results. Using a constant $\beta$ (as in our lab) is a simplification that does not reflect real-world models, where the noise level increases over time.

## Go deeper

To understand the full mathematical derivation, read the original paper:

*   **arXiv:2006.11239**: *Denoising Diffusion Probabilistic Models* by Jonathan Ho, Ajay Jain, and Pieter Abbeel. This paper introduces the weighted variational bound and the connection to denoising score matching. It reports an Inception score of 9.46 and a FID score of 3.17 on CIFAR10, which was state-of-the-art at the time.

This paper is the cornerstone of modern diffusion models. Every sampler in ComfyUI, from Euler to DPM++, is a variation on the theme established here.

