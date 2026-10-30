# CU-207 - Ancestral and SDE samplers: adding noise back

**Objective.** Compute an ancestral step, explain why these samplers do not settle as steps grow, and say honestly when added noise helps. Taught by Dr. Denoise.

## The idea

An ancestral sampler steps past the target noise level, then adds fresh noise to get back to it. Each step forgets some of the path so far. Samplers named `_ancestral`, `_a` or `_sde` belong to this family.

## The maths

To go from σ_from to σ_to, `get_ancestral_step` splits the target into two parts:

```
σ_up   = min( σ_to, η · √( σ_to² (σ_from² − σ_to²) / σ_from² ) )
σ_down = √( σ_to² − σ_up² )

x ← x + d · (σ_down − σ_from) + σ_up · z        z ~ N(0, I)
```

The bookkeeping is the point: σ_down² + σ_up² = σ_to², so the sample has exactly the noise level the schedule expects. η = 0 gives back the deterministic step.

## In ComfyUI

`sample_euler_ancestral` does this, and flow models go to `sample_euler_ancestral_RF`, which uses the same idea with different algebra because the interpolant scales the signal too. `dpmpp_sde` and the `dpmpp_2m_sde` family use `BrownianTreeNoiseSampler` in place of independent draws, so the noise between two sigmas depends only on those sigmas, and not on how many steps you took.

## Lab

```text
from    to      sigma_down  sigma_up   down^2+up^2  to^2
14.0    8.0     4.5714      6.5652     64.0000      64.0000
1.0     0.2     0.0400      0.1960     0.0400       0.0400
```

Most of each step down is noise put back in: going from 14 to 8 means stepping to 4.57, then adding noise of 6.57.

Both kinds reach the data distribution, at their own pace:

```text
steps  W1 euler   W1 ancestral
10     0.2623     0.3801
80     0.0393     0.0696
320    0.0130     0.0129
```

But do they settle on one image? Same seed, N against 2N steps:

```text
N      euler     ancestral  ancestral(eta=0.5)
10     0.2390    1.8318     1.2426
160    0.0349    2.1342     1.5741
```

Euler converges. Ancestral does not, and this is not a bug: its noise is drawn per step, so more steps means a different sequence. With a fixed noise path, an SDE sampler does settle, which is what the Brownian tree buys:

```text
10     1.5425
640    0.0658
```

Noise also forgets the start. Nudge the first noise, and only the deterministic result moves much:

```text
nudged start, same sampler seed: RMS change of the result   euler 0.3399   ancestral 0.0424
```

That explains the practical advice to avoid ancestral samplers when you want a small change of seed or strength to give a small change of image.

## What is contested

"Noise fixes errors" is half true. Karras et al. (2022) write that stochasticity is effective in correcting errors made by earlier steps but has its own drawbacks, and that the optimal amount should be determined empirically. This lab has a counter-example, with a steady bias added to the denoiser:

```text
biased denoiser, 80 steps, W1 to data   euler 0.2869   ancestral 0.4843
```

Here the ancestral sampler does worse. This is one toy and one kind of error, so it refutes only the unconditional claim. It is not evidence that ancestral samplers are worse on real models.

## Sources

- [Karras, Aittala, Aila, Laine 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
- [Song et al. 2020. Score-Based Generative Modeling through Stochastic Differential Equations](https://arxiv.org/abs/2011.13456)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
