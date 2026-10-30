# CU-206 - Sigma schedules: where the steps go

**Objective.** Compute what each ComfyUI scheduler returns, explain the flow shift, and measure why a schedule matters without pretending that one is always best. Taught by Dr. Denoise.

## The idea

A sampler (CU-205) says how to step. A scheduler says which noise levels to stop at. Same model, same step count, different stops, different result.

## The maths

These are the formulas in `comfy/samplers.py` and `comfy/k_diffusion/sampling.py`.

```
karras       σ_i = ( σmax^(1/ρ) + i/(n−1) · (σmin^(1/ρ) − σmax^(1/ρ)) )^ρ      ρ = 7
exponential  log-spaced from σmax to σmin
normal       evenly spaced in training timestep, mapped to σ
sgm_uniform  the same, on n+1 points with the last dropped
simple       every (1000/n)-th entry of the model's own sigma table, from the top
kl_optimal   tan( (1−a) atan σmax + a atan σmin ),  a = i/(n−1)
beta         timesteps at quantiles of Beta(0.6, 0.6)
```

Karras et al. (2022) report that ρ = 3 nearly equalises truncation error per step, yet ρ between 5 and 10 gives better images, and they conclude errors near σ_min have a large effect. So the choice of 7 comes from experiment on images, not from theory.

Flow models have a schedule in t, and `time_snr_shift` warps it towards high noise:

```
σ' = a σ / (1 + (a−1) σ)
```

FLUX ties the shift to image size: the `ModelSamplingFlux` node computes μ linearly in the token count, and `flux_time_shift` with its σ = 1 is the formula above with a = e^μ.

## In ComfyUI

`SCHEDULER_HANDLERS` in `comfy/samplers.py` lists the options. At full denoise, `EPS.noise_scaling` scales the first noise by √(1+σ²) rather than σ. The extra 1 is the variance of the latent itself, and the lab does the same. `ModelSamplingSD3` defaults to shift 3.0.

## Lab

The first table shows the schedules for SD 1.x. Note that `simple` and `sgm_uniform` stop near 0.34 and never visit the low levels that `karras` does.

```text
normal        14.615   7.840   4.609   2.918   1.950   1.345  ... 0.029
simple        14.615   8.303   5.088   3.321   2.276   1.613  ... 0.342
karras        14.615   9.103   5.478   3.169   1.749   0.914  ... 0.029
exponential   14.615   7.325   3.671   1.840   0.922   0.462  ... 0.029
```

Then each schedule against a 6000-step reference, with the exact denoiser:

```text
schedule       euler@10   euler@20   dpm2m@10   dpm2m@20
normal         0.12316   0.06500   0.23396   0.07024
simple         0.12088   0.06954   0.08455   0.05181
karras         0.15176   0.07800   0.05459   0.01037
exponential    0.15635   0.08059   0.03931   0.00898
kl_optimal     0.10740   0.05393   0.06005   0.01579
```

There is no single winner. For Euler the schedules are within 40 percent of each other. For DPM++ 2M at 10 steps, `normal` is six times worse than `exponential`. The best schedule depends on the solver, so the two choices are not independent.

```text
steps  shift=1.0  shift=1.5  shift=3.0  shift=6.0
8      0.14107    0.14446    0.18287    0.30681
```

On this toy, more shift is worse. That does not contradict real models using shift 3: a 1-D mixture has no image structure, and the value is chosen on images. Esser et al. (2024) present human preference ratings for shifting at higher resolution (their Figure 6).

```text
  512 px   1024 tokens  mu=0.630  exp(mu)=1.878
 1024 px   4096 tokens  mu=1.150  exp(mu)=3.158
```

## What is contested

Any "best scheduler" claim. Align Your Steps (Sabour et al. 2024) optimises the schedule per model, which itself suggests no fixed list is ideal.

## Sources

- [Karras, Aittala, Aila, Laine 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
- [Lee et al. 2024. Beta Sampling is All You Need: Efficient Image Generation Strategy for Diffusion Models using Stepwise Spectral Analysis](https://arxiv.org/abs/2407.12173)
- [Sabour, Fidler, Kreis 2024. Align Your Steps: Optimizing Sampling Schedules in Diffusion Models](https://arxiv.org/abs/2404.14507)
- [Esser et al. 2024. Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_model_advanced.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_model_advanced.py)
