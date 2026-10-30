# CU-202 - Diffusion from first principles

**Objective.** Derive the closed form of the forward process, say exactly what the network is trained to predict, and read the sigma numbers ComfyUI prints. Taught by Dr. Denoise.

## The idea

Destroying data is easy, so make it the training data. Add a little Gaussian noise many times, until nothing is left. Then train a network to undo one small step. Sohl-Dickstein et al. (2015) introduced this, and their key observation is that for small steps the reverse step is close to Gaussian too, so the network only has to supply its mean. Ho et al. (2020) found a parameterisation that made it work on images.

## The maths

One forward step, with a small variance β_t from a fixed schedule:

```
x_t = √(1−β_t) · x_(t−1) + √β_t · ε      ε ~ N(0, I)
```

A sum of independent Gaussians is Gaussian and the variances add, so any level can be reached in one jump (Ho et al. 2020, eq. 4):

```
x_t = √ᾱ_t · x_0 + √(1−ᾱ_t) · ε          ᾱ_t = Π_(s≤t) (1−β_s)
```

Ho et al. write the reverse mean using a noise prediction ε_θ and train it with the simplified loss (their eq. 14):

```
μ_θ(x_t, t) = ( x_t − β_t/√(1−ᾱ_t) · ε_θ(x_t, t) ) / √(1−β_t)
L_simple    = E ‖ ε − ε_θ( √ᾱ_t x_0 + √(1−ᾱ_t) ε, t ) ‖²
```

L_simple drops the weights of the variational bound. The paper calls the result a weighted variational bound and reports better samples with it, so this is an empirical choice, not a derived optimum. Weighting is still an active topic: see Min-SNR (Hang et al. 2023).

Divide the closed form by √ᾱ_t and a cleaner picture appears, the one every modern sampler uses:

```
x_t / √ᾱ_t = x_0 + σ · ε        σ = √( (1−ᾱ_t) / ᾱ_t )
```

Noise level is one number, σ. It also gives the signal-to-noise ratio directly: SNR = ᾱ_t / (1−ᾱ_t) = 1/σ².

## In ComfyUI

`ModelSamplingDiscrete` in `comfy/model_sampling.py` builds exactly these sigmas from the betas. The `EPS` class holds the conversions: the model input is x / √(σ²+1), which puts x back on the √ᾱ scale the network was trained on, and the denoised estimate is x − σ · ε̂. Samplers only ever see the denoised estimate.

## Lab

The lab computes both schedules, runs the 1000-step chain for real against the one-jump formula, trains a small epsilon network for 2000 steps, and grades it against the exact answer, which exists for this data.

```text
ddpm linear  4.0358e-05  4.0360e-05  0.0100     157.41
sd scaled    4.6601e-03  4.6819e-03  0.0292     14.61
```

Those columns are ᾱ_T, SNR_T, σ_min and σ_max. The second row is why SD 1.x reports σ from 0.0292 to 14.61. Its SNR at the last step is not zero: Lin et al. (2023) give x_T = 0.068265 · x_0 + 0.997667 · ε for this schedule, so a trace of the image survives at the "pure noise" end. They show this limits how bright or dark results can be.

```text
1000  -0.0043     1.0046      +0.0063     1.0089
variance the formula predicts at t=1000: 1.0001
```

Chain and jump agree, as the algebra says they must.

```text
Wasserstein-1 to the data  exact eps: 0.0344   trained net: 0.0743   two real samples: 0.0545
fraction in the right-hand mode (truth 0.700)  exact: 0.690   trained: 0.704
```

A network on a CPU, 2000 steps, gets within sampling noise of the right mode weights. Two real samples of this size differ by about 0.05 in this measure, so do not read the third decimal.

## What is contested

The choice of loss weighting, and of schedule, are empirical. Calling the last step "pure noise" is only approximately true for the schedules most models shipped with.

## Sources

- [Sohl-Dickstein, Weiss, Maheswaranathan, Ganguli 2015. Deep Unsupervised Learning using Nonequilibrium Thermodynamics](https://arxiv.org/abs/1503.03585)
- [Ho, Jain, Abbeel 2020. Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239)
- [Lin, Liu, Li, Yang 2023. Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/abs/2305.08891)
- [Hang et al. 2023. Efficient Diffusion Training via Min-SNR Weighting Strategy](https://arxiv.org/abs/2303.09556)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
